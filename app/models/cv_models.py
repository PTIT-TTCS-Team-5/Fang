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
    languages: list[str] = Field(
        default_factory=list, description="List of languages the candidate speaks."
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
