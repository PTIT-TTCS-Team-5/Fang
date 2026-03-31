from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_ingestion import router as ingestion_router
from app.core.database import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event
    await db.connect()
    yield
    # Shutdown event
    await db.disconnect()


app = FastAPI(
    title="Fang AI Core",
    description="AI Layer API for miCareer RAG system",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(ingestion_router, prefix="/v1")


@app.get("/healthz", tags=["System"])
async def health_check():
    return {"ok": True}
