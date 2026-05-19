"""synthetic_data/prompts.py — Prompt templates cho LLM generation."""

import json

from app.models.cv_models import ParsedCV
from synthetic_data.models import SyntheticJob

# ============================================================
# JSON Schema helpers
# ============================================================


def _cv_schema_str() -> str:
    """Lấy JSON Schema của ParsedCV để embed vào prompt."""
    return json.dumps(ParsedCV.model_json_schema(), ensure_ascii=False, indent=2)


def _job_schema_str() -> str:
    """Lấy JSON Schema của SyntheticJob để embed vào prompt."""
    return json.dumps(SyntheticJob.model_json_schema(), ensure_ascii=False, indent=2)


# ============================================================
# CV Batch Prompt
# ============================================================

CV_SYSTEM_PROMPT = """Bạn là engine sinh dữ liệu CV cho hệ thống tuyển dụng IT Việt Nam.
Nhiệm vụ: Sinh CHÍNH XÁC {batch_size} CV hoàn chỉnh dưới dạng JSON object.

OUTPUT FORMAT (bắt buộc):
{{
  "cvs": [ <ParsedCV_1>, <ParsedCV_2>, ... ]
}}

JSON Schema cho mỗi ParsedCV:
{cv_schema}

QUY TẮC BẮT BUỘC:
1. Tên ứng viên (fullName trong candidateInfo) PHẢI DÙNG CHÍNH XÁC tên đã cho trong manifest
2. Skills PHẢI lấy từ skill_pool đã chỉ định (không tự bịa skill ngoài danh sách)
3. exp_years quyết định số năm kinh nghiệm — timeline PHẢI hợp lý (endDate - startDate khớp exp_years)
4. rawText: 200-800 từ, viết tự nhiên như CV thật, ngôn ngữ Tiếng Việt
5. expectedSalaryMin/Max: theo salary_range đã cho (hoặc null nếu persona là intern/fresher không đề cập lương)
6. Date format: "YYYY-MM" hoặc "present" — KHÔNG được dùng format khác
7. Nếu persona có noise_level > 0, một số CV có thể có: lỗi chính tả nhỏ trong rawText, thiếu 1-2 field phụ, hoặc skill ngoài pool (nhưng ít nhất 60% skill phải từ skill_pool)
8. KHÔNG thêm field ngoài schema, KHÔNG bỏ field bắt buộc (rawText là bắt buộc)
9. Output phải là valid JSON — không có trailing comma, không có comment"""


def build_cv_batch_prompt(manifest_batch: list[dict]) -> tuple[str, str]:
    """Build system + user prompt cho CV batch.

    Returns: (system_prompt, user_prompt)
    """
    batch_size = len(manifest_batch)
    system = CV_SYSTEM_PROMPT.format(
        batch_size=batch_size,
        cv_schema=_cv_schema_str(),
    )

    # Build per-CV spec
    specs = []
    for i, entry in enumerate(manifest_batch):
        sal = entry.get("salary_range")
        sal_str = (
            f"{sal[0]:,} - {sal[1]:,} VND/tháng"
            if sal
            else "null (không đề cập trong CV)"
        )
        specs.append(
            f"CV #{i+1} (index={entry['cv_index']}):\n"
            f"  - fullName: {entry['full_name']}\n"
            f"  - persona: {entry['persona']} (exp={entry['exp_years']} năm)\n"
            f"  - skill_pool: {', '.join(entry['skill_pool'])}\n"
            f"  - expected_salary: {sal_str}\n"
            f"  - province: {entry['province']}"
        )

    user = (
        f"Batch ID: {manifest_batch[0]['batch_id']}\n\n"
        "Thông tin cho từng CV:\n"
        + "\n\n".join(specs)
        + "\n\nHãy sinh CHÍNH XÁC "
        + str(batch_size)
        + ' CV theo format {"cvs": [...]}.'
    )
    return system, user


# ============================================================
# Job Batch Prompt
# ============================================================

JOB_SYSTEM_PROMPT = """Bạn là engine sinh dữ liệu Job Posting cho hệ thống tuyển dụng IT Việt Nam.
Nhiệm vụ: Sinh CHÍNH XÁC {batch_size} job posting hoàn chỉnh dưới dạng JSON object.

OUTPUT FORMAT (bắt buộc):
{{
  "jobs": [ <SyntheticJob_1>, <SyntheticJob_2>, ... ]
}}

JSON Schema cho mỗi SyntheticJob:
{job_schema}

Thông tin catalog để điền ID:
JOBLEVEL IDs: Intern=1, Fresher=2, Junior=3, Middle=4, Senior=5, Lead=6, Manager=7, Director=8
JOBCATEGORY IDs:
  Backend=1, Frontend=2, Fullstack=3, Mobile=4, AI/ML=5, DataEng=6,
  DataScience=7, DevOps=8, QA=9, Security=10, Game=11, Embedded=12,
  Blockchain=13, UIUX=14, PM=15, ITSupport=16, ERP=17

QUY TẮC BẮT BUỘC:
1. title: Tên job cụ thể, chuyên nghiệp (VD: "Senior Backend Engineer (Java/Spring Boot)")
2. description: 300-700 từ, viết như JD thật — bao gồm: mô tả công việc, yêu cầu kỹ năng, quyền lợi
3. skill_names: Skills từ SKILL catalog (phải match đúng tên trong catalog)
4. custom_skills: Free-text skills không có trong catalog (framework mới, tool nội bộ...)
5. work_mode: ONSITE | HYBRID | REMOTE
6. prov_id: Mã tỉnh từ danh sách đã cho
7. comp_id: PHẢI dùng đúng compId từ danh sách đã cho
8. level_ids: List ID JOBLEVEL phù hợp (thường 1-2 level)
9. cat_ids: List ID JOBCATEGORY (thường 1-2 category)
10. lang_requirements: Nếu job yêu cầu ngoại ngữ, format: {{"lang_code": "en", "req_type": "REQUIRED", "min_level": "INTERMEDIATE"}}
11. Output phải là valid JSON"""


def build_job_batch_prompt(
    batch_specs: list[dict],
    company_map: dict[int, dict],
) -> tuple[str, str]:
    """Build system + user prompt cho Job batch.

    Args:
        batch_specs: List of job spec dicts (from job manifest)
        company_map: {comp_id: {"comp_name": ..., "prov_id": ...}}

    Returns: (system_prompt, user_prompt)
    """
    batch_size = len(batch_specs)
    system = JOB_SYSTEM_PROMPT.format(
        batch_size=batch_size,
        job_schema=_job_schema_str(),
    )

    company_info = "\n".join(
        f"  compId={cid}: {info['comp_name']} (tỉnh: {info['prov_id']})"
        for cid, info in company_map.items()
    )

    specs = []
    for i, spec in enumerate(batch_specs):
        specs.append(
            f"Job #{i+1}:\n"
            f"  - category_hint: {spec.get('category_hint', 'Backend Development')}\n"
            f"  - level_hint: {spec.get('level_hint', 'Junior/Middle')}\n"
            f"  - comp_id: {spec['comp_id']} ({company_map.get(spec['comp_id'], {}).get('comp_name', '?')})\n"
            f"  - prov_id: {spec.get('prov_id', 'HANOI')}\n"
            f"  - salary_hint: {spec.get('salary_hint', '15-25 triệu VND')}\n"
            f"  - work_mode: {spec.get('work_mode', 'ONSITE')}"
        )

    user = (
        f"Danh sách companies:\n{company_info}\n\n"
        "Thông tin cho từng Job:\n"
        + "\n\n".join(specs)
        + "\n\nHãy sinh CHÍNH XÁC "
        + str(batch_size)
        + ' job posting theo format {"jobs": [...]}.'
    )
    return system, user
