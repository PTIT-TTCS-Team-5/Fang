"""This module contains the core logic for parsing CVs using the Gemini API."""

from io import BytesIO
from typing import Any, Dict, Tuple

from google import genai
from google.genai import errors, types

from app.core.config import settings
from app.core.logging import logger
from app.models.cv_models import ParsedCV

# The fastest and most cost-effective model, used as the first attempt.
TIER_1_MODEL = "gemini-3.1-flash"
# A more powerful (and expensive) model, used as a fallback.
TIER_2_MODEL = "gemini-3.1-pro"

# The main prompt instructing the Gemini model on how to parse the CV.
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
    """Custom exception raised when CV parsing fails across all fallback tiers."""


# Defines a mapping from abstract model names to a list of specific,
# concrete model names to try, ordered by preference.
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

# In-memory cache to store resolved model names and avoid repeated API calls.
_MODEL_RESOLUTION_CACHE: dict[str, str] = {}


async def _list_generate_content_models(client: genai.Client) -> set[str]:
    """Lists all available Gemini models that support 'generateContent'.

    Args:
        client: An initialized `google.genai.Client` instance.

    Returns:
        A set of available model names.
    """
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
    """Finds and returns a concrete, available model name for a given abstract request.

    It checks for a cached resolution first. If not found, it queries the
    Gemini API for available models and finds the best match from the
    `MODEL_CANDIDATES` list. The result is then cached.

    Args:
        requested_model: The abstract model name (e.g., "gemini-3.1-flash").

    Returns:
        The resolved, available, concrete model name (e.g., "gemini-3.1-flash-preview").

    Raises:
        CVParsingError: If no suitable model can be found.
    """
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
    """Parses a CV PDF using a specified Gemini model.

    This function handles the entire interaction with the Gemini API for a single
    parsing attempt. It uploads the CV file, sends the generation request with
    the JSON schema, validates the response, and cleans up the uploaded file.

    Args:
        cv_bytes: The byte content of the PDF file.
        model_name: The abstract model name (e.g., "gemini-3.1-flash") to use.

    Returns:
        A `ParsedCV` object containing the structured data from the CV.

    Raises:
        errors.APIError: If the Gemini API returns an error.
        CVParsingError: For specific failures in the parsing logic, like an
                        empty response from the model.
        Exception: For other unexpected errors.
    """
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
        # Upload the PDF bytes to the Gemini Files API for processing.
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

            # Send the prompt and the uploaded file to the model.
            # The response is configured to be JSON, matching the ParsedCV schema.
            response = await aio_client.models.generate_content(
                model=resolved_model_name,
                contents=[CV_PARSE_PROMPT, uploaded_file],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ParsedCV,
                    temperature=0,  # Set to 0 for deterministic, factual output.
                ),
            )

            # Validate the response and deserialize it into a ParsedCV object.
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
        # Ensure the uploaded file is always deleted after the attempt.
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
    """Parses a CV using a two-tier fallback strategy.

    It first attempts to parse the CV with the fast and cheap TIER_1_MODEL.
    If that fails for any reason, it automatically falls back and retries
    with the more powerful TIER_2_MODEL.

    Args:
        cv_bytes: The byte content of the PDF file to parse.

    Returns:
        A tuple containing:
        - The full raw text extracted from the CV.
        - A dictionary representing the structured, parsed CV data.

    Raises:
        CVParsingError: If parsing fails on both tiers.
    """
    tier_1_error: Exception | None = None

    logger.info(
        "Starting CV parsing pipeline",
        extra={
            "tier1Model": TIER_1_MODEL,
            "tier2Model": TIER_2_MODEL,
            "cvBytes": len(cv_bytes),
        },
    )

    # Tier 1 Attempt
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

    # Tier 2 Fallback
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
