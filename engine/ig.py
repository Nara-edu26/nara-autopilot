"""Klien kecil untuk Instagram API with Instagram Login (graph.instagram.com)."""
from __future__ import annotations

import time

import requests


class IGError(RuntimeError):
    def __init__(self, status: int, payload: dict):
        err = (payload or {}).get("error", {}) if isinstance(payload, dict) else {}
        self.code = err.get("code")
        self.subcode = err.get("error_subcode")
        self.message = err.get("error_user_msg") or err.get("message") or str(payload)[:300]
        super().__init__(f"HTTP {status} · kode {self.code}/{self.subcode}: {self.message}")

    @property
    def token_mati(self) -> bool:
        return self.code == 190


class IG:
    def __init__(self, token: str, host: str = "https://graph.instagram.com", versi: str = ""):
        self.token = token
        self.host = host.rstrip("/")
        self.base = host.rstrip("/") + (f"/{versi.strip('/')}" if versi else "")
        self.s = requests.Session()

    def _req(self, method: str, path: str, **params):
        params["access_token"] = self.token
        url = f"{self.base}/{path.lstrip('/')}"
        for attempt in range(4):
            r = self.s.request(method, url, params=params if method == "GET" else None,
                               data=params if method != "GET" else None, timeout=60)
            try:
                payload = r.json()
            except ValueError:
                payload = {"error": {"message": r.text[:300]}}
            if r.ok and not (isinstance(payload, dict) and "error" in payload):
                return payload
            err = IGError(r.status_code, payload)
            # 2 / 4 / 17 / 32 / 613 = sementara atau batas laju: coba lagi pelan-pelan
            if err.code in (1, 2, 4, 17, 32, 613) and attempt < 3:
                time.sleep(20 * (attempt + 1))
                continue
            raise err
        raise RuntimeError("tidak tercapai")

    def get(self, path: str, **params):
        return self._req("GET", path, **params)

    def post(self, path: str, **params):
        return self._req("POST", path, **params)

    # --- akun ---
    def me(self) -> dict:
        return self.get("me", fields="user_id,username,account_type,followers_count,media_count")

    # --- terbit ---
    def create(self, ig_id: str, **params) -> str:
        clean = {k: (str(v).lower() if isinstance(v, bool) else v) for k, v in params.items() if v is not None}
        return self.post(f"{ig_id}/media", **clean)["id"]

    def wait(self, container_id: str, timeout: int = 600) -> None:
        t0 = time.time()
        delay = 5
        while True:
            st = self.get(container_id, fields="status_code,status")
            code = st.get("status_code")
            if code == "FINISHED":
                return
            if code in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"container {container_id} {code}: {st.get('status')}")
            if time.time() - t0 > timeout:
                raise TimeoutError(f"container {container_id} belum selesai setelah {timeout} detik ({code})")
            time.sleep(delay)
            delay = min(delay + 5, 30)

    def publish(self, ig_id: str, container_id: str) -> str:
        return self.post(f"{ig_id}/media_publish", creation_id=container_id)["id"]

    def limit(self, ig_id: str) -> dict:
        return self.get(f"{ig_id}/content_publishing_limit", fields="quota_usage,config")

    # --- data ---
    def media_info(self, media_id: str) -> dict:
        return self.get(media_id, fields="permalink,timestamp,media_type,media_product_type,like_count,comments_count")

    def insights(self, media_id: str, metrics: list[str]) -> dict:
        data = self.get(f"{media_id}/insights", metric=",".join(metrics))
        out = {}
        for m in data.get("data", []):
            vals = m.get("values") or [{}]
            out[m["name"]] = m.get("total_value", {}).get("value", vals[0].get("value"))
        return out

    def comments(self, media_id: str, limit: int = 50) -> list[dict]:
        return self.get(f"{media_id}/comments", fields="text,timestamp,like_count", limit=limit).get("data", [])

    def refresh_token(self) -> dict:
        r = self.s.get(f"{self.host}/refresh_access_token",
                       params={"grant_type": "ig_refresh_token", "access_token": self.token}, timeout=60)
        payload = r.json()
        if not r.ok or "error" in payload:
            raise IGError(r.status_code, payload)
        return payload
