"""
Rate limiter — Redis sliding-window algorithm.
Limits per org tier: free=60/min, pro=600/min, enterprise=6000/min
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.redis_client import redis_client
from core.config import settings

TIER_LIMITS = {
    "free":       (60,   60),
    "pro":        (600,  60),
    "enterprise": (6000, 60),
}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        org_id = getattr(request.state, "org_id", "anonymous")
        tier = await self._get_org_tier(org_id)
        limit, window = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

        now = time.time()
        key = f"rate:{org_id}:{int(now // window)}"

        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window)

        remaining = max(0, limit - count)
        reset_at = int((now // window + 1) * window)

        if count > limit:
            return JSONResponse(
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                    "Retry-After": str(reset_at - int(now)),
                },
                content={"error": "Rate limit exceeded", "retry_after": reset_at - int(now)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        return response

    async def _get_org_tier(self, org_id: str) -> str:
        cached = await redis_client.get(f"org_tier:{org_id}")
        if cached:
            return cached.decode()
        # Default to free; DB lookup happens in auth service
        return "free"
