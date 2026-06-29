from __future__ import annotations

from datetime import datetime


def parse_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def format_datetime(value: datetime | None, include_time: bool = True) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M" if include_time else "%Y-%m-%d")

