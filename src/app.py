from __future__ import annotations

import threading
import os
import sys
from pathlib import Path
import uvicorn

# Ensure the repository root is on sys.path when the script is launched directly.
root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

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
