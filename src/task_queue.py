from __future__ import annotations

import json
import os
from typing import Any

import redis


class TaskQueue:
    def __init__(self, url: str | None = None):
        self.redis_url = url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.client = redis.Redis.from_url(self.redis_url)

    def push(self, queue_name: str, payload: dict[str, Any]) -> None:
        self.client.rpush(queue_name, json.dumps(payload))

    def pop(self, queue_name: str, timeout: int = 5) -> dict[str, Any] | None:
        result = self.client.blpop(queue_name, timeout=timeout)
        if result is None:
            return None
        _, value = result
        return json.loads(value)

    def queue_length(self, queue_name: str) -> int:
        return self.client.llen(queue_name)
