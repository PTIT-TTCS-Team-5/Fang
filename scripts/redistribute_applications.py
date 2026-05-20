"""scripts/redistribute_applications.py — Phân bổ ứng viên thông minh & Mở khóa Chat RAG.

Giữ nguyên tất cả 500 applications hiện tại ở Job 1 (trường hợp đặc biệt).
Cho mỗi candidate, INSERT thêm 3 JOBAPPLICATION mới cho top-3 jobs phù hợp nhất.
Nhân bản đầy đủ CVPARSED + AIDOCUMENTCHUNK cho mỗi application mới.
INSERT AIINDEXJOB stat='SUCCESS' cho tất cả applications (gốc + mới).
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("redistribute")

from app.core.database import acquire_conn, db


async def redistribute():
    logger.info("=== BẮT ĐẦU PHÂN BỔ ỨNG VIÊN & MỞ KHÓA CHAT RAG ===")
    await db.connect()

    try:
        async with acquire_conn() as conn:
            # ─── 1. Fetch tất cả 20 Jobs ───
            job_rows = await conn.fetch("""
                SELECT j.jobPostId, j.title, j.description,
                       COALESCE(MIN(jl.minYears), 0) as min_years
                FROM JOBPOSTING j
                LEFT JOIN JOB_LEVEL_MAP jlm ON j.jobPostId = jlm.jobPostId
                LEFT JOIN JOBLEVEL jl ON jlm.levelId = jl.levelId
                GROUP BY j.jobPostId, j.title, j.description
            """)

            jobs = []
            for r in job_rows:
                job_id = r["jobpostid"]
                skill_rows = await conn.fetch(
                    "SELECT skillId FROM JOBREQUIREMENT WHERE jobPostId = $1", job_id
                )
                job_skills = {sr["skillid"] for sr in skill_rows}
                jobs.append(
                    {
                        "id": job_id,
                        "title": r["title"].lower(),
                        "min_years": r["min_years"],
                        "skills": job_skills,
                    }
                )

            logger.info(f"Loaded {len(jobs)} jobs.")

            # ─── 2. Fetch tất cả Candidates ───
            cand_rows = await conn.fetch("""
                SELECT c.userId, c.expyears, c.bio, u.fName, u.lName
                FROM CANDIDATE c
                JOIN "user" u ON c.userId = u.userId
            """)

            candidates = []
            for r in cand_rows:
                cand_id = r["userid"]
                skill_rows = await conn.fetch(
                    "SELECT skillId FROM CANDIDATESKILL WHERE userId = $1", cand_id
                )
                cand_skills = {sr["skillid"] for sr in skill_rows}

                candidates.append(
                    {
                        "id": cand_id,
                        "expyears": r["expyears"] or 0,
                        "bio": (r["bio"] or "").lower(),
                        "skills": cand_skills,
                        "name": f"{r['fname']} {r['lname']}",
                    }
                )

            logger.info(f"Loaded {len(candidates)} candidates.")

            # ─── 3. Tính điểm so khớp & chọn top-3 cho mỗi candidate ───
            def score_match(cand, job):
                """Local scoring: catalog skill overlap + title keywords + seniority."""
                skill_match = len(cand["skills"].intersection(job["skills"]))
                years_diff = job["min_years"] - cand["expyears"]
                exp_penalty = max(0, years_diff) * 4

                title_match = 0
                j_title = job["title"]
                c_bio = cand["bio"]

                keyword_groups = [
                    (
                        ["ai", "machine learning", "data scientist"],
                        ["ai", "machine", "data", "deep learning", "nlp"],
                    ),
                    (
                        ["devops", "cloud"],
                        ["devops", "docker", "aws", "kubernetes", "infra"],
                    ),
                    (
                        ["frontend", "react"],
                        ["frontend", "react", "vue", "angular", "ui"],
                    ),
                    (
                        ["mobile", "flutter"],
                        ["mobile", "flutter", "dart", "android", "ios"],
                    ),
                    (
                        ["backend", "java", "spring"],
                        ["backend", "java", "spring", "springboot", "node"],
                    ),
                    (["qa", "testing"], ["qa", "testing", "automation", "manual"]),
                    (["sap", "erp"], ["sap", "erp", "consultant"]),
                    (
                        ["support", "system admin"],
                        ["support", "system admin", "helpdesk", "network"],
                    ),
                    (
                        ["security", "cybersec"],
                        ["security", "penetration", "firewall", "soc"],
                    ),
                    (
                        ["project manager", "scrum"],
                        ["project", "scrum", "agile", "management"],
                    ),
                    (
                        ["python", "django", "flask"],
                        ["python", "django", "flask", "fastapi"],
                    ),
                    ([".net", "c#"], [".net", "c#", "asp.net", "blazor"]),
                ]

                for job_kws, cand_kws in keyword_groups:
                    if any(kw in j_title for kw in job_kws):
                        if any(kw in c_bio for kw in cand_kws):
                            title_match += 30

                return skill_match * 10 - exp_penalty + title_match

            # Tìm Job 1 ID
            job1_id = None
            for j in jobs:
                if j["id"] == 1:
                    job1_id = 1
                    break
            if job1_id is None:
                # Fallback: lấy job đầu tiên theo ID
                job1_id = min(j["id"] for j in jobs)
                logger.warning(
                    f"Job ID 1 không tồn tại, dùng Job ID {job1_id} làm đặc biệt."
                )

            logger.info(f"Job đặc biệt (giữ nguyên): Job ID {job1_id}")

            # Non-special jobs (loại trừ Job 1)
            other_jobs = [j for j in jobs if j["id"] != job1_id]

            redistribution_plan = []
            for c in candidates:
                scores = []
                for j in other_jobs:
                    s = score_match(c, j)
                    scores.append((j["id"], s))
                # Sắp xếp giảm dần theo điểm, lấy top 3
                scores.sort(key=lambda x: x[1], reverse=True)
                top3 = scores[:3]
                redistribution_plan.append(
                    {
                        "cand_id": c["id"],
                        "name": c["name"],
                        "top3": top3,
                    }
                )

            logger.info(
                f"Đã tính top-3 jobs cho {len(redistribution_plan)} candidates."
            )

            # ─── 4. Thực thi INSERT ───
            new_apps_created = 0
            cvparsed_copied = 0
            chunks_copied = 0
            aiindex_inserted = 0

            for idx, plan in enumerate(redistribution_plan):
                cand_id = plan["cand_id"]

                # Lấy application gốc (Job 1) để copy dữ liệu
                orig_app = await conn.fetchrow(
                    """
                    SELECT jobAppId, cvSnapUrl, stat, coverLetter
                    FROM JOBAPPLICATION
                    WHERE candidateId = $1 AND jobPostId = $2
                    LIMIT 1
                """,
                    cand_id,
                    job1_id,
                )

                if not orig_app:
                    logger.warning(
                        f"Candidate {cand_id} không có application ở Job {job1_id}, bỏ qua."
                    )
                    continue

                orig_app_id = orig_app["jobappid"]
                orig_cvsnapurl = orig_app["cvsnapurl"]
                orig_stat = orig_app["stat"]
                orig_cover = orig_app["coverletter"]

                # Lấy CVPARSED gốc
                orig_cv = await conn.fetchrow(
                    """
                    SELECT rawText, parsedJson, parserVer
                    FROM CVPARSED
                    WHERE jobAppId = $1
                """,
                    orig_app_id,
                )

                # Lấy tất cả chunks gốc
                orig_chunks = await conn.fetch(
                    """
                    SELECT sourceType, content, chunkIndex, tokenCount, metadata, embedding
                    FROM AIDOCUMENTCHUNK
                    WHERE jobAppId = $1
                    ORDER BY chunkIndex
                """,
                    orig_app_id,
                )

                # INSERT AIINDEXJOB cho application gốc (Job 1)
                existing_idx = await conn.fetchval(
                    "SELECT indexJobId FROM AIINDEXJOB WHERE jobAppId = $1 LIMIT 1",
                    orig_app_id,
                )
                if not existing_idx:
                    await conn.execute(
                        """
                        INSERT INTO AIINDEXJOB (jobAppId, stat, finishedAt)
                        VALUES ($1, 'SUCCESS', CURRENT_TIMESTAMP)
                    """,
                        orig_app_id,
                    )
                    aiindex_inserted += 1

                # INSERT 3 applications mới cho top-3 jobs
                for job_id, match_score in plan["top3"]:
                    # 4.1 INSERT JOBAPPLICATION
                    new_app_id = await conn.fetchval(
                        """
                        INSERT INTO JOBAPPLICATION (candidateId, jobPostId, stat, cvSnapUrl, coverLetter)
                        VALUES ($1, $2, $3, $4, $5)
                        RETURNING jobAppId
                    """,
                        cand_id,
                        job_id,
                        orig_stat,
                        orig_cvsnapurl,
                        orig_cover,
                    )
                    new_apps_created += 1

                    # 4.2 INSERT CVPARSED (nhân bản)
                    if orig_cv:
                        await conn.execute(
                            """
                            INSERT INTO CVPARSED (jobAppId, rawText, parsedJson, parserVer)
                            VALUES ($1, $2, $3, $4)
                        """,
                            new_app_id,
                            orig_cv["rawtext"],
                            orig_cv["parsedjson"],
                            orig_cv["parserver"],
                        )
                        cvparsed_copied += 1

                    # 4.3 INSERT AIDOCUMENTCHUNK (nhân bản với embeddings)
                    for chunk in orig_chunks:
                        await conn.execute(
                            """
                            INSERT INTO AIDOCUMENTCHUNK
                                (jobAppId, sourceType, content, chunkIndex, tokenCount, metadata, embedding)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                            new_app_id,
                            chunk["sourcetype"],
                            chunk["content"],
                            chunk["chunkindex"],
                            chunk["tokencount"],
                            chunk["metadata"],
                            chunk["embedding"],
                        )
                        chunks_copied += 1

                    # 4.4 INSERT AIINDEXJOB cho application mới
                    await conn.execute(
                        """
                        INSERT INTO AIINDEXJOB (jobAppId, stat, finishedAt)
                        VALUES ($1, 'SUCCESS', CURRENT_TIMESTAMP)
                    """,
                        new_app_id,
                    )
                    aiindex_inserted += 1

                # Progress log
                if (
                    idx < 5
                    or (idx + 1) % 100 == 0
                    or idx == len(redistribution_plan) - 1
                ):
                    top3_str = ", ".join(f"Job {jid}({sc})" for jid, sc in plan["top3"])
                    logger.info(
                        f"[{idx+1}/{len(redistribution_plan)}] '{plan['name']}' → {top3_str}"
                    )

            # ─── 5. Thống kê kết quả ───
            logger.info("=" * 60)
            logger.info("KẾT QUẢ PHÂN BỔ:")
            logger.info(f"  Applications mới tạo:    {new_apps_created}")
            logger.info(f"  CVPARSED nhân bản:       {cvparsed_copied}")
            logger.info(f"  Chunks nhân bản:         {chunks_copied}")
            logger.info(f"  AIINDEXJOB inserted:     {aiindex_inserted}")
            logger.info("=" * 60)

            # Bảng phân bổ chi tiết
            dist_stats = await conn.fetch("""
                SELECT ja.jobPostId, j.title, COUNT(*) as count
                FROM JOBAPPLICATION ja
                JOIN JOBPOSTING j ON ja.jobPostId = j.jobPostId
                GROUP BY ja.jobPostId, j.title
                ORDER BY ja.jobPostId
            """)

            print(
                "\n╔════════════════════════════════════════════════════════════════╗"
            )
            print("║          BẢNG PHÂN BỔ ỨNG VIÊN THEO CÔNG VIỆC               ║")
            print("╠═════╦════════════════════════════════════════════╦════════════╣")
            print("║ ID  ║ Tên Công Việc                             ║ Số Đơn    ║")
            print("╠═════╬════════════════════════════════════════════╬════════════╣")
            total_apps = 0
            for row in dist_stats:
                jid = row["jobpostid"]
                title = row["title"][:40]
                count = row["count"]
                total_apps += count
                marker = " ★" if jid == job1_id else ""
                print(f"║ {jid:>3} ║ {title:<42} ║ {count:>5}{marker:>4} ║")
            print("╠═════╬════════════════════════════════════════════╬════════════╣")
            print(f"║     ║ {'TỔNG CỘNG':<42} ║ {total_apps:>9} ║")
            print("╚═════╩════════════════════════════════════════════╩════════════╝")
            print("  ★ = Job đặc biệt (giữ nguyên tất cả applications gốc)\n")

            # Verify AIINDEXJOB
            total_idx = await conn.fetchval(
                "SELECT COUNT(*) FROM AIINDEXJOB WHERE stat = 'SUCCESS'"
            )
            logger.info(f"AIINDEXJOB records với stat='SUCCESS': {total_idx}")

            logger.info("=== HOÀN THÀNH PHÂN BỔ ỨNG VIÊN & MỞ KHÓA CHAT RAG ===")

    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(redistribute())
