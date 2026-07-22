import os
import sys
from pathlib import Path
from typing import Any, Optional

import httpx


class ConvexSync:
    def __init__(self, deployment: Optional[str] = None, admin_key: Optional[str] = None):
        self._load_env_file()
        self.deployment = deployment or os.environ.get("CONVEX_DEPLOYMENT") or os.environ.get("CONVEX_URL")
        self.admin_key = admin_key or os.environ.get("CONVEX_ADMIN_KEY") or os.environ.get("CONVEX_DEPLOY_KEY")
        self.base_url = self.deployment.rstrip("/") if self.deployment else None
        self.client = httpx.Client(timeout=60.0)

    def _load_env_file(self) -> None:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.admin_key:
            headers["Authorization"] = f"Convex {self.admin_key}"
            headers["X-Convex-Admin-Key"] = self.admin_key
        return headers

    def _is_mutation(self, function_name: str) -> bool:
        return any(function_name.endswith(suffix) for suffix in ("upsert", "markUploaded", "delete", "create", "patch"))

    def _call(self, function_name: str, args: Any) -> Any:
        if not self.base_url:
            raise RuntimeError("CONVEX_DEPLOYMENT is not configured")

        endpoint = "/api/mutation" if self._is_mutation(function_name) else "/api/query"
        payload = {
            "path": function_name,
            "args": args if isinstance(args, list) else [args],
        }

        urls = [self.base_url, self.base_url.replace(".convex.cloud", ".convex.site")]
        last_error = None
        for base in urls:
            url = f"{base}{endpoint}"
            try:
                response = self.client.post(url, headers=self._headers(), json=payload)
                try:
                    payload = response.json()
                except ValueError:
                    payload = None
                if response.status_code == 404:
                    last_error = RuntimeError(f"404 from {url}")
                    continue
                if isinstance(payload, dict) and payload.get("status") == "error":
                    raise RuntimeError(payload.get("errorMessage") or payload.get("message") or payload)
                response.raise_for_status()
                if isinstance(payload, dict) and "result" in payload:
                    return payload["result"]
                return payload
            except Exception as exc:
                last_error = exc
        raise last_error or RuntimeError("Convex call failed")

    def safe_call(self, function_name: str, args: Any) -> Optional[Any]:
        try:
            return self._call(function_name, args)
        except Exception as exc:
            print(f"[Convex] {function_name} failed: {exc}", file=sys.stderr)
            return None

    def upsert_account(self, slug: str, name: str, username: str | None = None, platform: str | None = None, status: str = "active") -> None:
        if not self.base_url:
            return
        self.safe_call("accounts:upsert", {
            "slug": slug,
            "name": name,
            "username": username,
            "platform": platform,
            "status": status,
            "lastSeenLiveAt": int(__import__("time").time() * 1000),
        })

    def upsert_recording(self, slug: str, account_slug: str | None, title: str, file_path: str, file_name: str, status: str = "recording", metadata: Optional[dict[str, Any]] = None) -> None:
        if not self.base_url:
            return
        self.safe_call("recordings:upsert", {
            "slug": slug,
            "accountSlug": account_slug,
            "title": title,
            "filePath": file_path,
            "fileName": file_name,
            "status": status,
            "metadata": metadata or {},
        })

    def upload_file(self, file_path: str, slug: str, account_slug: str | None = None, title: str | None = None) -> dict[str, Any]:
        if not self.base_url:
            raise RuntimeError("CONVEX_DEPLOYMENT is not configured")

        local_path = Path(file_path)
        if not local_path.exists():
            raise FileNotFoundError(file_path)

        filename = local_path.name
        ext = local_path.suffix.lower()
        content_type = {
            ".ts": "video/mp2t",
            ".mp4": "video/mp4",
            ".m3u8": "application/vnd.apple.mpegurl",
            ".flv": "video/x-flv",
        }.get(ext, "application/octet-stream")

        storage_headers = {k: v for k, v in self._headers().items() if k.lower() != "content-type"}
        with local_path.open("rb") as file_obj:
            files = {"file": (filename, file_obj, content_type)}
            response = self.client.post(
                f"{self.base_url}/api/storage",
                headers=storage_headers,
                files=files,
            )

        response.raise_for_status()
        payload = response.json()
        storage_id = payload.get("storageId") or payload.get("id")
        storage_url = payload.get("url") or payload.get("storageUrl")
        if not storage_id or not storage_url:
            raise RuntimeError(f"Unexpected storage response: {payload}")

        return {
            "storageId": storage_id,
            "storageUrl": storage_url,
            "fileName": filename,
            "slug": slug,
            "accountSlug": account_slug,
            "title": title or filename,
        }

    def finalize_recording(self, slug: str, file_path: str, account_slug: str | None = None, title: str | None = None, delete_local: bool = True) -> dict[str, Any]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)

        upload_result = self.upload_file(file_path, slug, account_slug=account_slug, title=title)
        self.safe_call("recordings:markUploaded", {
            "slug": slug,
            "storageId": upload_result["storageId"],
            "storageUrl": upload_result["storageUrl"],
            "deletedFromServer": delete_local,
        })
        if delete_local:
            os.remove(file_path)
        return upload_result

    def finalize_recording_safe(self, slug: str, file_path: str, account_slug: str | None = None, title: str | None = None, delete_local: bool = True) -> Optional[dict[str, Any]]:
        try:
            return self.finalize_recording(slug, file_path, account_slug=account_slug, title=title, delete_local=delete_local)
        except Exception as exc:
            print(f"[Convex] finalize_recording failed: {exc}", file=sys.stderr)
            return None
