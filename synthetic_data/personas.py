"""synthetic_data/personas.py — 8 Persona definitions + Manifest Generator.

Manifest generation is deterministic (seed=42) — chạy lại cho cùng kết quả.
"""

import random
from typing import TypedDict

# ============================================================
# Skill Pools per Category
# ============================================================

# Catalog skills (từ root_data.sql SKILL table)
SKILL_CATALOG = {
    # Languages
    "lang_basic": [
        "Java",
        "Python",
        "JavaScript",
        "TypeScript",
        "C++",
        "C#",
        "PHP",
        "Swift",
        "Kotlin",
    ],
    # Frontend
    "frontend": [
        "ReactJS",
        "VueJS",
        "Angular",
        "HTML/CSS",
        "Svelte",
        "Tailwind CSS",
        "Redux",
        "Webpack",
        "Vite",
    ],
    # Backend
    "backend_jvm": ["Spring Boot", "Java"],
    "backend_py": ["FastAPI", "Django", "Python"],
    "backend_js": ["NodeJS", "ExpressJS", "NestJS"],
    # DB
    "database": ["MySQL", "PostgreSQL", "MongoDB", "Redis", "SQL"],
    # Infra
    "devops": ["Docker", "AWS", "Linux", "Nginx", "PM2", "Git"],
    # Mobile
    "mobile": ["Swift", "Kotlin", "Flutter"],
    # AI/ML
    "ai_ml": [
        "Machine Learning",
        "Deep Learning",
        "NLP",
        "TensorFlow",
        "PyTorch",
        "Python",
        "Azure ML",
    ],
    # API / Protocols
    "api": ["RESTful API", "GraphQL", "WebSocket"],
    # Soft skills (not always included)
    "soft": ["Làm việc nhóm", "Giao tiếp", "Quản lý thời gian"],
    # Certs
    "certs": ["TOEIC", "IELTS"],
    # Version control
    "vcs": ["Git", "GitHub"],
}

# ============================================================
# Persona Definitions
# ============================================================


class PersonaDef(TypedDict):
    persona_type: str
    ratio: float
    exp_years_range: tuple[int, int]  # (min, max) inclusive
    skill_count_range: tuple[int, int]
    noise_level: float  # 0.0 = no noise
    salary_range: (
        tuple[int, int] | None
    )  # (min, max) VND/tháng, None = intern (no salary)
    skill_pool_keys: list[str]  # keys từ SKILL_CATALOG
    description: str


PERSONA_DEFS: list[PersonaDef] = [
    {
        "persona_type": "intern_blank",
        "ratio": 0.05,
        "exp_years_range": (0, 0),
        "skill_count_range": (2, 4),
        "noise_level": 0.15,
        "salary_range": None,
        "skill_pool_keys": ["lang_basic", "frontend", "vcs", "soft"],
        "description": "Thực tập sinh, chưa có kinh nghiệm",
    },
    {
        "persona_type": "fresher_dreamer",
        "ratio": 0.15,
        "exp_years_range": (0, 1),
        "skill_count_range": (5, 8),
        "noise_level": 0.10,
        "salary_range": (6_000_000, 10_000_000),
        "skill_pool_keys": ["frontend", "backend_js", "backend_py", "database", "vcs"],
        "description": "Sinh viên mới ra trường, nhiều kỳ vọng",
    },
    {
        "persona_type": "junior_solid",
        "ratio": 0.30,
        "exp_years_range": (1, 3),
        "skill_count_range": (6, 10),
        "noise_level": 0.03,
        "salary_range": (10_000_000, 18_000_000),
        "skill_pool_keys": [
            "frontend",
            "backend_jvm",
            "backend_py",
            "backend_js",
            "database",
            "api",
            "vcs",
        ],
        "description": "Junior vững chắc, cần hướng dẫn ít",
    },
    {
        "persona_type": "mid_generalist",
        "ratio": 0.25,
        "exp_years_range": (3, 5),
        "skill_count_range": (8, 15),
        "noise_level": 0.02,
        "salary_range": (18_000_000, 30_000_000),
        "skill_pool_keys": [
            "frontend",
            "backend_jvm",
            "backend_py",
            "backend_js",
            "database",
            "devops",
            "api",
            "vcs",
        ],
        "description": "Mid-level làm việc độc lập, đa ngăn",
    },
    {
        "persona_type": "senior_specialist",
        "ratio": 0.12,
        "exp_years_range": (5, 8),
        "skill_count_range": (10, 20),
        "noise_level": 0.0,
        "salary_range": (30_000_000, 55_000_000),
        "skill_pool_keys": [
            "ai_ml",
            "devops",
            "database",
            "api",
            "backend_jvm",
            "backend_py",
            "vcs",
        ],
        "description": "Senior chuyên sâu 1-2 lĩnh vực kỹ thuật",
    },
    {
        "persona_type": "senior_overqualified",
        "ratio": 0.05,
        "exp_years_range": (8, 12),
        "skill_count_range": (15, 25),
        "noise_level": 0.0,
        "salary_range": (55_000_000, 90_000_000),
        "skill_pool_keys": [
            "ai_ml",
            "devops",
            "database",
            "backend_jvm",
            "backend_py",
            "frontend",
            "api",
            "vcs",
            "soft",
        ],
        "description": "Lead/Architect cấp cao, dư năng lực cho most jobs",
    },
    {
        "persona_type": "career_changer",
        "ratio": 0.05,
        "exp_years_range": (3, 5),
        "skill_count_range": (5, 8),
        "noise_level": 0.08,
        "salary_range": (12_000_000, 22_000_000),
        "skill_pool_keys": ["frontend", "backend_py", "database", "vcs", "soft"],
        "description": "Chuyển ngành từ lĩnh vực khác vào IT",
    },
    {
        "persona_type": "foreign_cv",
        "ratio": 0.03,
        "exp_years_range": (2, 5),
        "skill_count_range": (8, 12),
        "noise_level": 0.03,
        "salary_range": (20_000_000, 40_000_000),
        "skill_pool_keys": [
            "backend_jvm",
            "backend_py",
            "database",
            "devops",
            "api",
            "vcs",
            "certs",
        ],
        "description": "CV viết theo chuẩn quốc tế, mixed EN/JP terminology",
    },
]

# Map persona_type → def for fast lookup
PERSONA_MAP: dict[str, PersonaDef] = {p["persona_type"]: p for p in PERSONA_DEFS}

# ============================================================
# Province Distribution
# ============================================================

PROVINCE_WEIGHTS = {
    "HANOI": 0.35,
    "TPHCM": 0.35,
    "DANANG": 0.10,
    "HAIPHONG": 0.05,
    "BACNINH": 0.03,
    "CANTHO": 0.03,
    "LAOCAI": 0.02,
    "QUANGNINH": 0.02,
    "KHANHHOA": 0.02,
    "GIALAI": 0.01,
    "DONGNAI": 0.01,
    "THANHHOA": 0.01,
}

_PROV_KEYS = list(PROVINCE_WEIGHTS.keys())
_PROV_VALS = list(PROVINCE_WEIGHTS.values())

# ============================================================
# Vietnamese Name Generator
# ============================================================

_HO = [
    ("Nguyễn", 38),
    ("Trần", 12),
    ("Lê", 10),
    ("Phạm", 8),
    ("Hoàng", 5),
    ("Vũ", 5),
    ("Đặng", 4),
    ("Bùi", 3),
    ("Đỗ", 2),
    ("Hồ", 2),
    ("Ngô", 2),
    ("Dương", 2),
    ("Lý", 1),
    ("Trương", 1),
    ("Đinh", 1),
    ("Lưu", 1),
    ("Mai", 1),
    ("Tô", 1),
]

_DEM_NAM = [
    "Văn",
    "Hữu",
    "Quang",
    "Thanh",
    "Đức",
    "Xuân",
    "Minh",
    "Anh",
    "Trung",
    "Đình",
]
_TEN_NAM = [
    "Hùng",
    "Dũng",
    "Tuấn",
    "Khoa",
    "Hiếu",
    "Thắng",
    "Nam",
    "Hải",
    "Phong",
    "Kiên",
    "Tùng",
    "Huy",
    "Đạt",
    "Long",
    "Bình",
    "Sơn",
    "Khánh",
    "Thành",
    "Phúc",
    "Vũ",
    "Cường",
    "Linh",
    "Hoàng",
    "Trường",
    "Duy",
    "Tài",
    "Tiến",
    "Bảo",
    "Quân",
    "Nhân",
]

_DEM_NU = [
    "Thị",
    "Thanh",
    "Ngọc",
    "Phương",
    "Hoàng",
    "Bích",
    "Thùy",
    "Kim",
    "Thu",
    "Lan",
]
_TEN_NU = [
    "Hà",
    "Linh",
    "Mai",
    "Yến",
    "Oanh",
    "Hương",
    "Trang",
    "Ngân",
    "Thảo",
    "Ly",
    "Hoa",
    "Anh",
    "Chi",
    "Vân",
    "Nhi",
    "Minh",
    "Phương",
    "Loan",
    "Trinh",
    "Nguyệt",
    "Diễm",
    "Tuyền",
    "Giang",
    "Xuân",
    "An",
    "Duyên",
    "Bảo",
    "Châu",
    "Nhung",
    "Hạnh",
]


def _generate_names(total: int, rng: random.Random) -> list[str]:
    """Generate `total` unique Vietnamese full names."""
    # Build weighted ho list
    ho_pool = []
    for ho, weight in _HO:
        ho_pool.extend([ho] * weight)

    names: set[str] = set()
    result: list[str] = []
    half = total // 2

    while len(result) < total:
        is_male = len(result) < half
        ho = rng.choice(ho_pool)
        if is_male:
            dem = rng.choice(_DEM_NAM)
            ten = rng.choice(_TEN_NAM)
        else:
            dem = rng.choice(_DEM_NU)
            ten = rng.choice(_TEN_NU)
        full = f"{ho} {dem} {ten}"
        if full not in names:
            names.add(full)
            result.append(full)

    return result


# ============================================================
# Manifest Generator
# ============================================================


class CVManifestEntry(TypedDict):
    cv_index: int
    batch_id: str
    persona: str
    skill_pool: list[str]  # Skills pre-selected từ catalog
    salary_range: list[int] | None
    exp_years: int
    province: str
    full_name: str


def generate_manifest(total_cv: int = 500, seed: int = 42) -> list[CVManifestEntry]:
    """Pre-compute toàn bộ CV assignments. Deterministic với seed=42.

    Returns list of CVManifestEntry (one per CV).
    """
    rng = random.Random(seed)

    # --- Bước 1: Tính số lượng theo tỉ lệ ---
    distribution: dict[str, int] = {}
    for p in PERSONA_DEFS:
        distribution[p["persona_type"]] = int(total_cv * p["ratio"])

    # Cân bằng remainder → thêm vào junior_solid
    assigned = sum(distribution.values())
    distribution["junior_solid"] += total_cv - assigned

    # --- Bước 2: Tạo ordered list persona assignments ---
    persona_assignments: list[str] = []
    for persona_type, count in distribution.items():
        persona_assignments.extend([persona_type] * count)
    rng.shuffle(persona_assignments)

    # --- Bước 3: Pre-generate names ---
    names = _generate_names(total_cv, rng)

    # --- Bước 4: Build manifest ---
    manifest: list[CVManifestEntry] = []

    for idx, persona_type in enumerate(persona_assignments):
        p_def = PERSONA_MAP[persona_type]
        batch_num = idx // 5 + 1
        batch_id = f"batch_{batch_num:03d}"

        # Build skill pool từ catalog keys của persona
        pool_keys = p_def["skill_pool_keys"]
        raw_pool: list[str] = []
        for key in pool_keys:
            raw_pool.extend(SKILL_CATALOG.get(key, []))
        # Deduplicate, shuffle
        unique_pool = list(dict.fromkeys(raw_pool))
        rng.shuffle(unique_pool)

        # Select skill count
        skill_min, skill_max = p_def["skill_count_range"]
        skill_count = rng.randint(skill_min, min(skill_max, len(unique_pool)))
        selected_skills = unique_pool[:skill_count]

        # Exp years
        exp_min, exp_max = p_def["exp_years_range"]
        exp_years = rng.randint(exp_min, exp_max)

        # Province
        province = rng.choices(_PROV_KEYS, weights=_PROV_VALS, k=1)[0]

        # Salary
        sal_range = p_def["salary_range"]

        entry: CVManifestEntry = {
            "cv_index": idx,
            "batch_id": batch_id,
            "persona": persona_type,
            "skill_pool": selected_skills,
            "salary_range": list(sal_range) if sal_range else None,
            "exp_years": exp_years,
            "province": province,
            "full_name": names[idx],
        }
        manifest.append(entry)

    return manifest


if __name__ == "__main__":
    # Quick sanity check
    m = generate_manifest(500)
    from collections import Counter

    counts = Counter(e["persona"] for e in m)
    print("Manifest generated:", len(m), "entries")
    for p, c in sorted(counts.items()):
        print(f"  {p:<25}: {c:>3} ({c/5:.0f}%)")
    print("First entry:", m[0])
