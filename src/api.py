from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.db import init_db, query
from src.recording_service import RecordingService

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "pandore_frontend"

app = FastAPI(title="Pandore API")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
service = RecordingService()


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.on_event("startup")
async def startup_event() -> None:
    init_db()


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"ok": True, "service": "pandore"})


@app.get("/status")
async def status() -> JSONResponse:
    recordings_count = query("SELECT COUNT(*) AS count FROM recordings")
    accounts_count = query("SELECT COUNT(*) AS count FROM accounts")
    return JSONResponse(
        {
            "service": "pandore",
            "queue": {
                "name": "pandore:jobs",
                "pending_jobs": service.task_queue.queue_length("pandore:jobs"),
            },
            "recordings_count": recordings_count[0]["count"] if recordings_count else 0,
            "accounts_count": accounts_count[0]["count"] if accounts_count else 0,
        }
    )


@app.get("/recordings")
async def recordings() -> JSONResponse:
    return JSONResponse({"recordings": service.list_recordings()})


@app.get("/accounts")
async def accounts() -> JSONResponse:
    return JSONResponse({"accounts": service.list_accounts()})


@app.get("/recordings/{slug}")
async def get_recording(slug: str) -> JSONResponse:
    recording = service.record_by_slug(slug)
    if recording is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    return JSONResponse(recording)
