"""Read-only tools for the JobPosting Agent runtime (FANG C3 WS3)."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

from app.core.config import settings
from app.core.database import acquire_conn
from app.services.nmaiex_mapper_service import PROFICIENCY_LEVELS
from app.services.nmaiex_ranking_service import rank_candidates_for_job

ToolResult = dict[str, Any]

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
PROFICIENCY_ORDER = PROFICIENCY_LEVELS
MAX_SNIPPET_CHARS = 200
MAX_RAW_CV_CHARS = 6000


def _warn(
    warning_type: str, message: str, suggestion: str | None = None
) -> dict[str, str | None]:
    return {"type": warning_type, "message": message, "suggestion": suggestion}


def _result(
    *,
    ok: bool,
    data: Any = None,
    source: dict[str, Any] | None = None,
    warnings: list[dict[str, Any]] | None = None,
    error: dict[str, str] | None = None,
) -> ToolResult:
    return {
        "ok": ok,
        "data": _json_safe(data),
        "source": source or {},
        "warnings": warnings or [],
        "error": error,
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    return value


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def _get(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return default


def mask_email(value: str | None) -> str | None:
    if not value:
        return value
    local, _, domain = value.partition("@")
    if not domain:
        return "***"
    prefix = local[:3] if len(local) > 3 else local[:1]
    return f"{prefix}***@{domain}"


def mask_phone(value: str | None) -> str | None:
    if not value:
        return value
    digits = re.sub(r"\D", "", value)
    if not digits:
        return "***"
    return f"***{digits[-4:]}"


def mask_pii_text(text: str | None) -> str:
    if not text:
        return ""
    masked = EMAIL_RE.sub(lambda m: mask_email(m.group(0)) or "***", text)
    masked = PHONE_RE.sub(lambda m: mask_phone(m.group(0)) or "***", masked)
    return masked


def _truncate(text: str | None, max_chars: int) -> str:
    if not text:
        return ""
    text = str(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _load_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


async def validate_job_application_scope(
    job_post_id: int, job_app_id: int
) -> dict[str, Any] | None:
    """Return application metadata only when the application belongs to the scoped job."""
    query = """
        SELECT
            ja.jobAppId AS job_app_id,
            ja.jobPostId AS job_post_id,
            ja.candidateId AS candidate_id,
            ja.stat AS application_status,
            ja.appliedAt AS applied_at,
            u.fName || ' ' || u.lName AS candidate_name
        FROM JOBAPPLICATION ja
        JOIN "user" u ON u.userId = ja.candidateId
        WHERE ja.jobAppId = $1 AND ja.jobPostId = $2
    """
    async with acquire_conn() as conn:
        row = await conn.fetchrow(query, job_app_id, job_post_id)
    return _row_to_dict(row) if row else None


async def _resolve_language_filter(language: str | None) -> dict[str, str | None]:
    if not language:
        return {"query": None, "code": None, "name": None}
    normalized = language.strip().lower()
    async with acquire_conn() as conn:
        row = await conn.fetchrow(
            """
            SELECT langCode AS lang_code, langName AS lang_name
            FROM LANGUAGE
            WHERE lower(langCode) = $1 OR lower(langName) = $1
            LIMIT 1
            """,
            normalized,
        )
    if row:
        d = _row_to_dict(row)
        return {
            "query": normalized,
            "code": (_get(d, "lang_code", "langcode") or "").lower(),
            "name": _get(d, "lang_name", "langname"),
        }
    return {"query": normalized, "code": normalized, "name": language}


async def _fetch_languages_for_candidates(
    candidate_ids: list[int],
) -> dict[int, list[dict[str, Any]]]:
    if not candidate_ids:
        return {}
    query = """
        SELECT
            cl.userId AS candidate_id,
            cl.langId AS lang_id,
            l.langCode AS lang_code,
            l.langName AS lang_name,
            cl.rawName AS raw_name,
            cl.proficiency,
            cl.rawProficiency AS raw_proficiency,
            cl.certification
        FROM CANDIDATELANGUAGE cl
        LEFT JOIN LANGUAGE l ON l.langId = cl.langId
        WHERE cl.userId = ANY($1::int[])
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch(query, candidate_ids)

    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        d = _row_to_dict(row)
        candidate_id = _get(d, "candidate_id", "candidateid")
        grouped.setdefault(candidate_id, []).append(
            {
                "lang_id": _get(d, "lang_id", "langid"),
                "lang_code": _get(d, "lang_code", "langcode"),
                "name": _get(d, "lang_name", "langname")
                or _get(d, "raw_name", "rawname"),
                "raw_name": _get(d, "raw_name", "rawname"),
                "proficiency": d.get("proficiency") or "BASIC",
                "raw_proficiency": _get(d, "raw_proficiency", "rawproficiency"),
                "certification": d.get("certification"),
            }
        )
    return grouped


def _language_matches(
    languages: list[dict[str, Any]],
    language_filter: dict[str, str | None],
    min_proficiency: str | None,
) -> tuple[bool, dict[str, Any] | None]:
    if not language_filter.get("query") and not min_proficiency:
        return True, None
    if not languages:
        return True, _warn(
            "data_quality",
            "Ứng viên chưa có dữ liệu ngôn ngữ chuẩn hóa; được giữ lại theo chính sách inclusive.",
            "Chạy re-enrichment để cải thiện độ chính xác bộ lọc ngôn ngữ.",
        )

    target_code = language_filter.get("code")
    target_query = language_filter.get("query")
    min_level = PROFICIENCY_ORDER.get((min_proficiency or "BASIC").upper(), 1)
    has_unknown = False

    for lang in languages:
        lang_code = (lang.get("lang_code") or "").lower()
        lang_name = (lang.get("name") or "").lower()
        raw_name = (lang.get("raw_name") or "").lower()
        if not lang_code:
            has_unknown = True
            continue
        name_matches = (
            not target_query
            or lang_code == target_code
            or target_query in lang_name
            or target_query in raw_name
        )
        level_matches = (
            PROFICIENCY_ORDER.get((lang.get("proficiency") or "BASIC").upper(), 1)
            >= min_level
        )
        if name_matches and level_matches:
            return True, None

    if has_unknown:
        return True, _warn(
            "data_quality",
            "Một số ngôn ngữ của ứng viên chưa map được vào LANGUAGE.langId; ứng viên được giữ lại.",
            "Kiểm tra rawName trong CANDIDATELANGUAGE hoặc chạy mapping bổ sung.",
        )
    return False, None


def _passes_filters(
    item: dict[str, Any],
    filters: dict[str, Any],
    language_filter: dict[str, str | None],
) -> tuple[bool, list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    status = filters.get("status")
    if (
        status
        and str(item.get("application_status", "")).lower() != str(status).lower()
    ):
        return False, warnings

    prov_filter = filters.get("province_id", filters.get("provId"))
    if (
        prov_filter
        and item.get("province_id")
        and str(item.get("province_id")) != str(prov_filter)
    ):
        return False, warnings
    if prov_filter and not item.get("province_id"):
        warnings.append(
            _warn(
                "data_quality",
                "Ứng viên chưa có tỉnh/thành chuẩn hóa; được giữ lại theo chính sách inclusive.",
                "Chạy re-enrichment để cập nhật user.provId.",
            )
        )

    min_score = filters.get("min_overall_score")
    if min_score is not None:
        try:
            if float(item.get("overall_score") or 0) < float(min_score):
                return False, warnings
        except (TypeError, ValueError):
            return False, warnings

    min_lang = filters.get("min_language_proficiency")
    lang_ok, lang_warning = _language_matches(
        item.get("languages") or [], language_filter, min_lang
    )
    if lang_warning:
        warnings.append(lang_warning)
    if not lang_ok:
        return False, warnings
    return True, warnings


async def _fetch_application_enrichment(
    job_post_id: int, candidate_ids: list[int]
) -> dict[int, dict[str, Any]]:
    if not candidate_ids:
        return {}
    query = """
        SELECT
            ja.jobAppId AS job_app_id,
            ja.candidateId AS candidate_id,
            ja.stat AS application_status,
            ja.appliedAt AS applied_at,
            u.provId AS province_id,
            p.provName AS province_name,
            c.expyears AS years_experience
        FROM JOBAPPLICATION ja
        JOIN CANDIDATE c ON c.userId = ja.candidateId
        JOIN "user" u ON u.userId = ja.candidateId
        LEFT JOIN PROVINCE p ON p.provId = u.provId
        WHERE ja.jobPostId = $1 AND ja.candidateId = ANY($2::int[])
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch(query, job_post_id, candidate_ids)
    return {
        _get(_row_to_dict(r), "candidate_id", "candidateid"): _row_to_dict(r)
        for r in rows
    }


async def get_job_posting_context(job_post_id: int) -> ToolResult:
    """Read compact job posting context, requirements, and application counts."""
    warnings: list[dict[str, Any]] = []
    async with acquire_conn() as conn:
        job = await conn.fetchrow(
            """
            SELECT
                jp.jobPostId AS job_post_id,
                jp.title,
                jp.description,
                jp.minSalary AS min_salary,
                jp.maxSalary AS max_salary,
                jp.workMode AS work_mode,
                jp.workLoc AS work_location,
                jp.provId AS province_id,
                p.provName AS province_name,
                jp.createdAt AS created_at,
                jp.expAt AS expires_at,
                c.compId AS company_id,
                c.compName AS company_name
            FROM JOBPOSTING jp
            JOIN COMPANY c ON c.compId = jp.compId
            LEFT JOIN PROVINCE p ON p.provId = jp.provId
            WHERE jp.jobPostId = $1
            """,
            job_post_id,
        )
        if not job:
            return _result(
                ok=False,
                source={"tool": "get_job_posting_context", "job_post_id": job_post_id},
                error={"code": "NOT_FOUND", "message": "JobPosting không tồn tại."},
            )

        status_counts = await conn.fetch(
            """
            SELECT stat, COUNT(*) AS count
            FROM JOBAPPLICATION
            WHERE jobPostId = $1
            GROUP BY stat
            """,
            job_post_id,
        )
        skills = await conn.fetch(
            """
            SELECT s.skillId AS skill_id, s.skillName AS skill_name
            FROM JOBREQUIREMENT jr
            JOIN SKILL s ON s.skillId = jr.skillId
            WHERE jr.jobPostId = $1
            ORDER BY s.skillName
            """,
            job_post_id,
        )
        languages = await conn.fetch(
            """
            SELECT l.langId AS lang_id, l.langCode AS lang_code, l.langName AS lang_name,
                   r.reqType AS requirement_type, r.minLevel AS min_level
            FROM JOB_LANG_REQUIREMENT r
            JOIN LANGUAGE l ON l.langId = r.langId
            WHERE r.jobPostId = $1
            ORDER BY r.reqType, l.langName
            """,
            job_post_id,
        )

    job_d = _row_to_dict(job)
    counts = {
        _get(_row_to_dict(r), "stat"): _get(_row_to_dict(r), "count", default=0)
        for r in status_counts
    }
    total = sum(int(v or 0) for v in counts.values())
    data = {
        "job_posting": {
            "job_post_id": _get(job_d, "job_post_id", "jobpostid"),
            "title": job_d.get("title"),
            "description": _truncate(job_d.get("description"), 2000),
            "salary": {
                "min": _get(job_d, "min_salary", "minsalary"),
                "max": _get(job_d, "max_salary", "maxsalary"),
            },
            "work_mode": _get(job_d, "work_mode", "workmode"),
            "work_location": _get(job_d, "work_location", "workloc"),
            "province": {
                "id": _get(job_d, "province_id", "provid"),
                "name": _get(job_d, "province_name", "provname"),
            },
            "company": {
                "id": _get(job_d, "company_id", "compid"),
                "name": _get(job_d, "company_name", "compname"),
            },
            "created_at": _get(job_d, "created_at", "createdat"),
            "expires_at": _get(job_d, "expires_at", "expat"),
        },
        "application_counts": {"total": total, "by_status": counts},
        "requirements": {
            "skills": [
                {
                    "skill_id": _get(_row_to_dict(r), "skill_id", "skillid"),
                    "name": _get(_row_to_dict(r), "skill_name", "skillname"),
                }
                for r in skills
            ],
            "languages": [
                {
                    "lang_id": _get(_row_to_dict(r), "lang_id", "langid"),
                    "lang_code": _get(_row_to_dict(r), "lang_code", "langcode"),
                    "name": _get(_row_to_dict(r), "lang_name", "langname"),
                    "requirement_type": _get(
                        _row_to_dict(r), "requirement_type", "reqtype"
                    ),
                    "min_level": _get(_row_to_dict(r), "min_level", "minlevel"),
                }
                for r in languages
            ],
        },
    }
    if not data["requirements"]["languages"]:
        warnings.append(
            _warn(
                "data_quality",
                "Tin tuyển dụng chưa khai báo yêu cầu ngôn ngữ chuẩn hóa.",
            )
        )
    return _result(
        ok=True,
        data=data,
        source={
            "tool": "get_job_posting_context",
            "tables": [
                "JOBPOSTING",
                "COMPANY",
                "PROVINCE",
                "JOBAPPLICATION",
                "JOBREQUIREMENT",
                "JOB_LANG_REQUIREMENT",
            ],
            "job_post_id": job_post_id,
        },
        warnings=warnings,
    )


async def get_job_candidate_ranking(
    job_post_id: int,
    limit: int = 10,
    filters: dict[str, Any] | None = None,
) -> ToolResult:
    """Return ranked candidates for the scoped job posting."""
    filters = filters or {}
    warnings: list[dict[str, Any]] = []
    requested_limit = limit or settings.jobposting_agent_default_top_n
    capped_limit = max(
        1, min(int(requested_limit), settings.jobposting_agent_hr_max_top_n)
    )
    if requested_limit > capped_limit:
        warnings.append(
            _warn(
                "limit_capped",
                f"Yêu cầu {requested_limit} ứng viên vượt giới hạn; đã giới hạn còn {capped_limit}.",
                "Dùng bộ lọc hoặc yêu cầu top N nhỏ hơn.",
            )
        )

    province_filter = filters.get("province_id", filters.get("provId"))
    ranking = await rank_candidates_for_job(
        job_post_id,
        limit=max(capped_limit, settings.jobposting_agent_hr_max_top_n),
        province_id=province_filter,
    )
    base_results = list((ranking or {}).get("results") or [])
    candidate_ids = [
        int(r["candidate_id"])
        for r in base_results
        if r.get("candidate_id") is not None
    ]
    app_meta = await _fetch_application_enrichment(job_post_id, candidate_ids)
    languages_by_candidate = await _fetch_languages_for_candidates(candidate_ids)
    lang_filter = await _resolve_language_filter(filters.get("language"))

    ranked: list[dict[str, Any]] = []
    working_set_filter = {
        int(x) for x in filters.get("working_set_job_app_ids", []) if str(x).isdigit()
    }
    seen_warnings: set[str] = set()

    for idx, row in enumerate(base_results, start=1):
        candidate_id = int(row["candidate_id"])
        meta = app_meta.get(candidate_id)
        if not meta:
            warnings.append(
                _warn(
                    "data_quality",
                    f"Không tìm thấy JOBAPPLICATION cho candidateId={candidate_id} trong jobPostId={job_post_id}.",
                )
            )
            continue
        job_app_id = _get(meta, "job_app_id", "jobappid")
        if working_set_filter and job_app_id not in working_set_filter:
            continue
        languages = languages_by_candidate.get(candidate_id, [])
        item = {
            "job_app_id": job_app_id,
            "candidate_id": candidate_id,
            "candidate_name": row.get("candidate_name"),
            "ranking_position": idx,
            "overall_score": row.get("match_score"),
            "score_breakdown": row.get("score_breakdown") or {},
            "application_status": _get(meta, "application_status", "stat"),
            "applied_at": _get(meta, "applied_at", "appliedat"),
            "years_experience": _get(meta, "years_experience", "expyears"),
            "province_id": _get(meta, "province_id", "provid"),
            "province_name": _get(meta, "province_name", "provname"),
            "languages": languages,
        }
        keep, filter_warnings = _passes_filters(item, filters, lang_filter)
        for w in filter_warnings:
            key = f"{w.get('type')}:{w.get('message')}"
            if key not in seen_warnings:
                warnings.append(w)
                seen_warnings.add(key)
        if keep:
            ranked.append(item)
        if len(ranked) >= capped_limit:
            break

    data = {
        "candidates": ranked,
        "total_available": (ranking or {}).get("total_candidates", len(base_results)),
        "returned": len(ranked),
        "requested_limit": requested_limit,
        "limit": capped_limit,
        "filters_applied": filters,
    }
    return _result(
        ok=True,
        data=data,
        source={
            "tool": "get_job_candidate_ranking",
            "service": "nmaiex_ranking_service.rank_candidates_for_job",
            "job_post_id": job_post_id,
        },
        warnings=warnings,
    )


async def _fetch_candidate_summaries(
    job_app_ids: list[int],
) -> dict[int, dict[str, Any]]:
    if not job_app_ids:
        return {}
    query = """
        SELECT
            ja.jobAppId AS job_app_id,
            ja.candidateId AS candidate_id,
            u.fName || ' ' || u.lName AS candidate_name,
            c.expyears AS years_experience,
            p.provName AS province_name,
            u.provId AS province_id
        FROM JOBAPPLICATION ja
        JOIN CANDIDATE c ON c.userId = ja.candidateId
        JOIN "user" u ON u.userId = ja.candidateId
        LEFT JOIN PROVINCE p ON p.provId = u.provId
        WHERE ja.jobAppId = ANY($1::int[])
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch(query, job_app_ids)
    return {
        _get(_row_to_dict(r), "job_app_id", "jobappid"): _row_to_dict(r) for r in rows
    }


async def search_job_applications_text(
    job_post_id: int,
    query: str,
    limit: int = 10,
    filters: dict[str, Any] | None = None,
) -> ToolResult:
    """Search CV raw text scoped to one job posting."""
    filters = filters or {}
    if not query or not query.strip():
        return _result(
            ok=False,
            source={"tool": "search_job_applications_text", "job_post_id": job_post_id},
            error={
                "code": "INVALID_QUERY",
                "message": "Query tìm kiếm không được để trống.",
            },
        )

    capped_limit = max(
        1,
        min(
            int(limit or settings.jobposting_agent_default_top_n),
            settings.jobposting_agent_hr_max_top_n,
        ),
    )
    search_text = query.strip()
    async with acquire_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT
                ja.jobAppId AS job_app_id,
                ja.candidateId AS candidate_id,
                ja.stat AS application_status,
                cv.rawText AS raw_text,
                u.provId AS province_id,
                p.provName AS province_name,
                u.fName || ' ' || u.lName AS candidate_name,
                c.expyears AS years_experience
            FROM JOBAPPLICATION ja
            JOIN CVPARSED cv ON cv.jobAppId = ja.jobAppId
            JOIN CANDIDATE c ON c.userId = ja.candidateId
            JOIN "user" u ON u.userId = ja.candidateId
            LEFT JOIN PROVINCE p ON p.provId = u.provId
            WHERE ja.jobPostId = $1 AND cv.rawText ILIKE $2
            ORDER BY ja.appliedAt DESC
            LIMIT $3
            """,
            job_post_id,
            f"%{search_text}%",
            max(capped_limit * 3, capped_limit),
        )

    candidate_ids = [_get(_row_to_dict(r), "candidate_id", "candidateid") for r in rows]
    langs_by_candidate = await _fetch_languages_for_candidates(
        [int(cid) for cid in candidate_ids if cid is not None]
    )
    lang_filter = await _resolve_language_filter(filters.get("language"))
    warnings: list[dict[str, Any]] = []
    seen_warnings: set[str] = set()
    results: list[dict[str, Any]] = []

    for row in rows:
        d = _row_to_dict(row)
        candidate_id = _get(d, "candidate_id", "candidateid")
        raw_text = _get(d, "raw_text", "rawtext") or ""
        idx = raw_text.lower().find(search_text.lower())
        start = max(idx - 80, 0) if idx >= 0 else 0
        snippet = mask_pii_text(
            _truncate(raw_text[start : start + MAX_SNIPPET_CHARS], MAX_SNIPPET_CHARS)
        )
        item = {
            "job_app_id": _get(d, "job_app_id", "jobappid"),
            "candidate_id": candidate_id,
            "candidate_name": _get(d, "candidate_name", "candidate_name"),
            "application_status": _get(d, "application_status", "stat"),
            "province_id": _get(d, "province_id", "provid"),
            "province_name": _get(d, "province_name", "provname"),
            "years_experience": _get(d, "years_experience", "expyears"),
            "languages": langs_by_candidate.get(candidate_id, []),
            "matched_snippets": [snippet] if snippet else [],
        }
        keep, filter_warnings = _passes_filters(item, filters, lang_filter)
        for w in filter_warnings:
            key = f"{w.get('type')}:{w.get('message')}"
            if key not in seen_warnings:
                warnings.append(w)
                seen_warnings.add(key)
        if keep:
            results.append(item)
        if len(results) >= capped_limit:
            break

    return _result(
        ok=True,
        data={
            "results": results,
            "total_matches": len(results),
            "query_used": search_text,
            "limit": capped_limit,
            "filters_applied": filters,
        },
        source={
            "tool": "search_job_applications_text",
            "tables": ["JOBAPPLICATION", "CVPARSED"],
            "job_post_id": job_post_id,
        },
        warnings=warnings,
    )


async def _get_application_detail(
    job_post_id: int, job_app_id: int
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    scope = await validate_job_application_scope(job_post_id, job_app_id)
    if not scope:
        return None, None
    query = """
        SELECT
            ja.jobAppId AS job_app_id,
            ja.jobPostId AS job_post_id,
            ja.candidateId AS candidate_id,
            ja.stat AS application_status,
            ja.appliedAt AS applied_at,
            u.fName || ' ' || u.lName AS candidate_name,
            u.email,
            u.phone,
            u.provId AS province_id,
            p.provName AS province_name,
            c.bio,
            c.expyears AS years_experience,
            cv.rawText AS raw_text,
            cv.parsedJson AS parsed_json
        FROM JOBAPPLICATION ja
        JOIN CANDIDATE c ON c.userId = ja.candidateId
        JOIN "user" u ON u.userId = ja.candidateId
        LEFT JOIN PROVINCE p ON p.provId = u.provId
        LEFT JOIN CVPARSED cv ON cv.jobAppId = ja.jobAppId
        WHERE ja.jobAppId = $1 AND ja.jobPostId = $2
    """
    async with acquire_conn() as conn:
        row = await conn.fetchrow(query, job_app_id, job_post_id)
    return scope, _row_to_dict(row) if row else None


async def get_job_application_summary(job_post_id: int, job_app_id: int) -> ToolResult:
    """Return compact summary for one scoped job application."""
    scope, detail = await _get_application_detail(job_post_id, job_app_id)
    if not scope or not detail:
        return _result(
            ok=False,
            source={
                "tool": "get_job_application_summary",
                "job_post_id": job_post_id,
                "job_app_id": job_app_id,
            },
            error={
                "code": "ACCESS_DENIED",
                "message": "Ứng viên không thuộc tin tuyển dụng hiện tại hoặc không tồn tại.",
            },
        )

    candidate_id = _get(detail, "candidate_id", "candidateid")
    langs = await _fetch_languages_for_candidates([candidate_id])
    parsed = _load_json(_get(detail, "parsed_json", "parsedjson")) or {}
    skills = parsed.get("skills") or []
    certificates = parsed.get("certificates") or []
    education = parsed.get("education") or []
    experience = parsed.get("experience") or []
    data = {
        "job_app_id": job_app_id,
        "candidate_id": candidate_id,
        "candidate_name": _get(detail, "candidate_name", "candidate_name"),
        "application_status": _get(detail, "application_status", "stat"),
        "applied_at": _get(detail, "applied_at", "appliedat"),
        "years_experience": _get(detail, "years_experience", "expyears"),
        "province": {
            "id": _get(detail, "province_id", "provid"),
            "name": _get(detail, "province_name", "provname"),
        },
        "top_skills": skills[:10] if isinstance(skills, list) else [],
        "languages": langs.get(candidate_id, []),
        "education_highlights": education[:3] if isinstance(education, list) else [],
        "experience_highlights": experience[:3] if isinstance(experience, list) else [],
        "certifications": certificates[:5] if isinstance(certificates, list) else [],
        "summary": _truncate(parsed.get("summary") or detail.get("bio"), 1000),
    }
    return _result(
        ok=True,
        data=data,
        source={
            "tool": "get_job_application_summary",
            "tables": ["JOBAPPLICATION", "CVPARSED", "CANDIDATELANGUAGE"],
            "job_post_id": job_post_id,
            "job_app_id": job_app_id,
        },
    )


def _redact_personal_info(candidate_info: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redacted = []
    for item in candidate_info:
        if not isinstance(item, dict):
            continue
        redacted.append(
            {
                "fullName": item.get("fullName"),
                "emails": [mask_email(e) for e in item.get("emails", [])],
                "phones": [mask_phone(p) for p in item.get("phones", [])],
                "location": "REDACTED" if item.get("location") else None,
            }
        )
    return redacted


async def get_job_application_full_cv(job_post_id: int, job_app_id: int) -> ToolResult:
    """Return a PII-masked full CV view for one scoped application."""
    scope, detail = await _get_application_detail(job_post_id, job_app_id)
    if not scope or not detail:
        return _result(
            ok=False,
            source={
                "tool": "get_job_application_full_cv",
                "job_post_id": job_post_id,
                "job_app_id": job_app_id,
            },
            error={
                "code": "ACCESS_DENIED",
                "message": "Ứng viên không thuộc tin tuyển dụng hiện tại hoặc không tồn tại.",
            },
        )

    parsed = _load_json(_get(detail, "parsed_json", "parsedjson")) or {}
    candidate_info = parsed.get("candidateInfo") or []
    raw_text = mask_pii_text(
        _get(detail, "raw_text", "rawtext") or parsed.get("rawText") or ""
    )
    data = {
        "job_app_id": job_app_id,
        "candidate_id": _get(detail, "candidate_id", "candidateid"),
        "candidate_name": _get(detail, "candidate_name", "candidate_name"),
        "personal_info": _redact_personal_info(
            candidate_info if isinstance(candidate_info, list) else []
        ),
        "profile_contact": {
            "email": mask_email(detail.get("email")),
            "phone": mask_phone(detail.get("phone")),
            "province": _get(detail, "province_name", "provname"),
            "address": "REDACTED",
        },
        "summary": _truncate(parsed.get("summary") or "", 1500),
        "education": parsed.get("education") or [],
        "experience": parsed.get("experience") or [],
        "skills": parsed.get("skills") or [],
        "languages": parsed.get("languages") or [],
        "certificates": parsed.get("certificates") or [],
        "raw_text_excerpt": _truncate(raw_text, MAX_RAW_CV_CHARS),
        "truncated": len(raw_text) > MAX_RAW_CV_CHARS,
    }
    return _result(
        ok=True,
        data=data,
        source={
            "tool": "get_job_application_full_cv",
            "tables": ["JOBAPPLICATION", "CVPARSED"],
            "job_post_id": job_post_id,
            "job_app_id": job_app_id,
        },
    )


async def get_candidate_ats_history(job_post_id: int, job_app_id: int) -> ToolResult:
    """Return ATS status/interview/feedback/offer timeline for one scoped application."""
    scope = await validate_job_application_scope(job_post_id, job_app_id)
    if not scope:
        return _result(
            ok=False,
            source={
                "tool": "get_candidate_ats_history",
                "job_post_id": job_post_id,
                "job_app_id": job_app_id,
            },
            error={
                "code": "ACCESS_DENIED",
                "message": "Ứng viên không thuộc tin tuyển dụng hiện tại hoặc không tồn tại.",
            },
        )

    async with acquire_conn() as conn:
        status_rows = await conn.fetch(
            """
            SELECT histId AS source_id, oldStat AS old_status, newStat AS new_status, changedAt AS changed_at, hrId AS hr_id
            FROM APPSTATUSHISTORY
            WHERE jobAppId = $1
            ORDER BY changedAt ASC
            """,
            job_app_id,
        )
        interview_rows = await conn.fetch(
            """
            SELECT i.intervId AS source_id, i.startAt AS start_at, i.endAt AS end_at, i."mode", i.linkMeet AS link_meet,
                   i.loc, f.feedbackId AS feedback_id, f.score, f.cmt AS comment, f.subAt AS feedback_at
            FROM INTERVIEW i
            LEFT JOIN INTERVIEWFEEDBACK f ON f.intervId = i.intervId
            WHERE i.jobAppId = $1
            ORDER BY i.startAt ASC
            """,
            job_app_id,
        )
        offer_rows = await conn.fetch(
            """
            SELECT offerId AS source_id, stat, salary, description, subAt AS submitted_at, ver, hrId AS hr_id
            FROM OFFER
            WHERE jobAppId = $1
            ORDER BY subAt ASC
            """,
            job_app_id,
        )

    timeline: list[dict[str, Any]] = []
    for row in status_rows:
        d = _row_to_dict(row)
        timeline.append({"type": "status", **d})
    for row in interview_rows:
        d = _row_to_dict(row)
        if d.get("comment"):
            d["comment"] = mask_pii_text(_truncate(d["comment"], 1000))
        timeline.append({"type": "interview", **d})
    for row in offer_rows:
        d = _row_to_dict(row)
        if d.get("description"):
            d["description"] = mask_pii_text(_truncate(d["description"], 1000))
        timeline.append({"type": "offer", **d})

    return _result(
        ok=True,
        data={
            "job_app_id": job_app_id,
            "candidate": scope,
            "timeline": sorted(
                _json_safe(timeline),
                key=lambda x: str(
                    x.get("changed_at")
                    or x.get("start_at")
                    or x.get("submitted_at")
                    or ""
                ),
            ),
        },
        source={
            "tool": "get_candidate_ats_history",
            "tables": ["APPSTATUSHISTORY", "INTERVIEW", "INTERVIEWFEEDBACK", "OFFER"],
            "job_post_id": job_post_id,
            "job_app_id": job_app_id,
        },
    )


async def count_job_applications(
    job_post_id: int, filters: dict[str, Any] | None = None
) -> ToolResult:
    """Count applications for a scoped job posting with optional normalized filters."""
    filters = filters or {}
    async with acquire_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT
                ja.jobAppId AS job_app_id,
                ja.candidateId AS candidate_id,
                ja.stat AS application_status,
                u.provId AS province_id
            FROM JOBAPPLICATION ja
            JOIN "user" u ON u.userId = ja.candidateId
            WHERE ja.jobPostId = $1
            """,
            job_post_id,
        )

    candidate_ids = [_get(_row_to_dict(r), "candidate_id", "candidateid") for r in rows]
    langs_by_candidate = await _fetch_languages_for_candidates(
        [int(cid) for cid in candidate_ids if cid is not None]
    )
    lang_filter = await _resolve_language_filter(filters.get("language"))
    warnings: list[dict[str, Any]] = []
    seen_warnings: set[str] = set()
    total = 0
    matching_ids: list[int] = []
    for row in rows:
        item = _row_to_dict(row)
        candidate_id = _get(item, "candidate_id", "candidateid")
        item = {
            "job_app_id": _get(item, "job_app_id", "jobappid"),
            "candidate_id": candidate_id,
            "application_status": _get(item, "application_status", "stat"),
            "province_id": _get(item, "province_id", "provid"),
            "languages": langs_by_candidate.get(candidate_id, []),
        }
        keep, filter_warnings = _passes_filters(item, filters, lang_filter)
        for w in filter_warnings:
            key = f"{w.get('type')}:{w.get('message')}"
            if key not in seen_warnings:
                warnings.append(w)
                seen_warnings.add(key)
        if keep:
            total += 1
            matching_ids.append(item["job_app_id"])

    return _result(
        ok=True,
        data={
            "count": total,
            "job_app_ids": matching_ids[: settings.jobposting_agent_hr_max_top_n],
            "filters_applied": filters,
        },
        source={
            "tool": "count_job_applications",
            "tables": ["JOBAPPLICATION", "CANDIDATELANGUAGE"],
            "job_post_id": job_post_id,
        },
        warnings=warnings,
    )
