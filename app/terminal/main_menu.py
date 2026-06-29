from __future__ import annotations

from app.config import get_settings
from app.terminal.analysis_menu import run_analysis_menu
from app.terminal.export_menu import run_export_menu
from app.terminal.fetch_log_menu import run_fetch_log_menu
from app.terminal.fetch_menu import run_fetch_menu
from app.terminal.location_menu import run_location_menu
from app.terminal.review_menu import run_review_menu
from app.terminal.settings_menu import run_settings_menu
from app.terminal.summary_menu import run_summary_menu


def run_main_menu() -> None:
    settings = get_settings()
    print("=" * 40)
    print(f"     {settings.app_name}")
    print("=" * 40)
    print("Fetch, monitor, and analyze Hermina location reviews.")
    print("=" * 40)

    while True:
        print("\nMain Menu\n")
        print("1. Manage Hermina Locations")
        print("2. Fetch / Sync Reviews")
        print("3. View Review Data")
        print("4. Analyze Reviews with Gemini")
        print("5. View Analysis Summary")
        print("6. Export Data")
        print("7. View Fetch Logs")
        print("8. System Settings")
        print("0. Exit")
        choice = input("\nSelect menu: ").strip()
        if choice == "1":
            run_location_menu()
        elif choice == "2":
            run_fetch_menu()
        elif choice == "3":
            run_review_menu()
        elif choice == "4":
            run_analysis_menu()
        elif choice == "5":
            run_summary_menu()
        elif choice == "6":
            run_export_menu()
        elif choice == "7":
            run_fetch_log_menu()
        elif choice == "8":
            run_settings_menu()
        elif choice == "0":
            print("Exiting Hermina Review Intelligence. Goodbye.")
            return
        else:
            print("Invalid menu selection. Please try again.")
