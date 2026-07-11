"""Enterprise Meet — FastAPI application entry point."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.database import check_db_connection, engine
import app.models  # noqa: F401 — registers all ORM models in SQLAlchemy mapper registry
from app.core.logging import configure_logging, get_logger
from app.core.redis import check_redis_connection, close_redis, get_redis_client
from app.middleware import register_middleware
from app.utils.storage import ensure_bucket_exists
from app.websocket.manager import manager

logger = get_logger(__name__)

_start_time = time.time()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application startup and shutdown events."""
    # ── Startup ───────────────────────────────────────────────────────────────
    configure_logging()
    logger.info("starting_up", env=settings.APP_ENV, version=settings.APP_VERSION)

    # Verify DB connectivity
    db_ok = await check_db_connection()
    if not db_ok:
        logger.error("database_connection_failed")
    else:
        logger.info("database_connected")

    # Verify Redis connectivity
    redis_ok = await check_redis_connection()
    if not redis_ok:
        logger.error("redis_connection_failed")
    else:
        logger.info("redis_connected")

    # Ensure MinIO buckets exist
    try:
        for bucket in [
            settings.MINIO_BUCKET_FILES,
            settings.MINIO_BUCKET_RECORDINGS,
            settings.MINIO_BUCKET_AVATARS,
        ]:
            ensure_bucket_exists(bucket)
        logger.info("minio_buckets_ready")
    except Exception as e:
        logger.warning("minio_init_failed", error=str(e))

    # Start WebSocket manager (Redis pub/sub)
    await manager.start()

    logger.info("startup_complete")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("shutting_down")
    await manager.stop()
    await close_redis()
    await engine.dispose()
    logger.info("shutdown_complete")


# ── Application Factory ───────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Enterprise-grade video conferencing platform API",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Middleware (order matters — outermost first)
    register_middleware(app)

    # API routes
    from app.api.v1.router import api_router
    app.include_router(api_router)

    # Prometheus metrics
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    # Health endpoints
    @app.get("/health", tags=["Health"], include_in_schema=True)
    async def health():
        db_ok = await check_db_connection()
        redis_ok = await check_redis_connection()
        status = "ok" if db_ok and redis_ok else "degraded"
        return {
            "status": status,
            "version": settings.APP_VERSION,
            "uptime_seconds": round(time.time() - _start_time, 2),
            "services": {
                "database": "ok" if db_ok else "error",
                "redis": "ok" if redis_ok else "error",
            },
        }

    @app.get("/ready", tags=["Health"], include_in_schema=False)
    async def readiness():
        db_ok = await check_db_connection()
        redis_ok = await check_redis_connection()
        if not db_ok or not redis_ok:
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail="Service not ready")
        return {"ready": True}

    @app.get("/live", tags=["Health"], include_in_schema=False)
    async def liveness():
        return {"alive": True}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 4,
        loop="uvloop",
        http="httptools",
        log_level=settings.LOG_LEVEL.lower(),
    )
