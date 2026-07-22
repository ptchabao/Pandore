from __future__ import annotations

import json
import os
from typing import Any

import redis


class EventBus:
    def __init__(self, url: str | None = None):
        self.redis_url = url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.client = redis.Redis.from_url(self.redis_url)

    def publish(self, channel: str, event: dict[str, Any]) -> None:
        self.client.publish(channel, json.dumps(event))

    def subscribe(self, channel: str):
        pubsub = self.client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(channel)
        return pubsub

    def enqueue_job(self, queue_name: str, job: dict[str, Any]) -> None:
        self.client.rpush(queue_name, json.dumps(job))

    def dequeue_job(self, queue_name: str, timeout: int = 5) -> dict[str, Any] | None:
        result = self.client.blpop(queue_name, timeout=timeout)
        if result is None:
            return None
        _, payload = result
        return json.loads(payload)
