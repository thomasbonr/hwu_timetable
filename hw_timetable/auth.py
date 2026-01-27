"""Lightweight token helpers.

The HW timetable API ultimately expects an ``Authorization: Bearer`` header. To
keep the CLI predictable, we now rely entirely on user-provided tokens rather
than attempting MSAL device flows.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

try:  # requests is optional during offline tests
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled gracefully below
    requests = None

TOKEN_CACHE_PATH = Path(os.path.expanduser("~/.cache/hw_timetable/token.txt"))


def _read_cached_token() -> Optional[str]:
    if TOKEN_CACHE_PATH.exists():
        try:
            cached = TOKEN_CACHE_PATH.read_text(encoding="utf-8").strip()
            if cached:
                return cached
        except OSError as exc:  # pragma: no cover - disk issues are rare
            logging.warning("Failed to read cached token: %s", exc)
    return None


def _write_cached_token(token: str) -> None:
    try:
        TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE_PATH.write_text(token.strip(), encoding="utf-8")
    except OSError as exc:  # pragma: no cover
        logging.warning("Failed to write token cache: %s", exc)


def _fetch_token_from_url(token_url: str) -> Optional[str]:
    if not token_url:
        return None
    if not requests:
        raise RuntimeError(
            "requests is required to download tokens via --token-url; install it first"
        )
    try:
        resp = requests.get(token_url, timeout=15)
        resp.raise_for_status()
        token = resp.text.strip()
        if not token:
            logging.warning("Token URL %s returned an empty response", token_url)
            return None
        return token
    except requests.RequestException as exc:  # pragma: no cover - network dependent
        logging.error("Failed to fetch token from %s: %s", token_url, exc)
        return None


def acquire_token(*, explicit_token: Optional[str] = None, token_url: Optional[str] = None) -> str:
    """Return a bearer token using CLI/env/user-provided sources only."""

    candidates = [
        explicit_token.strip() if explicit_token else None,
        os.getenv("HW_TIMETABLE_ACCESS_TOKEN", "").strip() or None,
    ]

    if token_url:
        candidates.append(_fetch_token_from_url(token_url))

    candidates.append(_read_cached_token())

    for token in candidates:
        if token:
            _write_cached_token(token)
            return token

    raise RuntimeError(
        "No API token available. Pass --token, set HW_TIMETABLE_ACCESS_TOKEN, or provide --token-url."
    )
