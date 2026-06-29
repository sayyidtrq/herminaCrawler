from __future__ import annotations

from app.services.analysis_service import AnalysisService
from app.services.location_service import LocationService
from app.services.review_service import ReviewService
from app.terminal.common import (
    ask_yes_no,
    handle_menu_error,
    parse_int,
    pause,
    print_heading,
    show_analysis_result,
    show_locations,
)
from app.utils.date_parser import format_datetime


def run_analysis_menu() -> None:
    service = AnalysisService()
    locations = LocationService()
    reviews = ReviewService()
    while True:
        print_heading("Analyze Reviews with Gemini")
        print("1. Analyze All Pending Reviews")
        print("2. Analyze Reviews by Location")
        print("3. Analyze Reviews by Rating")
        print("4. Re-run Analysis for Selected Review")
        print("5. Re-run Analysis by Location")
        print("0. Back to Main Menu")
        choice = input("\nSelect menu: ").strip()
        try:
            if choice == "1":
                show_analysis_result(service.analyze_pending())
                pause()
            elif choice == "2":
                location_id = _select_location(locations)
                if location_id is not None:
                    show_analysis_result(
                        service.analyze_pending(location_id=location_id)
                    )
                    pause()
            elif choice == "3":
                rating = parse_int(input("Rating (1-5): ").strip(), "Rating")
                if not 1 <= rating <= 5:
                    raise ValueError("Rating must be between 1 and 5.")
                show_analysis_result(service.analyze_pending(rating=rating))
                pause()
            elif choice == "4":
                _rerun_review(service, reviews)
            elif choice == "5":
                location_id = _select_location(locations)
                if location_id is not None and ask_yes_no(
                    "Re-run analysis for every review at this location?",
                    default=False,
                ):
                    show_analysis_result(service.rerun_location(location_id))
                    pause()
            elif choice == "0":
                return
            else:
                print("Invalid menu selection. Please try again.")
        except Exception as exc:
            handle_menu_error(exc)
            pause()


def _select_location(service: LocationService) -> int | None:
    locations = service.get_all_locations()
    show_locations(locations)
    if not locations:
        pause()
        return None
    return parse_int(input("\nLocation ID: ").strip(), "Location ID")


def _rerun_review(
    analysis_service: AnalysisService, review_service: ReviewService
) -> None:
    review_id = parse_int(input("Review ID: ").strip(), "Review ID")
    review = review_service.get_review(review_id)
    if review is None:
        raise ValueError("Review not found.")
    print(f"\nLocation : {review['location']}")
    print(f"Rating   : {review['rating'] or '-'}")
    print(f"Reviewer : {review['reviewer_name']}")
    print(f"Time     : {format_datetime(review['review_time'])}")
    print(f"Review   : {review['review_text']}")
    if ask_yes_no("Re-run analysis?", default=False):
        show_analysis_result(analysis_service.rerun_review(review_id))
    else:
        print("Analysis cancelled.")
    pause()

