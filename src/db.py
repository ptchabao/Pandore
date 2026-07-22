from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = ROOT / "pandore.db"

SQL_CREATE = [
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
        conn.commit()


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
