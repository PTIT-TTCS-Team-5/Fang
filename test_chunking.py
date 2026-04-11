import asyncio
import json
import os
from typing import Any

from app.core.database import acquire_conn, db
from app.core.logging import logger
from app.models.cv_models import ParsedCV
from app.services.chunking import process_document_to_chunks
from app.services.markdown_builder import (
    convert_json_to_markdown,
    extract_global_metadata,
)
from app.services.persistence import save_chunk_payloads

DEFAULT_TEST_JOB_APP_ID = 9999
SOURCE_TYPE = "CV"
TEST_JOB_APP_ID_ENV = "TEST_CHUNKING_JOB_APP_ID"
TEST_CV_PARSED_ID_ENV = "TEST_CHUNKING_CV_PARSED_ID"
PREVIEW_CHUNK_COUNT = 10
SEPARATOR = "=" * 80


def _read_target_ids() -> tuple[int, int | None]:
    """Resolve the target identifiers for loading CVPARSED from the database."""

    job_app_id_raw = os.getenv(
        TEST_JOB_APP_ID_ENV, str(DEFAULT_TEST_JOB_APP_ID)
    ).strip()
    cv_parsed_id_raw = os.getenv(TEST_CV_PARSED_ID_ENV, "").strip()

    try:
        job_app_id = int(job_app_id_raw)
    except ValueError as exc:
        raise ValueError(
            f"{TEST_JOB_APP_ID_ENV} must be an integer. Received: {job_app_id_raw!r}"
        ) from exc

    if not cv_parsed_id_raw:
        return job_app_id, None

    try:
        return job_app_id, int(cv_parsed_id_raw)
    except ValueError as exc:
        raise ValueError(
            f"{TEST_CV_PARSED_ID_ENV} must be an integer. Received: {cv_parsed_id_raw!r}"
        ) from exc


async def _load_parsed_cv_from_db(
    job_app_id: int,
    cv_parsed_id: int | None = None,
) -> tuple[int, ParsedCV, str | None]:
    """Load a parsed CV strictly from CVPARSED without parser fallback."""

    query = """
        SELECT cvParsedId, jobAppId, parsedJson, parserVer
        FROM CVPARSED
        WHERE jobAppId = $1
    """
    params: tuple[int, ...] = (job_app_id,)

    if cv_parsed_id is not None:
        query = """
            SELECT cvParsedId, jobAppId, parsedJson, parserVer
            FROM CVPARSED
            WHERE jobAppId = $1 AND cvParsedId = $2
        """
        params = (job_app_id, cv_parsed_id)

    async with acquire_conn() as conn:
        row = await conn.fetchrow(query, *params)

    if not row:
        target = (
            f"jobAppId={job_app_id}, cvParsedId={cv_parsed_id}"
            if cv_parsed_id is not None
            else f"jobAppId={job_app_id}"
        )
        raise LookupError(
            f"Khong tim thay ban ghi CVPARSED trong database cho {target}."
        )

    parsed_payload = row["parsedjson"]
    if isinstance(parsed_payload, str):
        parsed_payload = json.loads(parsed_payload)

    parsed_cv = ParsedCV.model_validate(parsed_payload)
    logger.info(
        "Da tai ParsedCV tu database cho smoke test",
        extra={
            "jobAppId": row["jobappid"],
            "cvParsedId": row["cvparsedid"],
        },
    )
    return row["cvparsedid"], parsed_cv, row["parserver"]


def _build_chunk_metadata(
    cv_parsed_id: int,
    parser_ver: str | None,
    global_context: str,
    parsed_cv: ParsedCV,
    markdown_text: str,
    chunk_count: int,
) -> list[dict[str, Any]]:
    """Build metadata rows aligned with AIDOCUMENTCHUNK for smoke-test inserts."""

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


def _print_chunk_preview(chunks: list[dict[str, Any]]) -> None:
    """Print the first three and the last chunk in a readable format."""

    if not chunks:
        print("\nKhong tao duoc chunk nao.")
        return

    selected_indexes = list(range(min(PREVIEW_CHUNK_COUNT, len(chunks))))
    last_index = len(chunks) - 1
    if last_index not in selected_indexes:
        selected_indexes.append(last_index)

    print(f"\n{SEPARATOR}")
    print("KET QUA SMOKE TEST CHUNKING")
    print(SEPARATOR)
    print(f"Tong so chunk duoc tao ra: {len(chunks)}")

    for chunk_position in selected_indexes:
        chunk = chunks[chunk_position]
        print(f"\n{SEPARATOR}")
        print(f"Chunk Index : {chunk['chunkIndex']}")
        print(f"Token Count : {chunk['tokenCount']}")
        print("Content:")
        print(chunk["content"])

    print(f"\n{SEPARATOR}")


async def run_test() -> None:
    """Run the DB-only chunking smoke test and persist results."""

    await db.connect()
    try:
        job_app_id, cv_parsed_id_filter = _read_target_ids()
        cv_parsed_id, parsed_cv, parser_ver = await _load_parsed_cv_from_db(
            job_app_id=job_app_id,
            cv_parsed_id=cv_parsed_id_filter,
        )
        global_context = extract_global_metadata(parsed_cv)
        markdown_text = convert_json_to_markdown(parsed_cv)
        chunks = process_document_to_chunks(markdown_text, global_context)
        metadata_items = _build_chunk_metadata(
            cv_parsed_id=cv_parsed_id,
            parser_ver=parser_ver,
            global_context=global_context,
            parsed_cv=parsed_cv,
            markdown_text=markdown_text,
            chunk_count=len(chunks),
        )
        await save_chunk_payloads(
            job_app_id=job_app_id,
            source_type=SOURCE_TYPE,
            chunk_payloads=chunks,
            metadata_items=metadata_items,
            replace_existing=True,
        )
        _print_chunk_preview(chunks)
        print(
            f"Da luu {len(chunks)} chunk vao bang AIDOCUMENTCHUNK cho jobAppId={job_app_id}."
        )
    except Exception:
        logger.exception("Co loi xay ra trong qua trinh smoke test chunking")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(run_test())
