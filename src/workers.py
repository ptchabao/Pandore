from __future__ import annotations

import json
import logging
import time
from typing import Any

from src.convex_sync import ConvexSync
from src.db import execute, query
from src.task_queue import TaskQueue

LOGGER = logging.getLogger("pandore.workers")


class JobWorker:
    def __init__(self, queue_name: str) -> None:
        self.queue_name = queue_name
        self.queue = TaskQueue()
        self.convex = ConvexSync()

    def run(self) -> None:
        LOGGER.info("Starting worker for %s", self.queue_name)
        while True:
            try:
                job = self.queue.pop(self.queue_name, timeout=5)
            except Exception as exc:
                LOGGER.exception("Queue pop failed: %s", exc)
                time.sleep(2)
                continue

            if job is None:
                time.sleep(1)
                continue

            try:
                self.handle(job)
            except Exception as exc:
                LOGGER.exception("Worker failed to process job: %s", exc)
                self.mark_job_failed(job, str(exc))

    def handle(self, job: dict[str, Any]) -> None:
        job_type = job.get("job_type")
        recording_slug = job.get("recording_slug")
        if job_type == "upload":
            self.handle_upload(recording_slug, job)
        elif job_type == "metadata":
            self.handle_metadata(recording_slug, job)
        else:
            LOGGER.warning("Unknown job type: %s", job_type)

    def mark_job_failed(self, job: dict[str, Any], error_message: str) -> None:
        job["retries"] = job.get("retries", 0) + 1
        job["last_error"] = error_message
        job["updated_at"] = int(time.time() * 1000)
        if job["retries"] < 5:
            self.queue.push(self.queue_name, job)
        else:
            LOGGER.error("Job permanently failed: %s", job)

    def handle_upload(self, recording_slug: str, job: dict[str, Any]) -> None:
        row = self.get_recording(recording_slug)
        if not row:
            raise RuntimeError(f"Recording not found: {recording_slug}")

        file_path = row["file_path"]
        if not file_path:
            raise RuntimeError("Upload job missing file path")

        LOGGER.info("Uploading recording %s", recording_slug)
        upload_result = self.convex.finalize_recording_safe(
            slug=recording_slug,
            file_path=file_path,
            account_slug=row.get("account_slug"),
            title=row.get("title"),
            delete_local=False,
        )
        if not upload_result:
            raise RuntimeError("Convex upload failed")

        execute(
            "UPDATE recordings SET status = ?, storage_id = ?, storage_url = ?, finished_at = ? WHERE slug = ?",
            (
                "uploaded",
                upload_result.get("storageId"),
                upload_result.get("storageUrl"),
                int(time.time() * 1000),
                recording_slug,
            ),
        )
        LOGGER.info("Upload completed for %s", recording_slug)

    def handle_metadata(self, recording_slug: str, job: dict[str, Any]) -> None:
        row = self.get_recording(recording_slug)
        if not row:
            raise RuntimeError(f"Recording not found: {recording_slug}")

        account_slug = row.get("account_slug")
        if not account_slug:
            account_slug = recording_slug

        self.convex.upsert_account(
            slug=account_slug,
            name=row.get("title") or recording_slug,
            username=row.get("account_slug"),
            platform=row.get("platform"),
            status="active",
        )
        self.convex.upsert_recording(
            slug=recording_slug,
            account_slug=account_slug,
            title=row.get("title") or recording_slug,
            file_path=row.get("file_path") or "",
            file_name=row.get("file_name") or "",
            status=row.get("status") or "recorded",
            metadata=json.loads(row.get("metadata") or "{}"),
        )

    def get_recording(self, slug: str) -> dict[str, Any] | None:
        rows = query("SELECT * FROM recordings WHERE slug = ?", (slug,))
        return dict(rows[0]) if rows else None
