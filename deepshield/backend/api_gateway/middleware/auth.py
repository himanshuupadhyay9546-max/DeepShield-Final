"""
JWT authentication middleware with RBAC.
Roles: super_admin | org_admin | analyst | viewer | api_client
"""
import uuid
import time
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import jwt

from core.config import settings
from core.redis_client import redis_client

BEARER = HTTPBearer(auto_error=False)

PUBLIC_PATHS = {
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "super_admin": {"*"},
    "org_admin":   {"detect", "upload", "reports", "admin:org", "users:manage"},
    "analyst":     {"detect", "upload", "reports"},
    "viewer":      {"reports:read"},
    "api_client":  {"detect", "upload"},
}


def create_access_token(user_id: str, role: str, org_id: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "org": org_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + settings.JWT_EXPIRE_SECONDS,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def is_token_revoked(jti: str) -> bool:
    return await redis_client.exists(f"revoked_token:{jti}")


def has_permission(role: str, required: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or required in perms


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())

        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Missing authorization header"},
            )

        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"error": e.detail})

        if await is_token_revoked(payload.get("jti", "")):
            return JSONResponse(status_code=401, content={"error": "Token revoked"})

        request.state.user_id = payload["sub"]
        request.state.user_role = payload["role"]
        request.state.org_id = payload["org"]
        request.state.token_jti = payload["jti"]

        return await call_next(request)


def require_permission(permission: str):
    """Dependency: raise 403 if caller lacks permission."""
    from fastapi import Depends
    async def checker(request: Request):
        role = getattr(request.state, "user_role", None)
        if not role or not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
    return Depends(checker)
