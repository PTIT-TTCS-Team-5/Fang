from pydantic import BaseModel, HttpUrl


class IngestionJobRequest(BaseModel):
    jobAppId: int
    cvSnapUrl: HttpUrl


class IngestionJobResponse(BaseModel):
    indexJobId: int
    status: str


class JobStatusResponse(BaseModel):
    status: str
    errorMsg: str | None = None
