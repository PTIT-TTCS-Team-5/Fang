"""synthetic_data/personas.py — 12 Persona definitions + Manifest Generator.

Manifest generation is deterministic (seed=42) — chạy lại cho cùng kết quả.

Extended Seeded Hybrid Manifest:
  - total_cv <= 500: logic nguyên bản, 8 personas gốc, RNG(seed). Cache-safe.
  - total_cv > 500 : Vùng 1 = đệ quy generate_manifest(500, seed) [bất biến].
                     Vùng 2 = _generate_extension với RNG(seed+1000), 12 personas,
                              phân bổ hardcoded từ EXTENSION_PERSONA_DISTRIBUTION.
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
    # QA Testing
    "qa_testing": [
        "Manual Testing",
        "Automation Testing",
        "Selenium",
        "Cypress",
        "JMeter",
        "API Testing",
    ],
    # ERP SAP Specialist
    "erp_sap": [
        "SAP ABAP",
        "SAP MM",
        "SAP SD",
        "SAP HANA",
        "SAP FICO",
        "ERP Consultant",
    ],
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
        "ratio": 0.13,
        "exp_years_range": (0, 1),
        "skill_count_range": (5, 8),
        "noise_level": 0.10,
        "salary_range": (6_000_000, 10_000_000),
        "skill_pool_keys": ["frontend", "backend_js", "backend_py", "database", "vcs"],
        "description": "Sinh viên mới ra trường, nhiều kỳ vọng",
    },
    {
        "persona_type": "junior_solid",
        "ratio": 0.20,
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
        "ratio": 0.17,
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
    {
        "persona_type": "mobile_developer",
        "ratio": 0.06,
        "exp_years_range": (2, 5),
        "skill_count_range": (6, 12),
        "noise_level": 0.03,
        "salary_range": (18_000_000, 32_000_000),
        "skill_pool_keys": ["mobile", "lang_basic", "api", "vcs"],
        "description": "Mobile developer chuyên phát triển Flutter/Native app",
    },
    {
        "persona_type": "qa_engineer",
        "ratio": 0.05,
        "exp_years_range": (1, 4),
        "skill_count_range": (5, 10),
        "noise_level": 0.05,
        "salary_range": (12_000_000, 25_000_000),
        "skill_pool_keys": ["qa_testing", "lang_basic", "api", "vcs", "soft"],
        "description": "Kỹ sư QA đảm bảo chất lượng, kiểm thử thủ công và tự động",
    },
    {
        "persona_type": "devops_infra",
        "ratio": 0.05,
        "exp_years_range": (3, 7),
        "skill_count_range": (8, 15),
        "noise_level": 0.02,
        "salary_range": (25_000_000, 50_000_000),
        "skill_pool_keys": ["devops", "database", "api", "vcs"],
        "description": "DevOps engineer tối ưu CI/CD và vận hành hạ tầng đám mây",
    },
    {
        "persona_type": "niche_specialist",
        "ratio": 0.04,
        "exp_years_range": (3, 8),
        "skill_count_range": (6, 12),
        "noise_level": 0.01,
        "salary_range": (30_000_000, 60_000_000),
        "skill_pool_keys": ["erp_sap", "database", "soft"],
        "description": "Chuyên gia tư vấn và triển khai giải pháp SAP/ERP",
    },
]

# Map persona_type → def for fast lookup
PERSONA_MAP: dict[str, PersonaDef] = {p["persona_type"]: p for p in PERSONA_DEFS}

# ============================================================
# Extension Distribution (500 CVs mới, index 500-999)
# Hardcoded để đảm bảo phân bổ chính xác, deterministic.
# Tổng = 500, thiết kế để cân bằng lại tổng thể 1000 CVs.
# ============================================================
EXTENSION_PERSONA_DISTRIBUTION: dict[str, int] = {
    "intern_blank": 25,
    "fresher_dreamer": 65,
    "junior_solid": 100,
    "mid_generalist": 85,
    "senior_specialist": 60,
    "senior_overqualified": 25,
    "career_changer": 25,
    "foreign_cv": 15,
    "mobile_developer": 60,  # 4 niche personas mới
    "qa_engineer": 50,
    "devops_infra": 50,
    "niche_specialist": 40,
    # Total: 600 raw → trimmed về 500 trong _generate_extension
}

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


# ============================================================
# Old personas snapshot (8 personas gốc) — dùng cho Vùng 1 (500 CVs đầu)
# Giữ nguyên ratio gốc để đảm bảo 100% cache hit với batch_001-batch_100
# ============================================================
_OLD_PERSONA_DEFS: list[PersonaDef] = [
    p
    for p in PERSONA_DEFS
    if p["persona_type"]
    not in ("mobile_developer", "qa_engineer", "devops_infra", "niche_specialist")
]
_OLD_PERSONA_RATIOS: dict[str, float] = {
    "intern_blank": 0.05,
    "fresher_dreamer": 0.15,
    "junior_solid": 0.30,
    "mid_generalist": 0.25,
    "senior_specialist": 0.12,
    "senior_overqualified": 0.05,
    "career_changer": 0.05,
    "foreign_cv": 0.03,
}


def _build_manifest_entries(
    rng: random.Random,
    persona_assignments: list[str],
    names: list[str],
    start_index: int = 0,
    start_batch_id: int = 1,
) -> list[CVManifestEntry]:
    """Helper: build manifest entries từ danh sách persona assignments + names."""
    manifest: list[CVManifestEntry] = []
    for offset, persona_type in enumerate(persona_assignments):
        p_def = PERSONA_MAP[persona_type]
        absolute_idx = start_index + offset
        batch_num = start_batch_id + (offset // 5)
        batch_id = f"batch_{batch_num:03d}"

        # Build skill pool
        raw_pool: list[str] = []
        for key in p_def["skill_pool_keys"]:
            raw_pool.extend(SKILL_CATALOG.get(key, []))
        unique_pool = list(dict.fromkeys(raw_pool))
        rng.shuffle(unique_pool)

        skill_min, skill_max = p_def["skill_count_range"]
        skill_count = rng.randint(skill_min, min(skill_max, len(unique_pool)))
        selected_skills = unique_pool[:skill_count]

        exp_min, exp_max = p_def["exp_years_range"]
        exp_years = rng.randint(exp_min, exp_max)
        province = rng.choices(_PROV_KEYS, weights=_PROV_VALS, k=1)[0]
        sal_range = p_def["salary_range"]

        entry: CVManifestEntry = {
            "cv_index": absolute_idx,
            "batch_id": batch_id,
            "persona": persona_type,
            "skill_pool": selected_skills,
            "salary_range": list(sal_range) if sal_range else None,
            "exp_years": exp_years,
            "province": province,
            "full_name": names[offset],
        }
        manifest.append(entry)
    return manifest


def generate_manifest(total_cv: int = 500, seed: int = 42) -> list[CVManifestEntry]:
    """Pre-compute toàn bộ CV assignments. Deterministic với seed=42.

    Hỗ trợ Extended Seeded Hybrid Manifest:
    - total_cv <= 500: Vùng 1 — 8 personas gốc, RNG(seed). 100% cache-safe với batch_001-100.
    - total_cv > 500 : Vùng 1 (index 0-499) đệ quy giữ bất biến,
                       Vùng 2 (index 500+) sinh với RNG(seed+1000), phân bổ EXTENSION_PERSONA_DISTRIBUTION.

    Returns list of CVManifestEntry (one per CV).
    """
    if total_cv <= 500:
        # ========= VÙNG 1: Logic nguyên bản cho 8 personas gốc =========
        rng = random.Random(seed)

        # Tính số lượng theo OLD ratio (không dùng ratio mới để tránh lệch cache)
        distribution: dict[str, int] = {}
        for persona_type, ratio in _OLD_PERSONA_RATIOS.items():
            distribution[persona_type] = int(total_cv * ratio)
        # Cân bằng remainder → thêm vào junior_solid
        assigned = sum(distribution.values())
        distribution["junior_solid"] += total_cv - assigned

        persona_assignments: list[str] = []
        for persona_type, count in distribution.items():
            persona_assignments.extend([persona_type] * count)
        rng.shuffle(persona_assignments)

        names = _generate_names(total_cv, rng)
        return _build_manifest_entries(
            rng, persona_assignments, names, start_index=0, start_batch_id=1
        )

    else:
        # ========= VÙNG 1: Lấy chính xác 500 entry đầu (bất biến) =========
        manifest_500 = generate_manifest(500, seed)  # 100% cache-safe
        used_names: set[str] = {e["full_name"] for e in manifest_500}

        # ========= VÙNG 2: Sinh N entry mới với RNG độc lập =========
        extra_count = min(total_cv - 500, 500)  # Tối đa 500 CVs mở rộng
        niche_rng = random.Random(seed + 1000)  # RNG riêng, tránh collision

        # Xây dựng danh sách persona assignments từ EXTENSION_PERSONA_DISTRIBUTION
        # Hardcoded để đảm bảo phân bổ chính xác
        raw_ext_assignments: list[str] = []
        for persona_type, count in EXTENSION_PERSONA_DISTRIBUTION.items():
            raw_ext_assignments.extend([persona_type] * count)

        # Trim về đúng extra_count
        niche_rng.shuffle(raw_ext_assignments)
        ext_assignments = raw_ext_assignments[:extra_count]

        # Generate tên mới, lọc trùng với 500 tên cũ
        # Sinh dư 20% để phòng trùng
        candidate_names = _generate_names(
            extra_count + extra_count // 5 + 20, niche_rng
        )
        unique_new_names: list[str] = []
        for name in candidate_names:
            if name not in used_names and name not in unique_new_names:
                unique_new_names.append(name)
            if len(unique_new_names) >= extra_count:
                break

        # Fallback nếu vẫn thiếu tên (cực kỳ hiếm)
        fallback_idx = 0
        while len(unique_new_names) < extra_count:
            unique_new_names.append(f"Ứng viên Mới {fallback_idx:04d}")
            fallback_idx += 1

        # start_batch_id = 101 (batch_101 → batch_200 cho 500 CVs mới)
        manifest_ext = _build_manifest_entries(
            niche_rng,
            ext_assignments,
            unique_new_names,
            start_index=500,
            start_batch_id=101,
        )
        return manifest_500 + manifest_ext


if __name__ == "__main__":
    from collections import Counter

    # --- Test Vùng 1: 500 CVs gốc (cache-safe) ---
    print("=== SANITY CHECK: generate_manifest(500) ===")
    m500 = generate_manifest(500)
    counts500 = Counter(e["persona"] for e in m500)
    print(f"Total: {len(m500)} entries")
    for p, c in sorted(counts500.items()):
        print(f"  {p:<25}: {c:>3}")
    batch_ids_500 = sorted(set(e["batch_id"] for e in m500))
    print(f"  Batch range: {batch_ids_500[0]} -> {batch_ids_500[-1]}")
    print(f"  cv_index range: {m500[0]['cv_index']} -> {m500[-1]['cv_index']}")

    # --- Test Vùng 2: 1000 CVs mở rộng ---
    print("\n=== SANITY CHECK: generate_manifest(1000) ===")
    m1000 = generate_manifest(1000)
    counts1000 = Counter(e["persona"] for e in m1000)
    counts_ext = Counter(e["persona"] for e in m1000[500:])
    print(
        f"Total: {len(m1000)} entries (Zone 1: {len(m500)}, Zone 2: {len(m1000)-len(m500)})"
    )
    print("  Persona distribution (full 1000):")
    for p, c in sorted(counts1000.items()):
        print(f"  {p:<25}: {c:>4} (ext={counts_ext.get(p,0):>3})")
    ext_batches = sorted(set(e["batch_id"] for e in m1000[500:]))
    print(f"  Extension batch range: {ext_batches[0]} -> {ext_batches[-1]}")
    print(
        f"  Extension cv_index range: {m1000[500]['cv_index']} -> {m1000[-1]['cv_index']}"
    )

    # --- Verify Zone 1 bất biến ---
    names_500 = [e["full_name"] for e in m500]
    names_in_1000_zone1 = [e["full_name"] for e in m1000[:500]]
    assert names_500 == names_in_1000_zone1, "FAIL: Zone 1 bi thay doi!"
    print("\n  [PASS] Zone 1 (500 CVs goc) hoan toan bat bien khi nang len 1000.")
    print(f"  First entry: {m1000[0]}")
    print(f"  Entry 500:   {m1000[500]}")
