from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.db import init_db, query
from src.recording_service import RecordingService
from pandore_server import build_overview, load_accounts, save_accounts, slugify

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "pandore_frontend"

app = FastAPI(title="Pandore API")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
service = RecordingService()


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/dashboard.js")
async def dashboard_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "dashboard.js", media_type="application/javascript")


@app.get("/app.js")
async def app_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")


@app.get("/styles.css")
async def styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")


@app.get("/dashboard")
async def dashboard() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/api/overview")
async def overview() -> JSONResponse:
    return JSONResponse(build_overview())


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


@app.post("/api/accounts")
async def create_account(request: Request) -> JSONResponse:
    payload = await request.json()
    name = str(payload.get("name") or payload.get("creator") or "").strip()
    username = str(payload.get("username") or name).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Missing account name")

    accounts_data = load_accounts()
    creator_slug = slugify(payload.get("creatorSlug") or username or name)
    account = {
        "creatorSlug": creator_slug,
        "name": name,
        "username": username or creator_slug,
        "status": payload.get("status", "active"),
        "avatar": name[:2].upper(),
    }
    existing = next((item for item in accounts_data if item["creatorSlug"] == creator_slug), None)
    if existing:
        existing.update(account)
    else:
        accounts_data.append(account)
    save_accounts(accounts_data)
    return JSONResponse({"accounts": accounts_data, "ok": True})


@app.delete("/api/accounts/{creator_slug}")
async def delete_account(creator_slug: str) -> JSONResponse:
    accounts_data = load_accounts()
    filtered = [item for item in accounts_data if item["creatorSlug"] != creator_slug]
    if len(filtered) == len(accounts_data):
        raise HTTPException(status_code=404, detail="Account not found")
    save_accounts(filtered)
    return JSONResponse({"accounts": filtered, "ok": True})


@app.get("/recordings/{slug}")
async def get_recording(slug: str) -> JSONResponse:
    recording = service.record_by_slug(slug)
    if recording is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    return JSONResponse(recording)
