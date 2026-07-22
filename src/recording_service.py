from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from src.db import execute, query
from src.models import Account, Recording
from src.task_queue import TaskQueue


class RecordingService:
    def __init__(self) -> None:
        self.task_queue = TaskQueue()

    def upsert_account(self, account: Account) -> None:
        existing = query("SELECT slug FROM accounts WHERE slug = ?", (account.slug,))
        if existing:
            execute(
                "UPDATE accounts SET name = ?, username = ?, platform = ?, status = ?, last_seen = ? WHERE slug = ?",
                (account.name, account.username, account.platform, account.status, account.last_seen, account.slug),
            )
        else:
            execute(
                "INSERT INTO accounts (slug, name, username, platform, status, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
                (account.slug, account.name, account.username, account.platform, account.status, account.last_seen),
            )

    def create_recording(self, recording: Recording) -> None:
        execute(
            "INSERT OR REPLACE INTO recordings (slug, account_slug, title, file_path, file_name, platform, status, metadata, created_at, finished_at, storage_id, storage_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                recording.slug,
                recording.account_slug,
                recording.title,
                recording.file_path,
                recording.file_name,
                recording.platform,
                recording.status,
                json.dumps(recording.metadata, ensure_ascii=False),
                recording.created_at,
                recording.finished_at,
                recording.storage_id,
                recording.storage_url,
            ),
        )

    def update_recording_status(self, slug: str, status: str, finished_at: int | None = None, storage_id: str | None = None, storage_url: str | None = None) -> None:
        fields: list[str] = ["status = ?"]
        values: list[Any] = [status]
        if finished_at is not None:
            fields.append("finished_at = ?")
            values.append(finished_at)
        if storage_id is not None:
            fields.append("storage_id = ?")
            values.append(storage_id)
        if storage_url is not None:
            fields.append("storage_url = ?")
            values.append(storage_url)
        values.append(slug)
        execute(f"UPDATE recordings SET {', '.join(fields)} WHERE slug = ?", tuple(values))

    def record_by_slug(self, slug: str) -> dict[str, Any] | None:
        rows = query("SELECT * FROM recordings WHERE slug = ?", (slug,))
        if not rows:
            return None
        row = rows[0]
        return dict(row)

    def list_recordings(self, user_id: str | None = None) -> list[dict[str, Any]]:
        if user_id:
            rows = query("SELECT * FROM recordings WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        else:
            rows = query("SELECT * FROM recordings ORDER BY created_at DESC")
        return [dict(row) for row in rows]

    def list_accounts(self, user_id: str | None = None) -> list[dict[str, Any]]:
        if user_id:
            rows = query("SELECT * FROM accounts WHERE user_id = ? ORDER BY last_seen DESC", (user_id,))
        else:
            rows = query("SELECT * FROM accounts ORDER BY last_seen DESC")
        accounts = []
        for row in rows:
            account = dict(row)
            account["creatorSlug"] = account.get("slug")
            account["avatar"] = (account.get("name") or "PA")[:2].upper()
            accounts.append(account)
        return accounts

    def enqueue_job(self, recording_slug: str, job_type: str, payload: dict[str, Any]) -> None:
        job = {
            "recording_slug": recording_slug,
            "job_type": job_type,
            "payload": payload,
            "retries": 0,
            "created_at": int(time.time() * 1000),
        }
        self.task_queue.push("pandore:jobs", job)

    def enqueue_upload(self, recording_slug: str) -> None:
        self.enqueue_job(recording_slug, "upload", {})

    def enqueue_metadata(self, recording_slug: str) -> None:
        self.enqueue_job(recording_slug, "metadata", {})
