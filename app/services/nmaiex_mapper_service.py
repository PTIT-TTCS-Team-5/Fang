# [NMAIex] Mapper Service — String → ID via LLM (auto-lite)
# Tham chiếu: [NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md — Mục 3.2, 7.2, 8.2, 8.3

from __future__ import annotations

import json
import logging

from app.core.database import acquire_conn
from app.core.nmaiex_config import nmaiex_settings
from app.models.nmaiex_schemas import ProvinceMappingResult, SkillMappingResult
from app.services.embedding import embed_chunks
from app.services.rag_orchestrator import invoke_generation

logger = logging.getLogger(__name__)


# ============================================================
# Province Mapper
# ============================================================


async def map_string_to_province_id(text: str) -> str | None:
    """Map địa chỉ tự do → provId chuẩn bằng LLM.

    Dùng danh sách 34 tỉnh sau sáp nhập 2025 từ DB (runtime fetch).
    Trả về None nếu LLM trả UNKNOWN hoặc parse thất bại.
    """
    if not text or not text.strip():
        return None

    async with acquire_conn() as conn:
        rows = await conn.fetch("SELECT provId, provName FROM PROVINCE ORDER BY provId")
    province_list = "\n".join(f"- {r['provid']}: {r['provname']}" for r in rows)

    messages = [
        {
            "role": "system",
            "content": (
                "Bạn là công cụ mapping địa chỉ Việt Nam. Nhiệm vụ DUY NHẤT của bạn là "
                "xác định mã provId phù hợp nhất từ DANH SÁCH SAU ĐÂY và chỉ trả về MÃ ĐÓ.\n"
                "DANH SÁCH TỈNH HỢP LỆ (sau sáp nhập 2025):\n"
                f"{province_list}\n\n"
                "QUY TẮC BẮT BUỘC:\n"
                "1. CHỈ trả về một mã provId duy nhất từ danh sách trên. Không được thêm text khác.\n"
                "2. Nếu địa chỉ thuộc tỉnh cũ đã sáp nhập, map sang tỉnh mới tương ứng "
                "(VD: 'Hải Dương' → HAIPHONG; 'Bình Dương' → TPHCM).\n"
                "3. Nếu không xác định được hoặc không khớp bất kỳ tỉnh nào → trả về: UNKNOWN\n"
                "4. TUYỆT ĐỐI KHÔNG tự tạo mã mới, KHÔNG giải thích, KHÔNG thêm dấu câu."
            ),
        },
        {"role": "user", "content": f"Địa chỉ cần map: {text}"},
    ]

    trace = await invoke_generation(messages, "auto-lite")
    raw = trace.response.strip().upper()

    try:
        result = ProvinceMappingResult(prov_id=None if raw == "UNKNOWN" else raw)
        return result.prov_id
    except Exception as e:
        logger.warning(f"[NMAIex] Province mapping validation failed: {e}. raw='{raw}'")
        return None


# ============================================================
# Skill Mapper — Strategy C (2-tier)
# ============================================================


async def map_skills(skills: list[str]) -> SkillMappingResult:
    """Tầng 1 — Closed-World Skill Mapper: Map list kỹ năng → SkillMappingResult.

    LLM nhận catalog từ DB (runtime), phân loại thành:
    - matched_ids: skillId khớp trong catalog → dùng cho exact scoring.
    - unmatched_texts: text không khớp → đưa sang Tầng 2 (embed fallback).

    Graceful degradation: nếu LLM trả output không hợp lệ, toàn bộ skills
    được đưa vào unmatched_texts để không mất thông tin.
    """
    if not skills:
        return SkillMappingResult(matched_ids=[], unmatched_texts=[])

    async with acquire_conn() as conn:
        rows = await conn.fetch(
            "SELECT skillId, skillName FROM SKILL ORDER BY skillName"
        )
    skill_list = "\n".join(f"- {r['skillid']}: {r['skillname']}" for r in rows)

    messages = [
        {
            "role": "system",
            "content": (
                "Bạn là công cụ mapping kỹ năng 2 tầng. Nhiệm vụ DUY NHẤT của bạn là "
                "phân loại các kỹ năng đầu vào thành:\n"
                "  1. matched_ids: Danh sách skillId từ catalog (số nguyên) khớp với kỹ năng.\n"
                "  2. unmatched_texts: Danh sách tên kỹ năng (string) KHÔNG khớp bất kỳ mục nào.\n\n"
                "DANH SÁCH KỸ NĂNG HỆ THỐNG:\n"
                f"{skill_list}\n\n"
                "QUY TẮC BẮT BUỘC:\n"
                '1. Trả về DUY NHẤT một JSON object: {"matched_ids": [...], "unmatched_texts": [...]}\n'
                "2. matched_ids: CHỈ chứa skillId (số nguyên) từ danh sách trên. KHÔNG tự tạo ID mới.\n"
                "3. unmatched_texts: Giữ nguyên text gốc của kỹ năng không khớp (không viết tắt, không dịch).\n"
                "4. Mỗi kỹ năng đầu vào phải xuất hiện đúng MỘT LẦN: hoặc trong matched_ids hoặc unmatched_texts.\n"
                "5. TUYỆT ĐỐI KHÔNG giải thích, KHÔNG thêm text ngoài JSON object."
            ),
        },
        {"role": "user", "content": f"Kỹ năng cần phân loại: {', '.join(skills)}"},
    ]

    trace = await invoke_generation(messages, "auto-lite")
    response_text = trace.response.strip()

    # Strip markdown code block nếu LLM wrap trong ```json
    if response_text.startswith("```"):
        lines = response_text.splitlines()
        response_text = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        ).strip()

    try:
        result = SkillMappingResult.model_validate_json(response_text)
        logger.info(
            f"[NMAIex] Skill mapping success: "
            f"{len(result.matched_ids)} matched, {len(result.unmatched_texts)} unmatched"
        )
        return result
    except Exception as e:
        logger.warning(
            f"[NMAIex] Skill mapping validation failed: {e}. "
            f"Graceful degradation: all {len(skills)} skills → unmatched_texts"
        )
        # Graceful degradation: không mất thông tin, chuyển toàn bộ sang Tầng 2
        return SkillMappingResult(matched_ids=[], unmatched_texts=list(skills))


# ============================================================
# Tầng 2 — Open-World Embedding Fallback
# ============================================================


async def embed_and_store_raw_skills(
    entity_type: str,
    entity_id: int,
    unmatched_texts: list[str],
    conn,
) -> None:
    """Tầng 2 — Open-World: Embed unmatched skills và lưu vào DB.

    Args:
        entity_type: "candidate" → INSERT vào CANDIDATE_SKILL_RAW.
                     "job"       → INSERT vào JOB_SKILL_RAW.
        entity_id:  candId (nếu candidate) hoặc jobPostId (nếu job).
        unmatched_texts: Danh sách skill text không khớp catalog từ Tầng 1.
        conn: asyncpg connection đang mở (được truyền từ caller để dùng transaction).
    """
    if not unmatched_texts:
        return

    dims = nmaiex_settings.nmaiex_skill_embedding_dims
    vectors = await embed_chunks(unmatched_texts, dimensions=dims)

    if entity_type == "candidate":
        table = "CANDIDATE_SKILL_RAW"
        id_col = "candId"
    elif entity_type == "job":
        table = "JOB_SKILL_RAW"
        id_col = "jobPostId"
    else:
        raise ValueError(
            f"Invalid entity_type: '{entity_type}'. Must be 'candidate' or 'job'."
        )

    if len(vectors) != len(unmatched_texts):
        logger.error(
            f"[NMAIex] embed_and_store_raw_skills: vector count mismatch "
            f"({len(vectors)} vs {len(unmatched_texts)}). Aborting insert."
        )
        return

    # Batch INSERT để tránh N+1 queries
    records = [
        (entity_id, text, json.dumps(vec))
        for text, vec in zip(unmatched_texts, vectors)
    ]

    await conn.executemany(
        f'INSERT INTO {table} ("{id_col}", "rawText", embedding) VALUES ($1, $2, $3::vector)',
        records,
    )

    logger.info(
        f"[NMAIex] Stored {len(records)} raw skill vectors "
        f"into {table} for {entity_type} id={entity_id}"
    )


# ============================================================
# Language Proficiency Normalizer (Phase 2.5g)
# ============================================================

# Thứ tự chuẩn hóa proficiency — dùng để so sánh level
PROFICIENCY_LEVELS = {
    "BASIC": 1,
    "INTERMEDIATE": 2,
    "ADVANCED": 3,
    "FLUENT": 4,
    "NATIVE": 5,
}

_PROFICIENCY_SYSTEM_PROMPT = (
    "Bạn là công cụ chuẩn hóa trình độ ngôn ngữ. Nhiệm vụ DUY NHẤT của bạn là "
    "map một mô tả trình độ bất kỳ sang MỘT trong 5 cấp độ chuẩn sau:\n"
    "  BASIC | INTERMEDIATE | ADVANCED | FLUENT | NATIVE\n\n"
    "Ví dụ mapping:\n"
    "  'N5', 'A1', 'Sơ cấp', 'Beginner' → BASIC\n"
    "  'N3', 'N4', 'B1', 'B2', 'Conversational', 'Trung cấp' → INTERMEDIATE\n"
    "  'N2', 'C1', 'IELTS 6.5-7.5', 'Business level', 'Khá' → ADVANCED\n"
    "  'N1', 'C2', 'IELTS 8+', 'Fluent', 'Thành thạo' → FLUENT\n"
    "  'Native speaker', 'Tiếng mẹ đẻ', 'Mother tongue' → NATIVE\n\n"
    "QUY TẮC BẮT BUỘC:\n"
    "1. CHỈ trả về MỘT từ trong 5 cấp độ trên. KHÔNG thêm text khác.\n"
    "2. Nếu không xác định được → trả về: BASIC\n"
    "3. TUYỆT ĐỐI KHÔNG giải thích, KHÔNG thêm dấu câu."
)


async def normalize_proficiency(raw_proficiency: str | None) -> str:
    """Chuẩn hóa raw proficiency string từ CV → BASIC|INTERMEDIATE|ADVANCED|FLUENT|NATIVE.

    [NMAIex Phase 2.5g] Dùng LLM auto-lite để map đa dạng cách viết:
      'N3' → INTERMEDIATE, 'IELTS 7.5' → ADVANCED, 'Native speaker' → NATIVE, v.v.

    Returns:
        Một trong: 'BASIC', 'INTERMEDIATE', 'ADVANCED', 'FLUENT', 'NATIVE'
        Fallback về 'BASIC' nếu raw_proficiency là None hoặc không xác định.
    """
    if not raw_proficiency or not raw_proficiency.strip():
        return "BASIC"

    # Fast path: nếu đã là cấp độ chuẩn → trả về ngay
    normalized = raw_proficiency.strip().upper()
    if normalized in PROFICIENCY_LEVELS:
        return normalized

    messages = [
        {"role": "system", "content": _PROFICIENCY_SYSTEM_PROMPT},
        {"role": "user", "content": f"Trình độ cần chuẩn hóa: {raw_proficiency}"},
    ]

    try:
        trace = await invoke_generation(messages, "auto-lite")
        result = trace.response.strip().upper()
        if result in PROFICIENCY_LEVELS:
            return result
        logger.warning(
            f"[NMAIex] normalize_proficiency got unexpected value: '{result}'. "
            f"Fallback to BASIC. raw='{raw_proficiency}'"
        )
        return "BASIC"
    except Exception as e:
        logger.warning(
            f"[NMAIex] normalize_proficiency LLM failed: {e}. "
            f"Fallback to BASIC. raw='{raw_proficiency}'"
        )
        return "BASIC"
