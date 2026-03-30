from io import BytesIO
from typing import Any, Dict, Tuple

from google import genai
from google.genai import errors, types

from app.core.config import settings
from app.core.logging import logger
from app.models.cv_models import ParsedCV

TIER_1_MODEL = "gemini-3.1-flash"
TIER_2_MODEL = "gemini-3.1-pro"

CV_PARSE_PROMPT = """
Extract the candidate's CV from the uploaded PDF into the provided JSON schema.

Rules:
- Use only information explicitly present in the PDF.
- Do not invent values. Use null for unknown scalar fields and [] for unknown lists.
- Normalize startDate and endDate to YYYY-MM whenever a month is available.
- Use "present" only when the CV clearly indicates an ongoing role or education entry.
- Keep summary concise and factual.
- Put the CV's plain extracted text into rawText.
- Return only the structured data required by the schema.
""".strip()


class CVParsingError(Exception):
    """Raised when both Gemini parsing tiers fail."""


MODEL_CANDIDATES: dict[str, list[str]] = {
    "gemini-3.1-flash": [
        "gemini-3.1-flash",
        "gemini-3.1-flash-preview",
        "gemini-3.1-flash-lite-preview",
        "gemini-3-flash-preview",
        "gemini-2.5-flash",
        "gemini-flash-latest",
    ],
    "gemini-3.1-pro": [
        "gemini-3.1-pro",
        "gemini-3.1-pro-preview",
        "gemini-3-pro-preview",
        "gemini-2.5-pro",
        "gemini-pro-latest",
    ],
}

_MODEL_RESOLUTION_CACHE: dict[str, str] = {}


async def _list_generate_content_models(client: genai.Client) -> set[str]:
    async with client.aio as aio_client:
        pager = await aio_client.models.list(config={"page_size": 100})
        available_models: set[str] = set()
        async for model in pager:
            model_name = getattr(model, "name", "") or ""
            supported_actions = set(getattr(model, "supported_actions", []) or [])
            normalized_name = model_name.removeprefix("models/")
            if normalized_name and "generateContent" in supported_actions:
                available_models.add(normalized_name)
        return available_models


async def _resolve_model_name(requested_model: str) -> str:
    cached_model = _MODEL_RESOLUTION_CACHE.get(requested_model)
    if cached_model:
        return cached_model

    candidates = MODEL_CANDIDATES.get(requested_model, [requested_model])
    client = genai.Client(api_key=settings.google_api_key)

    try:
        available_models = await _list_generate_content_models(client)
    finally:
        client.close()

    for candidate in candidates:
        if candidate in available_models:
            _MODEL_RESOLUTION_CACHE[requested_model] = candidate
            if candidate != requested_model:
                logger.info(
                    "Resolved Gemini model alias",
                    extra={
                        "requestedModel": requested_model,
                        "resolvedModel": candidate,
                    },
                )
            return candidate

    raise CVParsingError(
        f"No available Gemini model could satisfy requested model '{requested_model}'. "
        f"Candidates tried: {candidates}. Available generateContent models: {sorted(available_models)}"
    )


async def _parse_cv_with_gemini(cv_bytes: bytes, model_name: str) -> ParsedCV:
    resolved_model_name = await _resolve_model_name(model_name)
    logger.info(
        "Starting CV parse with Gemini",
        extra={
            "tierModel": model_name,
            "resolvedTierModel": resolved_model_name,
            "cvBytes": len(cv_bytes),
        },
    )

    uploaded_file = None
    client = genai.Client(api_key=settings.google_api_key)

    try:
        async with client.aio as aio_client:
            uploaded_file = await aio_client.files.upload(
                file=BytesIO(cv_bytes),
                config=types.UploadFileConfig(
                    mime_type="application/pdf",
                    display_name=f"{model_name}-cv.pdf",
                ),
            )
            logger.info(
                "Uploaded CV to Gemini Files API",
                extra={
                    "tierModel": model_name,
                    "resolvedTierModel": resolved_model_name,
                    "uploadedFileName": getattr(uploaded_file, "name", None),
                    "uploadedFileUri": getattr(uploaded_file, "uri", None),
                },
            )

            response = await aio_client.models.generate_content(
                model=resolved_model_name,
                contents=[CV_PARSE_PROMPT, uploaded_file],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ParsedCV,
                    temperature=0,
                ),
            )

            parsed_payload = getattr(response, "parsed", None)
            if isinstance(parsed_payload, ParsedCV):
                parsed_cv = parsed_payload
            elif parsed_payload is not None:
                parsed_cv = ParsedCV.model_validate(parsed_payload)
            elif getattr(response, "text", None):
                parsed_cv = ParsedCV.model_validate_json(response.text)
            else:
                raise CVParsingError(
                    f"Gemini model '{resolved_model_name}' returned an empty structured response."
                )

            parsed_cv.parserVer = resolved_model_name

            logger.info(
                "Gemini CV parse completed successfully",
                extra={
                    "tierModel": model_name,
                    "resolvedTierModel": resolved_model_name,
                    "candidateCount": len(parsed_cv.candidateInfo),
                    "educationCount": len(parsed_cv.education),
                    "experienceCount": len(parsed_cv.experience),
                    "skillCount": len(parsed_cv.skills),
                },
            )
            return parsed_cv
    except errors.APIError:
        logger.exception(
            "Gemini CV parse failed with API error",
            extra={
                "tierModel": model_name,
                "resolvedTierModel": resolved_model_name,
                "cvBytes": len(cv_bytes),
            },
        )
        raise
    except Exception:
        logger.exception(
            "Gemini CV parse failed",
            extra={
                "tierModel": model_name,
                "resolvedTierModel": resolved_model_name,
                "cvBytes": len(cv_bytes),
            },
        )
        raise
    finally:
        try:
            if uploaded_file is not None:
                cleanup_client = genai.Client(api_key=settings.google_api_key)
                try:
                    async with cleanup_client.aio as cleanup_aio_client:
                        await cleanup_aio_client.files.delete(name=uploaded_file.name)
                        logger.info(
                            "Deleted uploaded Gemini file",
                            extra={
                                "tierModel": model_name,
                                "resolvedTierModel": resolved_model_name,
                                "uploadedFileName": getattr(
                                    uploaded_file, "name", None
                                ),
                            },
                        )
                finally:
                    cleanup_client.close()
        except Exception:
            logger.exception(
                "Failed to delete uploaded Gemini file",
                extra={
                    "tierModel": model_name,
                    "resolvedTierModel": resolved_model_name,
                    "uploadedFileName": getattr(uploaded_file, "name", None),
                },
            )
        finally:
            client.close()


async def parse_to_raw_and_json(cv_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    tier_1_error: Exception | None = None

    logger.info(
        "Starting CV parsing pipeline",
        extra={
            "tier1Model": TIER_1_MODEL,
            "tier2Model": TIER_2_MODEL,
            "cvBytes": len(cv_bytes),
        },
    )

    try:
        logger.info("Running CV parser tier 1", extra={"tierModel": TIER_1_MODEL})
        parsed_cv = await _parse_cv_with_gemini(cv_bytes, TIER_1_MODEL)
        logger.info("CV parser tier 1 succeeded", extra={"tierModel": TIER_1_MODEL})
        return parsed_cv.rawText, parsed_cv.model_dump()
    except Exception as exc:
        tier_1_error = exc
        logger.exception(
            "CV parser tier 1 failed, falling back to tier 2",
            extra={"tierModel": TIER_1_MODEL},
        )

    try:
        logger.info("Running CV parser tier 2", extra={"tierModel": TIER_2_MODEL})
        parsed_cv = await _parse_cv_with_gemini(cv_bytes, TIER_2_MODEL)
        logger.info("CV parser tier 2 succeeded", extra={"tierModel": TIER_2_MODEL})
        return parsed_cv.rawText, parsed_cv.model_dump()
    except Exception as tier_2_error:
        logger.exception(
            "CV parser tier 2 failed",
            extra={"tierModel": TIER_2_MODEL},
        )
        raise CVParsingError(
            "CV parsing failed for both Gemini tiers. "
            f"Tier 1 ({TIER_1_MODEL}) error: {tier_1_error}. "
            f"Tier 2 ({TIER_2_MODEL}) error: {tier_2_error}."
        ) from tier_2_error
