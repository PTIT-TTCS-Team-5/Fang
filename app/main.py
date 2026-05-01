from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.nmaiex_routes_ranking import router as nmaiex_router
from app.api.routes_chat import router as chat_router
from app.api.routes_ingestion import router as ingestion_router
from app.core.config import settings
from app.core.database import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event
    await db.connect()
    yield
    # Shutdown event
    await db.disconnect()


app = FastAPI(
    title="FANG AI Core",
    description="AI Layer API for miCareer — Ingestion + RAG Query (v2)",
    version="2.0.0",
    lifespan=lifespan,
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- v2 routes ---
app.include_router(ingestion_router, prefix="/v2")
app.include_router(chat_router, prefix="/v2")
app.include_router(nmaiex_router, prefix="/v2/nmaiex")

# --- v1 routes (backward-compatible, deprecated) ---
app.include_router(ingestion_router, prefix="/v1")


@app.get("/v2/healthz", tags=["System"])
async def health_check_v2():
    return {"ok": True, "version": "2.0"}


# Backward-compatible v1 health check
@app.get("/healthz", tags=["System"])
async def health_check():
    return {"ok": True}
