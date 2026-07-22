from __future__ import annotations

import threading
import os
import uvicorn

from src.db import init_db
from src.workers import JobWorker
from src.api import app as api_app


def start_workers() -> None:
    upload_worker = JobWorker("pandore:jobs")
    thread = threading.Thread(target=upload_worker.run, daemon=True)
    thread.start()


if __name__ == "__main__":
    init_db()
    start_workers()
    uvicorn.run(
        api_app,
        host="0.0.0.0",
        port=int(os.environ.get("PANDORE_PORT", "8000")),
        log_level="info",
    )
