from __future__ import annotations

import re
from datetime import datetime, timedelta


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


# Google Maps review timestamps only ever arrive as coarse relative text
# ("2 minggu lalu", "a year ago"), never as absolute dates, so day/month/year
# are treated as fixed-length approximations rather than calendar-accurate spans.
_UNIT_SECONDS: dict[str, int] = {
    "second": 1,
    "detik": 1,
    "minute": 60,
    "menit": 60,
    "hour": 3600,
    "jam": 3600,
    "day": 86400,
    "hari": 86400,
    "week": 7 * 86400,
    "minggu": 7 * 86400,
    "pekan": 7 * 86400,
    "month": 30 * 86400,
    "bulan": 30 * 86400,
    "year": 365 * 86400,
    "tahun": 365 * 86400,
}

_JUST_NOW_PATTERNS = (
    "baru saja",
    "beberapa saat",
    "beberapa detik",
    "just now",
    "moments ago",
)

_SINGLE_UNIT_WORDS = {
    "sehari": "hari",
    "seminggu": "minggu",
    "sepekan": "minggu",
    "sebulan": "bulan",
    "setahun": "tahun",
    "kemarin": "hari",
    "yesterday": "hari",
    "a": None,  # resolved via following word, e.g. "a day ago"
    "an": None,
}

_NUMBER_WORDS = {
    "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5,
    "enam": 6, "tujuh": 7, "delapan": 8, "sembilan": 9, "sepuluh": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

_RELATIVE_PATTERN = re.compile(
    r"(?P<amount>\d+|satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh"
    r"|one|two|three|four|five|six|seven|eight|nine|ten|a|an)\s+"
    r"(?P<unit>detik|menit|jam|hari|minggu|pekan|bulan|tahun"
    r"|second|minute|hour|day|week|month|year)s?",
    re.IGNORECASE,
)


def _resolve_amount(raw: str) -> int:
    raw = raw.lower()
    if raw in {"a", "an"}:
        return 1
    if raw.isdigit():
        return int(raw)
    return _NUMBER_WORDS.get(raw, 1)


def parse_relative_datetime(
    text: str | None, reference: datetime | None = None
) -> datetime | None:
    """Parse Indonesian/English relative-time strings from Google Maps reviews.

    Examples handled: "2 minggu lalu", "sehari yang lalu", "kemarin",
    "a year ago", "3 hours ago", "baru saja".
    """
    if not text:
        return None
    reference = reference or datetime.now().astimezone()
    normalized = text.strip().lower()
    if not normalized:
        return None

    if any(pattern in normalized for pattern in _JUST_NOW_PATTERNS):
        return reference

    for word, unit in _SINGLE_UNIT_WORDS.items():
        if unit and word in normalized:
            return reference - timedelta(seconds=_UNIT_SECONDS[unit])

    match = _RELATIVE_PATTERN.search(normalized)
    if match:
        amount = _resolve_amount(match.group("amount"))
        unit = match.group("unit").lower()
        seconds = _UNIT_SECONDS.get(unit)
        if seconds is not None:
            return reference - timedelta(seconds=amount * seconds)

    return None


def is_within_date_range(
    review_time: datetime | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> bool:
    """True if review_time falls within [date_from, date_to] (bounds optional).

    A missing review_time is always treated as in-range: we'd rather keep an
    undated review than silently drop it because we couldn't resolve a date.
    """
    if review_time is None:
        return True
    if date_from is not None and review_time < date_from:
        return False
    if date_to is not None and review_time > date_to:
        return False
    return True


DATE_PRESETS = {
    "today",
    "yesterday",
    "last_7_days",
    "last_30_days",
    "this_month",
    "custom",
}


def resolve_date_range(
    preset: str | None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    reference: datetime | None = None,
) -> tuple[datetime | None, datetime | None]:
    """Resolve a date_preset (or explicit custom range) into (date_from, date_to)."""
    reference = reference or datetime.now().astimezone()
    if not preset or preset == "custom":
        return date_from, date_to

    today_start = reference.replace(hour=0, minute=0, second=0, microsecond=0)
    if preset == "today":
        return today_start, reference
    if preset == "yesterday":
        yesterday_start = today_start - timedelta(days=1)
        return yesterday_start, today_start
    if preset == "last_7_days":
        return today_start - timedelta(days=7), reference
    if preset == "last_30_days":
        return today_start - timedelta(days=30), reference
    if preset == "this_month":
        return today_start.replace(day=1), reference
    return date_from, date_to
