from __future__ import annotations

from app.config import get_settings
from app.services.location_service import LocationService
from app.services.review_service import ReviewService
from app.terminal.common import (
    handle_menu_error,
    parse_int,
    pause,
    print_heading,
    show_locations,
    show_reviews,
)
from app.utils.pagination import run_paginated


def run_review_menu() -> None:
    service = ReviewService()
    locations = LocationService()
    settings = get_settings()
    while True:
        print_heading("View Review Data")
        print("1. View All Reviews")
        print("2. View Reviews by Location")
        print("3. View Reviews by Rating")
        print("4. View Reviews by Sentiment")
        print("5. Search Review Text")
        print("6. View Latest Reviews")
        print("0. Back to Main Menu")
        choice = input("\nSelect menu: ").strip()
        try:
            filters: dict = {}
            if choice == "1":
                pass
            elif choice == "2":
                all_locations = locations.get_all_locations()
                show_locations(all_locations)
                if not all_locations:
                    pause()
                    continue
                filters["location_id"] = parse_int(
                    input("\nLocation ID: ").strip(), "Location ID"
                )
            elif choice == "3":
                rating = parse_int(input("Rating (1-5): ").strip(), "Rating")
                if not 1 <= rating <= 5:
                    raise ValueError("Rating must be between 1 and 5.")
                filters["rating"] = rating
            elif choice == "4":
                sentiment = input(
                    "Sentiment (positive/neutral/negative/mixed/unknown): "
                ).strip().lower()
                if sentiment not in {
                    "positive",
                    "neutral",
                    "negative",
                    "mixed",
                    "unknown",
                }:
                    raise ValueError("Invalid sentiment.")
                filters["sentiment"] = sentiment
            elif choice == "5":
                keyword = input("Search keyword: ").strip()
                if not keyword:
                    raise ValueError("Search keyword is required.")
                filters["keyword"] = keyword
            elif choice == "6":
                filters["latest_first"] = True
            elif choice == "0":
                return
            else:
                print("Invalid menu selection. Please try again.")
                continue

            _show_paginated(service, settings.page_size, **filters)
            pause()
        except Exception as exc:
            handle_menu_error(exc)
            pause()


def _show_paginated(service: ReviewService, page_size: int, **filters) -> None:
    def fetch(page: int, size: int):
        return service.get_reviews(page=page, page_size=size, **filters)

    run_paginated(fetch, show_reviews, page_size)

