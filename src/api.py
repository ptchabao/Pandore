from __future__ import annotations

import json
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.db import execute, init_db, query
from src.recording_service import RecordingService
from pandore_server import slugify
from src.auth import audit, clear_session_cookie, create_session, get_current_user, hash_password, set_session_cookie, verify_password, _token_hash

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "pandore_frontend"

app = FastAPI(title="Pandore API")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
service = RecordingService()
_login_attempts: dict[str, list[float]] = {}


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/dashboard.js")
async def dashboard_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "dashboard.js", media_type="application/javascript")


@app.get("/auth.js")
async def auth_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "auth.js", media_type="application/javascript")


@app.get("/app.js")
async def app_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")


@app.get("/styles.css")
async def styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")


@app.get("/dashboard")
async def dashboard() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/login")
async def login_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "login.html")


@app.get("/register")
async def register_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "login.html")


@app.get("/api/overview")
async def overview(request: Request) -> JSONResponse:
    user = get_current_user(request)
    recordings_data = service.list_recordings(user["id"])
    accounts_data = service.list_accounts(user["id"])
    return JSONResponse({
        "hero": {"title": "Votre coffre Pandore", "subtitle": "Vos archives vidéo, privées et indexées par IA."},
        "continueWatching": recordings_data[:4],
        "recent": recordings_data,
        "creators": accounts_data,
        "accounts": accounts_data,
        "storage": {"recordingsCount": len(recordings_data), "totalBytes": 0, "archiveRoot": "private"},
        "dateGroups": [],
    })


@app.on_event("startup")
async def startup_event() -> None:
    init_db()


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"ok": True, "service": "pandore"})


@app.post("/api/auth/register")
async def register(request: Request) -> JSONResponse:
    payload = await request.json()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    if "@" not in email or len(password) < 10:
        raise HTTPException(status_code=400, detail="Email valide et mot de passe de 10 caractères minimum requis")
    if query("SELECT id FROM users WHERE email = ?", (email,)):
        raise HTTPException(status_code=409, detail="Un compte existe déjà pour cet email")

    user_id = str(uuid.uuid4())
    timestamp = int(time.time() * 1000)
    execute("INSERT INTO users (id, email, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, 'USER', ?, ?)", (user_id, email, hash_password(password), timestamp, timestamp))
    execute("INSERT INTO usage_limits (user_id, updated_at) VALUES (?, ?)", (user_id, timestamp))
    token = create_session(user_id, request)
    response = JSONResponse({"ok": True, "user": {"id": user_id, "email": email, "role": "USER"}}, status_code=201)
    set_session_cookie(response, token)
    return response


@app.post("/api/auth/login")
async def login(request: Request) -> JSONResponse:
    payload = await request.json()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    client_key = request.client.host if request.client else "unknown"
    attempts = [stamp for stamp in _login_attempts.get(client_key, []) if stamp > time.time() - 900]
    if len(attempts) >= 10:
        raise HTTPException(status_code=429, detail="Trop de tentatives. Réessayez dans quelques minutes.")
    rows = query("SELECT * FROM users WHERE email = ?", (email,))
    if not rows or not verify_password(password, rows[0]["password_hash"]):
        attempts.append(time.time())
        _login_attempts[client_key] = attempts
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    _login_attempts.pop(client_key, None)
    user = dict(rows[0])
    token = create_session(user["id"], request)
    response = JSONResponse({"ok": True, "user": {"id": user["id"], "email": user["email"], "role": user["role"]}})
    set_session_cookie(response, token)
    return response


@app.post("/api/auth/logout")
async def logout(request: Request) -> JSONResponse:
    user = get_current_user(request, required=False)
    token = request.cookies.get("pandore_session")
    if token:
        execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
    if user:
        audit(user["id"], "logout", request)
    response = JSONResponse({"ok": True})
    clear_session_cookie(response)
    return response


@app.get("/api/auth/me")
async def me(request: Request) -> JSONResponse:
    user = get_current_user(request)
    return JSONResponse({"id": user["id"], "email": user["email"], "role": user["role"], "email_verified": bool(user["email_verified"])})


@app.get("/api/security")
async def security(request: Request) -> JSONResponse:
    user = get_current_user(request)
    sessions = query("SELECT id, user_agent, ip_address, last_seen, created_at FROM sessions WHERE user_id = ? ORDER BY last_seen DESC", (user["id"],))
    audit_rows = query("SELECT action, metadata, created_at FROM audit_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 30", (user["id"],))
    return JSONResponse({"sessions": [dict(row) for row in sessions], "activity": [dict(row) for row in audit_rows], "protection_score": 60})


@app.get("/api/billing")
async def billing(request: Request) -> JSONResponse:
    user = get_current_user(request)
    rows = query("SELECT * FROM usage_limits WHERE user_id = ?", (user["id"],))
    usage = dict(rows[0]) if rows else {"storage_limit_bytes": 26843545600, "storage_used_bytes": 0, "ai_credits": 1000, "ai_used": 0}
    return JSONResponse({"plan": "FREE" if user["role"] == "USER" else user["role"], "usage": usage})


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
async def recordings(request: Request) -> JSONResponse:
    user = get_current_user(request)
    return JSONResponse({"recordings": service.list_recordings(user["id"])})


@app.get("/accounts")
async def accounts(request: Request) -> JSONResponse:
    user = get_current_user(request)
    return JSONResponse({"accounts": service.list_accounts(user["id"])})


@app.post("/api/accounts")
async def create_account(request: Request) -> JSONResponse:
    user = get_current_user(request)
    payload = await request.json()
    name = str(payload.get("name") or payload.get("creator") or "").strip()
    username = str(payload.get("username") or name).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Missing account name")

    creator_slug = slugify(payload.get("creatorSlug") or username or name)
    timestamp = int(time.time() * 1000)
    execute("INSERT INTO accounts (slug, name, username, status, last_seen, user_id) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(slug) DO UPDATE SET name = excluded.name, username = excluded.username, status = excluded.status, last_seen = excluded.last_seen, user_id = excluded.user_id", (creator_slug, name, username or creator_slug, payload.get("status", "active"), timestamp, user["id"]))
    audit(user["id"], "account_created", request)
    return JSONResponse({"accounts": service.list_accounts(user["id"]), "ok": True})


@app.delete("/api/accounts/{creator_slug}")
async def delete_account(creator_slug: str, request: Request) -> JSONResponse:
    user = get_current_user(request)
    rows = query("SELECT slug FROM accounts WHERE slug = ? AND user_id = ?", (creator_slug, user["id"]))
    if not rows:
        raise HTTPException(status_code=404, detail="Account not found")
    execute("DELETE FROM accounts WHERE slug = ? AND user_id = ?", (creator_slug, user["id"]))
    audit(user["id"], "account_deleted", request)
    return JSONResponse({"accounts": service.list_accounts(user["id"]), "ok": True})


@app.get("/recordings/{slug}")
async def get_recording(slug: str, request: Request) -> JSONResponse:
    user = get_current_user(request)
    rows = query("SELECT * FROM recordings WHERE slug = ? AND user_id = ?", (slug, user["id"]))
    recording = dict(rows[0]) if rows else None
    if recording is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    audit(user["id"], "recording_viewed", request)
    return JSONResponse(recording)
