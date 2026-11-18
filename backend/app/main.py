from contextlib import asynccontextmanager
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, get_engine
from app.core.logging import configure_logging, correlation_id_ctx, get_logger
from app.models.entities import Base
from app.services.scheduler_jobs import seed_default_rules_and_policies

configure_logging()
logger = get_logger("main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        await seed_default_rules_and_policies(db)
    logger.info("personal_intelligent_email_os_started", env=settings.APP_ENV)
    yield
    await eng.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Production-grade Self-Hosted Personal Intelligent Email OS for Gmail "
        "with 3D Classification, Safe Bulk Cleanup, pgvector RAG, and Telegram Command Center."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    correlation_id_ctx.set(cid)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
    }


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
