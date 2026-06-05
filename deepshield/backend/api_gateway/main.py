"""
DeepShield Enterprise — API Gateway
FastAPI entrypoint with JWT auth, RBAC, rate limiting, audit logging.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

from middleware.auth import JWTAuthMiddleware
from middleware.rate_limiter import RateLimiterMiddleware
from middleware.audit_log import AuditLogMiddleware
from routers import detect, upload, reports, admin, realtime, health
from core.config import settings
from core.database import init_db
from core.redis_client import init_redis

logger = logging.getLogger("deepshield")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_redis()
    logger.info("DeepShield API gateway started")
    yield
    logger.info("DeepShield API gateway shutdown")


app = FastAPI(
    title="DeepShield Enterprise API",
    version="2.0.0",
    description="Enterprise deepfake detection platform — multi-modal AI analysis",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Middleware stack (order matters: outermost → innermost) ────────────────
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(JWTAuthMiddleware)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(detect.router, prefix="/api/v1", tags=["detection"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(realtime.router, prefix="/api/v1", tags=["realtime"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "request_id": request.state.request_id},
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, workers=4)
