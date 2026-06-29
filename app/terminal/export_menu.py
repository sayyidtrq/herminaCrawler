from __future__ import annotations

from app.services.export_service import ExportService
from app.services.location_service import LocationService
from app.terminal.common import (
    handle_menu_error,
    parse_int,
    pause,
    print_heading,
    show_locations,
)


def run_export_menu() -> None:
    service = ExportService()
    locations = LocationService()
    while True:
        print_heading("Export Data")
        print("1. Export All Reviews to CSV")
        print("2. Export Reviews by Location to CSV")
        print("3. Export Analysis Summary to CSV")
        print("4. Export Raw Reviews to JSON")
        print("0. Back to Main Menu")
        choice = input("\nSelect menu: ").strip()
        try:
            if choice == "1":
                path = service.export_all_reviews_csv()
            elif choice == "2":
                all_locations = locations.get_all_locations()
                show_locations(all_locations)
                if not all_locations:
                    pause()
                    continue
                location_id = parse_int(
                    input("\nLocation ID: ").strip(), "Location ID"
                )
                path = service.export_location_reviews_csv(location_id)
            elif choice == "3":
                path = service.export_analysis_summary_csv()
            elif choice == "4":
                path = service.export_raw_reviews_json()
            elif choice == "0":
                return
            else:
                print("Invalid menu selection. Please try again.")
                continue
            print("\nExport completed.")
            try:
                display_path = path.relative_to(path.parent.parent)
            except ValueError:
                display_path = path
            print(f"File saved to: {display_path}")
            pause()
        except Exception as exc:
            handle_menu_error(exc)
            pause()

