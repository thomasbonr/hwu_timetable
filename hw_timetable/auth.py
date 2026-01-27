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

TOKEN_CACHE_PATH = Path(os.path.expanduser("~/.cache/hw_timetable/token.txt"))


def _normalize_token(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    token = value.strip()
    if not token:
        return None
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token or None


def _read_cached_token() -> Optional[str]:
    if TOKEN_CACHE_PATH.exists():
        try:
            cached = TOKEN_CACHE_PATH.read_text(encoding="utf-8")
            normalized = _normalize_token(cached)
            if normalized:
                return normalized
        except OSError as exc:  # pragma: no cover - disk issues are rare
            logging.warning("Failed to read cached token: %s", exc)
    return None


def _write_cached_token(token: str) -> None:
    normalized = _normalize_token(token)
    if not normalized:
        return
    try:
        TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE_PATH.write_text(normalized, encoding="utf-8")
    except OSError as exc:  # pragma: no cover
        logging.warning("Failed to write token cache: %s", exc)


def acquire_token(*, explicit_token: Optional[str] = None) -> str:
    """Return a bearer token using CLI/env/user-provided sources only."""

    candidates = [
        _normalize_token(explicit_token),
        _normalize_token(os.getenv("HW_TIMETABLE_ACCESS_TOKEN")),
    ]

    candidates.append(_read_cached_token())

    for token in candidates:
        if token:
            _write_cached_token(token)
            return token

    raise RuntimeError(
        "No API token available. Pass --token or set HW_TIMETABLE_ACCESS_TOKEN."
    )
