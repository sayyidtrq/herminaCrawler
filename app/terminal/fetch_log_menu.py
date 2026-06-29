from __future__ import annotations

from app.services.fetch_log_service import FetchLogService
from app.services.location_service import LocationService
from app.terminal.common import (
    handle_menu_error,
    parse_int,
    pause,
    print_heading,
    show_locations,
)
from app.utils.date_parser import format_datetime
from app.utils.formatter import print_table, truncate


def run_fetch_log_menu() -> None:
    service = FetchLogService()
    locations = LocationService()
    while True:
        print_heading("View Fetch Logs")
        print("1. View Latest Fetch Logs")
        print("2. View Fetch Logs by Location")
        print("3. View Failed Fetch Logs")
        print("0. Back to Main Menu")
        choice = input("\nSelect menu: ").strip()
        try:
            if choice == "1":
                _show_logs(service.get_logs())
            elif choice == "2":
                all_locations = locations.get_all_locations()
                show_locations(all_locations)
                if not all_locations:
                    pause()
                    continue
                location_id = parse_int(
                    input("\nLocation ID: ").strip(), "Location ID"
                )
                _show_logs(service.get_logs(location_id=location_id))
            elif choice == "3":
                _show_logs(service.get_logs(failed_only=True))
            elif choice == "0":
                return
            else:
                print("Invalid menu selection. Please try again.")
                continue
            pause()
        except Exception as exc:
            handle_menu_error(exc)
            pause()


def _show_logs(logs: list[dict]) -> None:
    print_table(
        [
            "ID",
            "Location",
            "Source",
            "Status",
            "Fetched",
            "Inserted",
            "Duplicate",
            "Failed",
            "Started At",
            "Error",
        ],
        [
            [
                log["id"],
                log["location"],
                log["source"],
                log["status"],
                log["total_fetched"],
                log["total_inserted"],
                log["total_duplicate"],
                log["total_failed"],
                format_datetime(log["started_at"]),
                truncate(log["error_message"] or "", 30),
            ]
            for log in logs
        ],
    )

