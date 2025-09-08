"""Authentication helpers using MSAL."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import msal

AUTHORITY = "https://login.microsoftonline.com/6c425ff2-6865-42df-a4db-8e6af634813d"
CLIENT_ID = "9f069110-869b-4b7a-9dc9-8c80eec3df3c"
SCOPES = [
    "api://76ae141c-6671-45b5-8d6c-a4325e0a0032/student-timetable",
    "offline_access",
    "openid",
    "profile",
]
CACHE_PATH = Path(os.path.expanduser("~/.cache/hw_timetable/msal_cache.bin"))


def _load_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if CACHE_PATH.exists():
        try:
            cache.deserialize(CACHE_PATH.read_text())
        except Exception as exc:  # pragma: no cover - corruption is rare
            logging.warning("Failed to deserialize cache: %s", exc)
    return cache


def _save_cache(cache: msal.SerializableTokenCache) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(cache.serialize())


def acquire_token() -> str:
    """Acquire an access token using MSAL or environment fallback."""
    cache = _load_cache()
    app = msal.PublicClientApplication(
        CLIENT_ID, authority=AUTHORITY, token_cache=cache
    )
    accounts = app.get_accounts()
    result: Optional[dict] = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if not result:
        try:
            flow = app.initiate_device_flow(scopes=SCOPES)
        except Exception as exc:  # pragma: no cover - network errors
            logging.error("Device flow init failed: %s", exc)
            flow = None
        if flow and "user_code" in flow:
            print(flow["message"])  # pragma: no cover - interactive
            result = app.acquire_token_by_device_flow(flow)
        if not result or "access_token" not in result:
            token = os.getenv("HW_TIMETABLE_ACCESS_TOKEN")
            if not token:
                raise RuntimeError("Could not obtain access token")
            return token
    if "access_token" in result:
        _save_cache(cache)
        return result["access_token"]
    raise RuntimeError("Failed to acquire token")
