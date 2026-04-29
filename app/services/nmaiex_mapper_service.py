import json

from app.core.database import acquire_conn
from app.services.rag_orchestrator import invoke_generation


async def map_string_to_province_id(text: str) -> str | None:
    """Map địa chỉ tự do → provId chuẩn bằng LLM."""
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
    result = trace.response.strip().upper()
    return result if result != "UNKNOWN" else None


async def map_strings_to_skill_ids(skills: list[str]) -> list[int]:
    """Map danh sách kỹ năng text → skillId. Dùng LLM vì cách viết đa dạng."""
    if not skills:
        return []

    async with acquire_conn() as conn:
        rows = await conn.fetch(
            "SELECT skillId, skillName FROM SKILL ORDER BY skillName"
        )
    skill_list = "\n".join(f"- {r['skillid']}: {r['skillname']}" for r in rows)

    messages = [
        {
            "role": "system",
            "content": (
                "Bạn là công cụ mapping kỹ năng. Nhiệm vụ DUY NHẤT của bạn là map các kỹ năng "
                "người dùng cung cấp sang các skillId từ DANH SÁCH SAU ĐÂY.\n"
                "DANH SÁCH KỸ NĂNG HỆ THỐNG:\n"
                f"{skill_list}\n\n"
                "QUY TẮC BẮT BUỘC:\n"
                "1. Trả về MỘT JSON array duy nhất, chứa các skillId (số nguyên). VD: [1, 5, 12]\n"
                "2. CHỈ dùng skillId từ danh sách trên. KHÔNG được tự tạo ID mới.\n"
                "3. Nếu một kỹ năng không khớp bất kỳ mục nào → bỏ qua (không thêm vào array).\n"
                "4. Nếu không có kỹ năng nào khớp → trả về: []\n"
                "5. TUYỆT ĐỐI KHÔNG giải thích, KHÔNG thêm text ngoài JSON array."
            ),
        },
        {"role": "user", "content": f"Kỹ năng cần map: {', '.join(skills)}"},
    ]

    trace = await invoke_generation(messages, "auto-lite")
    response_text = trace.response.strip()

    try:
        # Strip potential markdown formatting if LLM includes it
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        elif response_text.startswith("```"):
            response_text = response_text[3:]

        if response_text.endswith("```"):
            response_text = response_text[:-3]

        response_text = response_text.strip()

        parsed_skills = json.loads(response_text)
        if isinstance(parsed_skills, list) and all(
            isinstance(i, int) for i in parsed_skills
        ):
            return parsed_skills
        return []
    except json.JSONDecodeError:
        return []
