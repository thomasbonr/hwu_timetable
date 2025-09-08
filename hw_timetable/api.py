"""API client for HW timetable."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - requests may be missing in tests
    requests = None


BASE_URL = "https://timetableexplorer-api.hw.ac.uk"
ENDPOINTS = [
    "/Student/programme-info",
    "/systemadmin/semesters",
    "/activity/activities",
    "/activity/blocked-out-periods",
    "/activity/ad-hoc",
]


class APIClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        dump_json: bool = False,
        offline: bool = False,
    ) -> None:
        self.token = token
        self.dump_json = dump_json
        self.offline = offline
        self.session = requests.Session() if requests else None
        self.json_dir = Path("out/json")
        self.json_dir.mkdir(parents=True, exist_ok=True)

    def _json_path(self, endpoint: str) -> Path:
        name = endpoint.strip("/").replace("/", "_") + ".json"
        return self.json_dir / name

    def get(self, endpoint: str) -> Any:
        if self.offline:
            with self._json_path(endpoint).open("r", encoding="utf-8") as f:
                return json.load(f)
        if not requests:
            raise RuntimeError("requests is required for network operations")
        url = BASE_URL + endpoint
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        for attempt in range(4):
            try:
                resp = self.session.get(url, headers=headers, timeout=30)
                if resp.status_code == 401 and attempt == 0:
                    logging.info("Token expired, refreshing")
                    from . import auth  # local import to avoid hard dependency

                    self.token = auth.acquire_token()
                    headers["Authorization"] = f"Bearer {self.token}"
                    continue
                if resp.status_code >= 500:
                    time.sleep(2**attempt)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if self.dump_json:
                    with self._json_path(endpoint).open("w", encoding="utf-8") as f:
                        json.dump(data, f)
                return data
            except requests.RequestException as exc:
                logging.warning("Request error: %s", exc)
                time.sleep(2**attempt)
        raise RuntimeError(f"Failed to fetch {endpoint}")
