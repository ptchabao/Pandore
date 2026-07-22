from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
import uuid
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from fastapi import HTTPException, Request

from src.db import execute, query

PASSWORD_HASHER = PasswordHasher()
JWT_SECRET = os.environ.get("PANDORE_JWT_SECRET", "change-this-secret-in-production")
JWT_ALGORITHM = "HS256"
SESSION_DAYS = int(os.environ.get("PANDORE_SESSION_DAYS", "30"))


def now_ms() -> int:
    return int(time.time() * 1000)


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHash):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: str, request: Request) -> str:
    raw_token = secrets.token_urlsafe(48)
    issued = now_ms()
    expires = issued + SESSION_DAYS * 24 * 60 * 60 * 1000
    execute(
        "INSERT INTO sessions (id, user_id, token_hash, expires_at, created_at, last_seen, ip_address, user_agent) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, _token_hash(raw_token), expires, issued, issued, request.client.host if request.client else None, request.headers.get("user-agent")),
    )
    audit(user_id, "login_success", request)
    return raw_token


def get_current_user(request: Request, required: bool = True) -> dict[str, Any] | None:
    token = request.cookies.get("pandore_session")
    if not token:
        if required:
            raise HTTPException(status_code=401, detail="Authentication required")
        return None

    rows = query(
        "SELECT u.id, u.email, u.role, u.email_verified, u.created_at, s.id AS session_id FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ?",
        (_token_hash(token), now_ms()),
    )
    if not rows:
        if required:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        return None
    user = dict(rows[0])
    execute("UPDATE sessions SET last_seen = ? WHERE id = ?", (now_ms(), user["session_id"]))
    return user


def require_role(user: dict[str, Any], *roles: str) -> None:
    if user["role"] not in roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def audit(user_id: str | None, action: str, request: Request | None = None, metadata: str = "{}") -> None:
    execute(
        "INSERT INTO audit_logs (user_id, action, metadata, ip_address, user_agent, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, action, metadata, request.client.host if request and request.client else None, request.headers.get("user-agent") if request else None, now_ms()),
    )


def set_session_cookie(response: Any, token: str) -> None:
    response.set_cookie(
        "pandore_session",
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=os.environ.get("PANDORE_COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
    )


def clear_session_cookie(response: Any) -> None:
    response.delete_cookie("pandore_session")
