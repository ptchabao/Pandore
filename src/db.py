from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = ROOT / "pandore.db"

SQL_CREATE = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'USER' CHECK(role IN ('USER', 'PREMIUM', 'ADMIN')),
        email_verified INTEGER NOT NULL DEFAULT 0,
        failed_attempts INTEGER NOT NULL DEFAULT 0,
        locked_until INTEGER,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at INTEGER NOT NULL,
        created_at INTEGER NOT NULL,
        last_seen INTEGER NOT NULL,
        ip_address TEXT,
        user_agent TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usage_limits (
        user_id TEXT PRIMARY KEY,
        storage_limit_bytes INTEGER NOT NULL DEFAULT 26843545600,
        ai_credits INTEGER NOT NULL DEFAULT 1000,
        storage_used_bytes INTEGER NOT NULL DEFAULT 0,
        ai_used INTEGER NOT NULL DEFAULT 0,
        updated_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        action TEXT NOT NULL,
        metadata TEXT NOT NULL DEFAULT '{}',
        ip_address TEXT,
        user_agent TEXT,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS accounts (
        slug TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        username TEXT,
        platform TEXT,
        status TEXT NOT NULL,
        last_seen INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recordings (
        slug TEXT PRIMARY KEY,
        account_slug TEXT,
        title TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_name TEXT NOT NULL,
        platform TEXT,
        status TEXT NOT NULL,
        metadata TEXT,
        created_at INTEGER NOT NULL,
        finished_at INTEGER,
        storage_id TEXT,
        storage_url TEXT,
        FOREIGN KEY(account_slug) REFERENCES accounts(slug)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recording_slug TEXT NOT NULL,
        job_type TEXT NOT NULL,
        status TEXT NOT NULL,
        payload TEXT,
        retries INTEGER NOT NULL,
        last_error TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        FOREIGN KEY(recording_slug) REFERENCES recordings(slug)
    )
    """
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        for sql in SQL_CREATE:
            conn.execute(sql)
        _add_column_if_missing(conn, "accounts", "user_id", "TEXT")
        _add_column_if_missing(conn, "recordings", "user_id", "TEXT")
        _add_column_if_missing(conn, "recordings", "privacy", "TEXT NOT NULL DEFAULT 'private'")
        _add_column_if_missing(conn, "recordings", "content_hash", "TEXT")
        conn.commit()


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def execute(sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()
    return cur


def query(sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows
