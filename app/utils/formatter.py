from __future__ import annotations

from typing import Iterable, Sequence


def truncate(value: object, length: int = 40) -> str:
    text = "" if value is None else str(value)
    if len(text) <= length:
        return text
    return text[: max(0, length - 3)] + "..."


def print_table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    materialized = [list(row) for row in rows]
    if not materialized:
        print("(no data)")
        return
    try:
        from tabulate import tabulate

        print(tabulate(materialized, headers=headers, tablefmt="simple"))
    except ImportError:
        widths = [len(str(header)) for header in headers]
        for row in materialized:
            for index, value in enumerate(row):
                widths[index] = max(widths[index], len(str(value)))
        print(" | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)))
        print("-+-".join("-" * width for width in widths))
        for row in materialized:
            print(
                " | ".join(
                    str(value).ljust(widths[index])
                    for index, value in enumerate(row)
                )
            )

