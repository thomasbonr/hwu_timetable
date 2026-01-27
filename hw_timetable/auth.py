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


def acquire_token(*, explicit_token: Optional[str] = None) -> str:
    """Return a bearer token using CLI/env/user-provided sources only."""

    candidates = [
        explicit_token.strip() if explicit_token else None,
        os.getenv("HW_TIMETABLE_ACCESS_TOKEN", "").strip() or None,
    ]

    candidates.append(_read_cached_token())

    for token in candidates:
        if token:
            _write_cached_token(token)
            return token

    raise RuntimeError(
        "No API token available. Pass --token or set HW_TIMETABLE_ACCESS_TOKEN."
    )
