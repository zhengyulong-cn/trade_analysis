from contextlib import contextmanager
from threading import RLock

from tqsdk import TqApi, TqAuth

from app.core.config import settings


class TqSdkClientManager:
    def __init__(self):
        self._api: TqApi | None = None
        # TqApi 在所有请求间共享，因此对其访问需进行序列化处理。
        # 此处使用 RLock 是因为 session() 方法可能在已持有锁的情况下再次调用 start() 方法。
        self._lock = RLock()

    def start(self) -> None:
        with self._lock:
            if self._api is not None:
                return
            self._api = TqApi(
                web_gui=settings.tqsdk_web_gui,
                auth=TqAuth(settings.tqsdk_username, settings.tqsdk_password),
            )

    def close(self) -> None:
        with self._lock:
            if self._api is None:
                return
            self._api.close()
            self._api = None

    @contextmanager
    def session(self):
        # 确保在整个使用区块内保持同一把锁的持有，这样并发请求就不会同时操作共享的 TqApi 实例。
        with self._lock:
            if self._api is None:
                self.start()
            if self._api is None:
                raise RuntimeError("初始化TqApi客户端失败")
            yield self._api


tqsdk_client_manager = TqSdkClientManager()
