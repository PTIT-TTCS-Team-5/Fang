from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

DATE_PATTERN = r"^(?:\d{4}-(0[1-9]|1[0-2])|present)$"
CVDate = Annotated[str, Field(pattern=DATE_PATTERN)]


class CVBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class CandidateInfo(CVBaseModel):
    fullName: str | None = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    location: str | None = None


class Education(CVBaseModel):
    school: str | None = None
    degree: str | None = None
    startDate: CVDate | None = None
    endDate: CVDate | None = None


class Experience(CVBaseModel):
    company: str | None = None
    title: str | None = None
    startDate: CVDate | None = None
    endDate: CVDate | None = None
    description: str | None = None


class ParsedCV(CVBaseModel):
    candidateInfo: list[CandidateInfo] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    summary: str = ""
    rawText: str = Field(..., min_length=1)
    parserVer: str | None = None
