from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.logging import get_logger
from app.core.rate_limit import limiter

logger = get_logger(__name__)


class CORSErrorMiddleware(BaseHTTPMiddleware):
    """Ensure CORS headers are present on ALL responses, including error responses
    from route dependencies that bypass the standard CORSMiddleware pipeline."""

    def __init__(self, app, allowed_origins: list[str]):
        super().__init__(app)
        self.allowed_origins = set(allowed_origins)

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "")
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                "unhandled_middleware_exception",
                error=str(exc),
                path=str(request.url),
            )
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"},
            )

        if origin in self.allowed_origins or "*" in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Vary"] = "Origin"

        return response


def register_middleware(app: FastAPI) -> None:
    # Rate Limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Standard CORS middleware (handles preflight OPTIONS correctly)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Fallback: inject CORS headers on responses that bypassed CORSMiddleware
    # (e.g. 401/403 from auth dependencies, unhandled exceptions)
    app.add_middleware(CORSErrorMiddleware, allowed_origins=settings.CORS_ORIGINS)
