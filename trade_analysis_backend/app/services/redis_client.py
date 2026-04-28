from threading import RLock

from redis import Redis

from app.core.config import settings


class RedisClientManager:
    def __init__(self):
        self._client: Redis | None = None
        self._lock = RLock()

    def start(self) -> None:
        with self._lock:
            if self._client is not None:
                return
            client = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
            )
            client.ping()
            self._client = client

    def close(self) -> None:
        with self._lock:
            if self._client is None:
                return
            self._client.close()
            self._client = None

    def get_client(self) -> Redis:
        with self._lock:
            if self._client is None:
                self.start()
            if self._client is None:
                raise RuntimeError("Failed to initialize Redis client")
            return self._client


redis_client_manager = RedisClientManager()
