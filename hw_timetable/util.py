"""Utility helpers."""

from __future__ import annotations

import logging
from datetime import date
from zoneinfo import ZoneInfo


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s:%(name)s:%(message)s")


def parse_timezone(tz: str) -> ZoneInfo:
    return ZoneInfo(tz)


def today() -> date:
    return date.today()
