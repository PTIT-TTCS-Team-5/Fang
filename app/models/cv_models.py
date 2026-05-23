from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Regex to validate date format "YYYY-MM" or the special value "present"
DATE_PATTERN = r"^(?:\d{4}-(0[1-9]|1[0-2])|present)$"
# Custom type hint for validated date strings
CVDate = Annotated[str, Field(pattern=DATE_PATTERN)]


class CVBaseModel(BaseModel):
    """Base model configuration that all other CV models inherit from."""

    # Ignore any extra fields from the input that are not defined in the model
    model_config = ConfigDict(extra="ignore")


class CandidateInfo(CVBaseModel):
    """Represents the basic personal information of a candidate."""

    fullName: str | None = Field(None, description="Candidate's full name.")
    emails: list[str] = Field(
        default_factory=list, description="List of candidate's email addresses."
    )
    phones: list[str] = Field(
        default_factory=list, description="List of candidate's phone numbers."
    )
    location: str | None = Field(None, description="Candidate's location or address.")


class Education(CVBaseModel):
    """Represents a single educational entry from a CV."""

    school: str | None = Field(None, description="Name of the school or university.")
    degree: str | None = Field(None, description="Degree or qualification obtained.")
    startDate: CVDate | None = Field(
        None, description="Start date of education (YYYY-MM)."
    )
    endDate: CVDate | None = Field(
        None, description='End date of education (YYYY-MM or "present").'
    )


class Experience(CVBaseModel):
    """Represents a single work experience entry from a CV."""

    company: str | None = Field(None, description="Name of the company.")
    title: str | None = Field(None, description="Job title or position.")
    startDate: CVDate | None = Field(
        None, description="Start date of employment (YYYY-MM)."
    )
    endDate: CVDate | None = Field(
        None, description='End date of employment (YYYY-MM or "present").'
    )
    description: str | None = Field(
        None, description="Description of responsibilities and achievements."
    )


class LanguageEntry(CVBaseModel):
    """Represents a language skill from a CV.

    [NMAIex Phase 2.5f] Breaking change: replaces list[str] in ParsedCV.languages.
    Proficiency is stored as raw string from CV (e.g. 'N3', 'Fluent', 'B2') —
    normalization to BASIC|INTERMEDIATE|ADVANCED|FLUENT|NATIVE happens in
    nmaiex_mapper_service.normalize_proficiency() at scoring time.
    """

    language: str = Field(
        ..., description="Language name (e.g. 'English', 'Japanese')."
    )
    proficiency: str | None = Field(
        None,
        description="Proficiency as stated in CV (e.g. 'N3', 'Fluent', 'B2'). Raw string.",
    )


class ParserSelfReport(CVBaseModel):
    """Optional model-reported confidence metadata for parser quality review."""

    confidence: float | None = Field(
        None,
        ge=0,
        le=1,
        description="Model self-reported confidence in [0, 1].",
    )
    issues: list[str] = Field(
        default_factory=list,
        description="Short quality or uncertainty issues reported by the parser model.",
    )
    uncertainFields: list[str] = Field(
        default_factory=list,
        description="Field names the parser model considers uncertain.",
    )


class ParsedCV(CVBaseModel):
    """The root model representing the entire parsed content of a CV."""

    candidateInfo: list[CandidateInfo] = Field(
        default_factory=list, description="List of candidate's personal information."
    )
    education: list[Education] = Field(
        default_factory=list, description="List of candidate's educational background."
    )
    experience: list[Experience] = Field(
        default_factory=list, description="List of candidate's work experience."
    )
    skills: list[str] = Field(
        default_factory=list, description="List of skills extracted from the CV."
    )
    certificates: list[str] = Field(
        default_factory=list, description="List of certificates obtained."
    )
    languages: list[LanguageEntry] = Field(
        default_factory=list,
        description="[NMAIex Phase 2.5f] List of languages with proficiency levels.",
    )
    summary: str = Field("", description="A brief summary or objective from the CV.")
    rawText: str = Field(
        ...,
        min_length=1,
        description="The full raw text extracted from the CV file.",
    )
    parserVer: str | None = Field(
        None, description="Version of the CV parser used to process the file."
    )
    # [NMAIex Phase 2.5d] Expected salary — dùng cho Salary Adjustment trong C→J
    # LLM trả null nếu CV không đề cập. None = không có thông tin.
    expectedSalaryMin: int | None = Field(
        None,
        description="Expected minimum salary (VND). None if not stated in CV.",
    )
    expectedSalaryMax: int | None = Field(
        None,
        description="Expected maximum salary (VND). None if not stated in CV.",
    )
    parserSelfReport: ParserSelfReport | None = Field(
        None,
        description="Optional parser self-report used as an extra quality signal.",
    )
