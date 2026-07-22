from __future__ import annotations

import dataclasses
import datetime
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Account:
    slug: str
    name: str
    username: str | None = None
    platform: str | None = None
    status: str = "active"
    last_seen: int = field(default_factory=lambda: int(datetime.datetime.utcnow().timestamp() * 1000))


@dataclass
class Recording:
    slug: str
    account_slug: str | None
    title: str
    file_path: str
    file_name: str
    platform: str | None = None
    status: str = "recorded"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: int = field(default_factory=lambda: int(datetime.datetime.utcnow().timestamp() * 1000))
    finished_at: int | None = None
    storage_id: str | None = None
    storage_url: str | None = None


@dataclass
class Job:
    id: int | None
    recording_slug: str
    job_type: str
    status: str = "pending"
    payload: dict[str, Any] = field(default_factory=dict)
    retries: int = 0
    last_error: str | None = None
    created_at: int = field(default_factory=lambda: int(datetime.datetime.utcnow().timestamp() * 1000))
    updated_at: int = field(default_factory=lambda: int(datetime.datetime.utcnow().timestamp() * 1000))
