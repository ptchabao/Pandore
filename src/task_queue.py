from __future__ import annotations

import json
import os
from typing import Any

import redis
from redis.exceptions import ConnectionError, TimeoutError


class TaskQueue:
    def __init__(self, url: str | None = None):
        self.redis_url = url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.client = self._create_client()

    def _create_client(self) -> redis.Redis:
        return redis.Redis.from_url(
            self.redis_url,
            socket_connect_timeout=5,
            socket_timeout=10,
            retry_on_timeout=True,
        )

    def _reconnect(self) -> None:
        self.client = self._create_client()

    def push(self, queue_name: str, payload: dict[str, Any]) -> None:
        try:
            self.client.rpush(queue_name, json.dumps(payload))
        except (ConnectionError, TimeoutError):
            self._reconnect()
            self.client.rpush(queue_name, json.dumps(payload))

    def pop(self, queue_name: str, timeout: int = 5) -> dict[str, Any] | None:
        try:
            result = self.client.blpop(queue_name, timeout=timeout)
        except TimeoutError:
            return None
        except ConnectionError:
            self._reconnect()
            return None

        if result is None:
            return None
        _, value = result
        return json.loads(value)

    def queue_length(self, queue_name: str) -> int:
        try:
            return self.client.llen(queue_name)
        except (ConnectionError, TimeoutError):
            self._reconnect()
            return self.client.llen(queue_name)
