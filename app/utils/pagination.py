from __future__ import annotations

from collections.abc import Callable


def run_paginated(
    fetch_page: Callable[[int, int], tuple[list[dict], int]],
    render_page: Callable[[list[dict], int, int], None],
    page_size: int,
) -> None:
    page = 1
    while True:
        items, total = fetch_page(page, page_size)
        if not items:
            print("No reviews found.")
            return
        total_pages = max(1, (total + page_size - 1) // page_size)
        render_page(items, page, total_pages)
        if total_pages == 1:
            return
        choice = input("[N]ext, [P]revious, [Q]uit: ").strip().lower()
        if choice == "n" and page < total_pages:
            page += 1
        elif choice == "p" and page > 1:
            page -= 1
        elif choice in {"q", ""}:
            return

