"""Utilities for converting parsed CV data into markdown-friendly text."""

from __future__ import annotations

import re
from datetime import date

from app.models.cv_models import CandidateInfo, Education, Experience, ParsedCV

MAX_CORE_SKILLS = 8
WHITESPACE_PATTERN = re.compile(r"\s+")
BULLET_PREFIX_PATTERN = re.compile(r"^[\-\*\u2022]+\s*")


def extract_global_metadata(parsed_cv: ParsedCV) -> str:
    """Build a deterministic section-pinning line for every chunk.

    The current `ParsedCV` schema does not expose a dedicated target-role field,
    so this function infers it from the most recent experience title first and
    then falls back to the summary's first sentence when needed.
    """

    parsed = _validate_parsed_cv(parsed_cv)
    candidate = _get_primary_candidate(parsed)

    full_name = _clean_text(candidate.fullName) or "Unknown"
    total_experience = _format_total_experience(parsed.experience)
    target_role = _extract_target_role(parsed) or "Unknown"
    core_skills = _format_core_skills(parsed.skills)

    return (
        f"[Candidate: {full_name} | Total Exp: {total_experience} | "
        f"Target Role: {target_role} | Core Skills: {core_skills}]"
    )


def convert_json_to_markdown(parsed_cv: ParsedCV) -> str:
    """Flatten a parsed CV into markdown with stable semantic headings."""

    parsed = _validate_parsed_cv(parsed_cv)
    candidate = _get_primary_candidate(parsed)
    full_name = _clean_text(candidate.fullName) or "Candidate Profile"

    sections: list[str] = [f"# {full_name}"]

    contact_lines = _build_contact_lines(candidate)
    if contact_lines:
        sections.append("## Contact")
        sections.extend(f"- {line}" for line in contact_lines)

    summary = _clean_text(parsed.summary)
    if summary:
        sections.append("## Summary")
        sections.append(summary)

    if parsed.experience:
        sections.append("## Experience")
        for experience in parsed.experience:
            sections.extend(_experience_to_markdown(experience))

    if parsed.education:
        sections.append("## Education")
        for education in parsed.education:
            sections.extend(_education_to_markdown(education))

    if parsed.skills:
        sections.append("## Skills")
        sections.extend(f"- {skill}" for skill in _clean_string_list(parsed.skills))

    if parsed.certificates:
        sections.append("## Certificates")
        sections.extend(
            f"- {certificate}"
            for certificate in _clean_string_list(parsed.certificates)
        )

    if parsed.languages:
        sections.append("## Languages")
        formatted_langs = []
        seen_langs = set()
        for lang_entry in parsed.languages:
            lang = _clean_text(lang_entry.language)
            prof = _clean_text(lang_entry.proficiency)
            if lang and lang.lower() not in seen_langs:
                seen_langs.add(lang.lower())
                if prof:
                    formatted_langs.append(f"{lang} ({prof})")
                else:
                    formatted_langs.append(lang)
        sections.extend(f"- {fl}" for fl in formatted_langs)

    return "\n".join(sections).strip()


def _validate_parsed_cv(parsed_cv: ParsedCV) -> ParsedCV:
    """Validate the input object and return a normalized ParsedCV instance."""

    if isinstance(parsed_cv, ParsedCV):
        return parsed_cv
    return ParsedCV.model_validate(parsed_cv)


def _get_primary_candidate(parsed_cv: ParsedCV) -> CandidateInfo:
    """Return the first candidate info block or an empty placeholder."""

    if parsed_cv.candidateInfo:
        return parsed_cv.candidateInfo[0]
    return CandidateInfo()


def _build_contact_lines(candidate: CandidateInfo) -> list[str]:
    """Convert candidate contact information into display-safe bullet lines."""

    contact_lines: list[str] = []

    emails = _clean_string_list(candidate.emails)
    if emails:
        contact_lines.append(f"Emails: {', '.join(emails)}")

    phones = _clean_string_list(candidate.phones)
    if phones:
        contact_lines.append(f"Phones: {', '.join(phones)}")

    location = _clean_text(candidate.location)
    if location:
        contact_lines.append(f"Location: {location}")

    return contact_lines


def _experience_to_markdown(experience: Experience) -> list[str]:
    """Serialize one experience entry into markdown lines."""

    title = _clean_text(experience.title) or "Unknown Title"
    company = _clean_text(experience.company) or "Unknown Company"
    date_range = _format_date_range(experience.startDate, experience.endDate)
    heading = f"### {title} at {company}"
    if date_range:
        heading = f"{heading} ({date_range})"

    lines = [heading]
    for description_line in _split_description_lines(experience.description):
        lines.append(f"- {description_line}")

    return lines


def _education_to_markdown(education: Education) -> list[str]:
    """Serialize one education entry into markdown lines."""

    degree = _clean_text(education.degree) or "Unknown Degree"
    school = _clean_text(education.school) or "Unknown School"
    date_range = _format_date_range(education.startDate, education.endDate)
    heading = f"### {degree} - {school}"
    if date_range:
        heading = f"{heading} ({date_range})"

    return [heading]


def _split_description_lines(description: str | None) -> list[str]:
    """Normalize description text into clean bullet items."""

    normalized = _clean_text(description, preserve_newlines=True)
    if not normalized:
        return []

    raw_lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    if len(raw_lines) > 1:
        cleaned_lines = [_strip_bullet_prefix(line) for line in raw_lines]
        return [line for line in cleaned_lines if line]

    single_line = _strip_bullet_prefix(raw_lines[0])
    if not single_line:
        return []

    segments = [
        segment.strip(" ;")
        for segment in re.split(r"(?:\s*[\u2022\-\*]\s+|;\s+)", single_line)
        if segment.strip(" ;")
    ]
    return segments or [single_line]


def _strip_bullet_prefix(value: str) -> str:
    """Remove common bullet markers from the beginning of a line."""

    return BULLET_PREFIX_PATTERN.sub("", value).strip()


def _clean_string_list(values: list[str]) -> list[str]:
    """Clean, deduplicate, and preserve order for simple string lists."""

    cleaned_values: list[str] = []
    seen: set[str] = set()

    for value in values:
        cleaned = _clean_text(value)
        if cleaned and cleaned.lower() not in seen:
            cleaned_values.append(cleaned)
            seen.add(cleaned.lower())

    return cleaned_values


def _clean_text(value: str | None, preserve_newlines: bool = False) -> str:
    """Normalize whitespace while optionally preserving line breaks."""

    if value is None:
        return ""

    text = value.strip()
    if not text:
        return ""

    if preserve_newlines:
        lines = [
            WHITESPACE_PATTERN.sub(" ", line).strip() for line in text.splitlines()
        ]
        return "\n".join(line for line in lines if line)

    return WHITESPACE_PATTERN.sub(" ", text)


def _format_total_experience(experiences: list[Experience]) -> str:
    """Estimate total experience from the overall experience timeline."""

    ranges: list[tuple[date, date]] = []
    for experience in experiences:
        start_date = _parse_cv_date(experience.startDate)
        end_date = _parse_cv_date(experience.endDate)
        if start_date is None:
            continue
        ranges.append((start_date, end_date or date.today()))

    if not ranges:
        return "Unknown"

    earliest_start = min(start for start, _ in ranges)
    latest_end = max(end for _, end in ranges)
    months = max(1, _month_delta(earliest_start, latest_end))
    years = round(months / 12, 1)
    years_display = int(years) if years.is_integer() else years

    return f"{years_display} Years"


def _extract_target_role(parsed_cv: ParsedCV) -> str:
    """Infer the target role using the latest experience title when possible."""

    latest_experience = _get_latest_experience(parsed_cv.experience)
    if latest_experience is not None:
        latest_title = _clean_text(latest_experience.title)
        if latest_title:
            return latest_title

    summary = _clean_text(parsed_cv.summary)
    if not summary:
        return ""

    first_sentence = re.split(r"(?<=[.!?])\s+", summary, maxsplit=1)[0].strip()
    return first_sentence[:120].rstrip(" ,;")


def _get_latest_experience(experiences: list[Experience]) -> Experience | None:
    """Return the latest experience block based on end date and start date."""

    if not experiences:
        return None

    def _sort_key(experience: Experience) -> tuple[date, date]:
        end_date = _parse_cv_date(experience.endDate) or date.today()
        start_date = _parse_cv_date(experience.startDate) or date.min
        return end_date, start_date

    return max(experiences, key=_sort_key)


def _format_core_skills(skills: list[str]) -> str:
    """Serialize the most relevant skills into a compact comma-separated list."""

    cleaned_skills = _clean_string_list(skills)[:MAX_CORE_SKILLS]
    if not cleaned_skills:
        return "Unknown"
    return ", ".join(cleaned_skills)


def _format_date_range(start_date: str | None, end_date: str | None) -> str:
    """Format a start/end date range for markdown headings."""

    start = _clean_text(start_date)
    end = _clean_text(end_date)

    if start and end:
        return f"{start} - {end}"
    if start:
        return start
    if end:
        return end
    return ""


def _parse_cv_date(value: str | None) -> date | None:
    """Parse CV date strings in YYYY-MM format or the special value 'present'."""

    if value is None:
        return None

    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized == "present":
        return date.today()

    try:
        year_str, month_str = normalized.split("-", maxsplit=1)
        return date(int(year_str), int(month_str), 1)
    except (TypeError, ValueError):
        return None


def _month_delta(start_date: date, end_date: date) -> int:
    """Return the inclusive month span between two dates."""

    if end_date < start_date:
        start_date, end_date = end_date, start_date

    return (
        (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
    )
