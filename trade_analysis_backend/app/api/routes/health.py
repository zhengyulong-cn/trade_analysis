from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import RedisClientDep
from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/redis")
def redis_health_check(redis_client: RedisClientDep) -> dict[str, object]:
    try:
        redis_client.ping()
        client_info = redis_client.client_info()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis health check failed: {exc}",
        ) from exc

    return {
        "status": "ok",
        "redis": {
            "url": settings.redis_url,
            "ping": True,
            "db": settings.redis_db,
            "addr": client_info.get("addr"),
            "name": client_info.get("name"),
        },
    }
