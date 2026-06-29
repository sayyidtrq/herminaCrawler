from __future__ import annotations

import re


def parse_rating(value: object) -> int | None:
    if value is None:
        return None
    match = re.search(r"([1-5](?:[.,]0)?)", str(value))
    if not match:
        return None
    rating = int(float(match.group(1).replace(",", ".")))
    return rating if 1 <= rating <= 5 else None


def parse_compact_count(value: object, default: int = 0) -> int:
    if value is None:
        return default
    text = str(value).strip().lower().replace("\xa0", " ")
    match = re.search(r"(\d[\d.,]*)\s*([km]?)", text)
    if not match:
        return default
    number_text, suffix = match.groups()
    if suffix:
        normalized = number_text.replace(",", ".")
        try:
            number = float(normalized)
        except ValueError:
            return default
        multiplier = 1_000 if suffix == "k" else 1_000_000
        return int(number * multiplier)
    digits = re.sub(r"\D", "", number_text)
    return int(digits) if digits else default

