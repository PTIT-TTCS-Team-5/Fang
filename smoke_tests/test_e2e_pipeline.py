import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.database import acquire_conn, db
from app.core.logging import logger
from app.models.cv_models import ParsedCV
from app.services.chunking import process_document_to_chunks
from app.services.cv_loader import download_cv
from app.services.cv_parser import parse_to_raw_and_json
from app.services.embedding import embed_chunks
from app.services.markdown_builder import (
    convert_json_to_markdown,
    extract_global_metadata,
)
from app.services.persistence import save_chunk_payloads, save_parsed_cv

DEFAULT_JOB_APP_ID = 9999
DEFAULT_PDF_PATH = "sample.pdf"
DEFAULT_PREVIEW_COUNT = 3
SOURCE_TYPE = "CV"
EXPECTED_EMBEDDING_DIM = 1024


def _console_print(text: str = "") -> None:
    """Print text safely on Windows terminals with limited encodings."""

    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    sys.stdout.buffer.write(f"{text}\n".encode(encoding, errors="replace"))


def _validate_runtime_embedding_config() -> None:
    """Fail fast when runtime embedding settings drift from the current schema."""

    if settings.embedding_dim != EXPECTED_EMBEDDING_DIM:
        raise RuntimeError(
            "Runtime EMBEDDING_DIM does not match the current database schema. "
            f"Expected {EXPECTED_EMBEDDING_DIM}, got {settings.embedding_dim}. "
            "Update your environment config or override EMBEDDING_DIM before "
            "running test_e2e_pipeline.py."
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the CV E2E pipeline: parse -> markdown -> chunk -> embed -> DB."
    )
    parser.add_argument("--pdf-path", default=DEFAULT_PDF_PATH)
    parser.add_argument("--cv-url", default=os.getenv("E2E_CV_URL"))
    parser.add_argument("--job-app-id", type=int, default=DEFAULT_JOB_APP_ID)
    parser.add_argument("--preview-count", type=int, default=DEFAULT_PREVIEW_COUNT)
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Run parse/chunk/embed only without persisting to PostgreSQL.",
    )
    return parser.parse_args()


async def _load_cv_bytes(pdf_path: str, cv_url: str | None) -> tuple[bytes, str]:
    if cv_url:
        logger.info("Loading CV from remote URL", extra={"cvUrl": cv_url})
        return await download_cv(cv_url), cv_url

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(
            f"CV file not found at '{pdf_file}'. Provide --cv-url or a valid --pdf-path."
        )

    logger.info("Loading CV from local file", extra={"pdfPath": str(pdf_file)})
    return pdf_file.read_bytes(), str(pdf_file.resolve())


def _build_chunk_metadata(
    cv_parsed_id: int,
    parser_ver: str,
    global_context: str,
    parsed_cv: ParsedCV,
    markdown_text: str,
    chunk_count: int,
) -> list[dict[str, Any]]:
    candidate_name = None
    if parsed_cv.candidateInfo:
        candidate_name = parsed_cv.candidateInfo[0].fullName

    base_metadata = {
        "cvParsedId": cv_parsed_id,
        "parserVer": parser_ver,
        "candidateName": candidate_name,
        "chunkingStrategy": "hybrid-structure-aware",
        "contextInjected": True,
        "globalContext": global_context,
        "markdownLength": len(markdown_text),
    }
    return [dict(base_metadata) for _ in range(chunk_count)]


def _print_chunk_preview(
    chunk_payloads: list[dict[str, Any]],
    preview_count: int,
) -> None:
    if not chunk_payloads:
        _console_print("Khong tao duoc chunk nao.")
        return

    _console_print("\n" + "=" * 80)
    _console_print("CHUNK PREVIEW")
    _console_print("=" * 80)
    for payload in chunk_payloads[: max(1, preview_count)]:
        _console_print(f"\nChunk Index : {payload['chunkIndex']}")
        _console_print(f"Token Count : {payload['tokenCount']}")
        _console_print(payload["content"][:1000])


async def _ensure_mock_job_application(job_app_id: int, cv_source: str) -> None:
    mock_queries = [
        """
        INSERT INTO "user" (
            userId, userName, pwd, fName, lName, email, provId, ward, street, role
        )
        VALUES (
            $1, 'mock_candidate', 'mock_pwd', 'Candidate', 'Mock',
            'mock@test.com', 'HANOI', 'CG', '123 Test', 'CANDIDATE'
        )
        ON CONFLICT (userId) DO NOTHING;
        """,
        """
        INSERT INTO CANDIDATE (userId)
        VALUES ($1)
        ON CONFLICT (userId) DO NOTHING;
        """,
        """
        INSERT INTO COMPANY (compId, compName, provId, ward, street)
        VALUES ($1, 'Mock AI Company', 'HANOI', 'CG', '123 Test')
        ON CONFLICT (compId) DO NOTHING;
        """,
        """
        INSERT INTO JOBPOSTING (jobPostId, title, description, expAt, compId)
        VALUES (
            $1, 'Mock AI Engineer', 'Mock Description',
            CURRENT_TIMESTAMP + INTERVAL '30 days', $1
        )
        ON CONFLICT (jobPostId) DO NOTHING;
        """,
        """
        INSERT INTO JOBAPPLICATION (jobAppId, candidateId, jobPostId, stat, cvSnapUrl)
        VALUES ($1, $1, $1, 'PENDING', $2)
        ON CONFLICT (jobAppId) DO UPDATE
        SET cvSnapUrl = EXCLUDED.cvSnapUrl;
        """,
    ]

    async with acquire_conn() as conn:
        await conn.execute(mock_queries[0], job_app_id)
        await conn.execute(mock_queries[1], job_app_id)
        await conn.execute(mock_queries[2], job_app_id)
        await conn.execute(mock_queries[3], job_app_id)
        await conn.execute(mock_queries[4], job_app_id, cv_source)


async def _verify_persisted_rows(job_app_id: int) -> None:
    async with acquire_conn() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) AS chunk_count,
                COUNT(embedding) AS embedded_count
            FROM AIDOCUMENTCHUNK
            WHERE jobAppId = $1 AND sourceType = $2;
            """,
            job_app_id,
            SOURCE_TYPE,
        )

    _console_print("\n" + "=" * 80)
    _console_print("DATABASE CHECK")
    _console_print("=" * 80)
    _console_print(f"jobAppId       : {job_app_id}")
    _console_print(f"saved chunks   : {row['chunk_count']}")
    _console_print(f"saved vectors  : {row['embedded_count']}")


async def run_e2e_pipeline(args: argparse.Namespace) -> None:
    _validate_runtime_embedding_config()
    cv_bytes, cv_source = await _load_cv_bytes(args.pdf_path, args.cv_url)

    raw_text, parsed_json = await parse_to_raw_and_json(cv_bytes)
    parsed_cv = ParsedCV.model_validate(parsed_json)
    parser_ver = str(parsed_json.get("parserVer") or "gemini_tiered_fallback")

    global_context = extract_global_metadata(parsed_cv)
    markdown_text = convert_json_to_markdown(parsed_cv)
    chunk_payloads = process_document_to_chunks(markdown_text, global_context)
    chunk_contents = [payload["content"] for payload in chunk_payloads]

    _console_print("\n" + "=" * 80)
    _console_print("PIPELINE SUMMARY")
    _console_print("=" * 80)
    _console_print(f"CV source      : {cv_source}")
    _console_print(f"parser version : {parser_ver}")
    _console_print(f"markdown chars : {len(markdown_text)}")
    _console_print(f"chunk count    : {len(chunk_payloads)}")

    _print_chunk_preview(chunk_payloads, args.preview_count)

    vectors = await embed_chunks(chunk_contents) if chunk_contents else []
    _console_print(f"embedding count: {len(vectors)}")

    if args.skip_db:
        _console_print("Bo qua buoc ghi database do co --skip-db.")
        return

    await db.connect()
    try:
        await _ensure_mock_job_application(args.job_app_id, cv_source)
        cv_parsed_id = await save_parsed_cv(
            args.job_app_id,
            raw_text,
            parsed_json,
            parser_ver,
        )
        metadata_items = _build_chunk_metadata(
            cv_parsed_id=cv_parsed_id,
            parser_ver=parser_ver,
            global_context=global_context,
            parsed_cv=parsed_cv,
            markdown_text=markdown_text,
            chunk_count=len(chunk_payloads),
        )
        await save_chunk_payloads(
            job_app_id=args.job_app_id,
            source_type=SOURCE_TYPE,
            chunk_payloads=chunk_payloads,
            metadata_items=metadata_items,
            embeddings=vectors,
            replace_existing=True,
        )
        await _verify_persisted_rows(args.job_app_id)
    finally:
        await db.disconnect()


if __name__ == "__main__":
    cli_args = _parse_args()
    asyncio.run(run_e2e_pipeline(cli_args))
