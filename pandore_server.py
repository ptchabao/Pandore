from __future__ import annotations

import json
import mimetypes
import os
import re
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

ROOT = Path(__file__).resolve().parent
ARCHIVE_ROOT = ROOT / "downloads" / "TikTok直播"
FRONTEND_DIR = ROOT / "pandore_frontend"
ACCOUNTS_FILE = FRONTEND_DIR / "accounts.json"
PORT = int(os.environ.get("PANDORE_PORT", "8000"))
SUPPORTED_EXTENSIONS = {".ts", ".mp4", ".flv", ".m3u8"}
MEDIA_MIME_TYPES = {
    ".ts": "video/mp2t",
    ".m3u8": "application/vnd.apple.mpegurl",
    ".mp4": "video/mp4",
    ".flv": "video/x-flv",
}
FILENAME_RE = re.compile(
    r"^(?P<prefix>.+?)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<time>\d{2}-\d{2}-\d{2})(?:\.(?P<ext>[^.]+))?$"
)


class PandoreHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        pathname = unquote(parsed.path)

        if pathname.startswith("/api/"):
            self._handle_api(pathname)
            return

        if pathname in {"/", "/index.html"}:
            self._send_file(FRONTEND_DIR / "index.html", "text/html; charset=utf-8")
            return

        if pathname in {"/dashboard", "/dashboard.html"}:
            self._send_file(FRONTEND_DIR / "dashboard.html", "text/html; charset=utf-8")
            return

        if pathname.startswith("/media/"):
            rel_path = pathname[len("/media/"):]
            self._serve_media(rel_path)
            return

        resolved = (FRONTEND_DIR / pathname.lstrip("/")).resolve()
        if resolved.is_file() and resolved.is_relative_to(FRONTEND_DIR.resolve()):
            mime = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            self._send_file(resolved, mime)
            return

        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        pathname = unquote(parsed.path)
        if pathname == "/api/accounts":
            self._handle_account_post()
            return
        self._send_json({"error": "Unknown POST route"}, status=404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        pathname = unquote(parsed.path)
        if pathname.startswith("/api/accounts/"):
            slug = pathname[len("/api/accounts/"):]
            self._handle_account_delete(slug)
            return
        self._send_json({"error": "Unknown DELETE route"}, status=404)

    def _handle_api(self, pathname: str):
        if pathname == "/api/overview":
            self._send_json(build_overview())
            return

        if pathname == "/api/health":
            self._send_json({"ok": True, "archive_root": str(ARCHIVE_ROOT)})
            return

        if pathname == "/api/accounts":
            self._send_json({"accounts": load_accounts()})
            return

        if pathname.startswith("/api/search"):
            query = urlparse(self.path).query
            params = dict(item.split("=", 1) for item in query.split("&") if "=" in item)
            q = params.get("q", "").strip().lower()
            self._send_json(search_catalog(q))
            return

        if pathname.startswith("/api/creator/"):
            slug = pathname[len("/api/creator/"):]
            self._send_json(get_creator_page(slug))
            return

        if pathname.startswith("/api/live/"):
            live_id = pathname[len("/api/live/"):]
            payload = get_live_payload(live_id)
            if payload is None:
                self._send_json({"error": "Live not found"}, status=404)
                return
            self._send_json(payload)
            return

        self._send_json({"error": "Unknown API route"}, status=404)

    def _read_body(self) -> dict[str, Any]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0

        body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            return json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            return {}

    def _handle_account_post(self):
        payload = self._read_body()
        name = str(payload.get("name") or payload.get("creator") or "").strip()
        username = str(payload.get("username") or name).strip()
        if not name:
            self._send_json({"error": "Missing account name"}, status=400)
            return

        accounts = load_accounts()
        creator_slug = slugify(payload.get("creatorSlug") or username or name)
        account = {
            "creatorSlug": creator_slug,
            "name": name,
            "username": username or creator_slug,
            "status": payload.get("status", "active"),
            "avatar": name[:2].upper(),
        }

        existing = next((item for item in accounts if item["creatorSlug"] == creator_slug), None)
        if existing:
            existing.update(account)
        else:
            accounts.append(account)

        save_accounts(accounts)
        self._send_json({"accounts": accounts, "ok": True})

    def _handle_account_delete(self, creator_slug: str):
        accounts = load_accounts()
        filtered = [item for item in accounts if item["creatorSlug"] != creator_slug]
        if len(filtered) == len(accounts):
            self._send_json({"error": "Account not found"}, status=404)
            return
        save_accounts(filtered)
        self._send_json({"accounts": filtered, "ok": True})

    def _serve_media(self, rel_path: str):
        candidate = (ARCHIVE_ROOT / unquote(rel_path)).resolve()
        if not candidate.is_relative_to(ARCHIVE_ROOT.resolve()):
            self._send_json({"error": "Invalid path"}, status=400)
            return
        if not candidate.is_file():
            self._send_json({"error": "Media not found"}, status=404)
            return
        mime = MEDIA_MIME_TYPES.get(candidate.suffix.lower())
        if mime is None:
            mime = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
        self._send_file(candidate, mime)

    def _send_file(self, file_path: Path, mime: str):
        try:
            data = file_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "File not found"}, status=404)
            return
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: Any, status: int = 200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args):
        return


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def read_video_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def estimate_duration_seconds(size_bytes: int) -> int:
    if size_bytes <= 0:
        return 60
    mb = size_bytes / (1024 * 1024)
    return max(60, int(round(mb * 8 / 1.5)))


def creator_display_name(folder: Path) -> str:
    directory_name = folder.name.replace("__", " ").replace("_", " ")
    directory_name = re.sub(r"\s+", " ", directory_name).strip()
    if "-" in directory_name:
        base = directory_name.rsplit("-", 1)[0]
        return base.strip()
    return directory_name.strip()


def infer_title(path: Path) -> str:
    match = FILENAME_RE.match(path.stem)
    if match:
        return f"Live du {match['date']} à {match['time'].replace('-', ':')}"
    return path.stem


@lru_cache(maxsize=1)
def catalog() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not ARCHIVE_ROOT.exists():
        return items

    for path in ARCHIVE_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        folder = path.parent
        creator = creator_display_name(folder)
        creator_slug = slugify(creator)
        match = FILENAME_RE.match(path.stem)
        if not match:
            continue

        date_str = match["date"]
        time_str = match["time"]
        dt = datetime.strptime(f"{date_str} {time_str.replace('-', ':')}", "%Y-%m-%d %H:%M:%S")
        size = read_video_size(path)
        duration_sec = estimate_duration_seconds(size)
        archive_relative = path.relative_to(ARCHIVE_ROOT).as_posix()
        root_relative = path.relative_to(ROOT).as_posix()
        items.append(
            {
                "id": slugify(f"{creator_slug}-{date_str}-{time_str}-{path.stem}"),
                "creator": creator,
                "creatorSlug": creator_slug,
                "title": infer_title(path),
                "date": dt.isoformat(),
                "timestamp": int(dt.timestamp()),
                "duration": duration_sec,
                "durationLabel": format_duration(duration_sec),
                "sizeBytes": size,
                "extension": path.suffix.lower(),
                "file": root_relative,
                "videoUrl": f"/media/{quote(archive_relative)}",
                "thumbnail": f"https://placehold.co/320x180/111827/ffffff?text={quote(creator)}",
                "progress": min(0.95, max(0.1, (duration_sec % 300) / max(duration_sec, 1))),
                "isNew": (datetime.now() - dt).total_seconds() < 86400,
            }
        )

    items.sort(key=lambda item: item["timestamp"], reverse=True)
    return items


def load_accounts() -> list[dict[str, Any]]:
    if ACCOUNTS_FILE.exists():
        try:
            return json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    accounts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in catalog():
        if item["creatorSlug"] in seen:
            continue
        seen.add(item["creatorSlug"])
        accounts.append(
            {
                "creatorSlug": item["creatorSlug"],
                "name": item["creator"],
                "username": item["creatorSlug"],
                "status": "active",
                "avatar": item["creator"][:2].upper(),
            }
        )
        if len(accounts) >= 8:
            break

    save_accounts(accounts)
    return accounts


def save_accounts(accounts: list[dict[str, Any]]) -> None:
    ACCOUNTS_FILE.write_text(json.dumps(accounts, ensure_ascii=False, indent=2), encoding="utf-8")


def build_overview() -> dict[str, Any]:
    items = catalog()
    recent = items[:12]
    creators = []
    creator_map: dict[str, dict[str, Any]] = {}
    dashboard_accounts = load_accounts()

    for item in items:
        creator = creator_map.setdefault(
            item["creatorSlug"],
            {
                "creator": item["creator"],
                "creatorSlug": item["creatorSlug"],
                "count": 0,
                "totalDuration": 0,
                "latest": item["timestamp"],
                "thumbnail": item["thumbnail"],
            },
        )
        creator["count"] += 1
        creator["totalDuration"] += item["duration"]
        creator["latest"] = max(creator["latest"], item["timestamp"])

    creators = sorted(creator_map.values(), key=lambda c: c["latest"], reverse=True)[:10]
    date_groups = defaultdict(list)
    for item in recent:
        month = item["date"][:7]
        date_groups[month].append(item)

    continue_list = [item for item in recent[:6]]
    for item in continue_list:
        item["progress"] = round((item["timestamp"] % 100) / 100, 2)

    return {
        "hero": {
            "title": "Pandore – Tes lives TikTok",
            "subtitle": "Tous tes lives archivés, au même endroit.",
            "searchPlaceholder": "Cherche un créateur, un titre, une date ou un mot-clé",
        },
        "continueWatching": continue_list,
        "recent": recent,
        "creators": creators,
        "accounts": dashboard_accounts,
        "dateGroups": [
            {"label": month, "items": items_for_group}
            for month, items_for_group in sorted(date_groups.items(), reverse=True)[:8]
        ],
        "myList": recent[:4],
        "history": [item for item in recent[:5]],
    }


def search_catalog(query: str) -> dict[str, Any]:
    items = catalog()
    if not query:
        return {"query": query, "count": len(items), "items": items[:20]}

    hits = []
    lowered = query.lower()
    for item in items:
        haystack = " ".join(
            [item["creator"], item["title"], item["date"], item["durationLabel"], item["creatorSlug"]]
        ).lower()
        if lowered in haystack:
            hits.append(item)

    return {"query": query, "count": len(hits), "items": hits[:20]}


def get_creator_page(slug: str) -> dict[str, Any]:
    items = [item for item in catalog() if item["creatorSlug"] == slug]
    if not items:
        return {"error": "Creator not found"}
    items.sort(key=lambda item: item["timestamp"], reverse=True)
    total_duration = sum(item["duration"] for item in items)
    return {
        "creator": items[0]["creator"],
        "creatorSlug": slug,
        "stats": {
            "count": len(items),
            "totalDuration": total_duration,
            "totalDurationLabel": format_duration(total_duration),
            "lastLive": items[0]["date"],
        },
        "items": items,
    }


def get_live_payload(live_id: str) -> dict[str, Any] | None:
    item = next((entry for entry in catalog() if entry["id"] == live_id), None)
    if item is None:
        return None
    return {
        "live": item,
        "suggestions": [entry for entry in catalog() if entry["creatorSlug"] == item["creatorSlug"] and entry["id"] != item["id"]][:6],
    }


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), PandoreHandler)
    print(f"Pandore frontend is running on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server")
        server.server_close()
