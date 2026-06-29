from __future__ import annotations

from app.services.settings_service import SettingsService
from app.terminal.common import handle_menu_error, pause, print_heading


def run_settings_menu() -> None:
    service = SettingsService()
    while True:
        print_heading("System Settings")
        print("1. Check Database Connection")
        print("2. Check Gemini API Key")
        print("3. Check Review Source API Key")
        print("4. Show App Configuration")
        print("0. Back to Main Menu")
        choice = input("\nSelect menu: ").strip()
        try:
            if choice == "1":
                result = service.check_database_connection()
                status = "OK" if result["ok"] else "FAILED"
                print(f"\nDatabase connection: {status}")
                if not result["ok"]:
                    print(f"Error: {result['message']}")
            elif choice == "2":
                result = service.check_gemini_key()
                print(
                    "\nGemini API Key: "
                    + ("FOUND" if result["found"] else "NOT FOUND")
                )
                if result["found"]:
                    print(f"Value: {result['masked']}")
            elif choice == "3":
                result = service.check_review_source_key()
                print(
                    "\nReview Source API Key: "
                    + ("FOUND" if result["found"] else "NOT FOUND")
                )
                if result["found"]:
                    print(f"Value: {result['masked']}")
            elif choice == "4":
                print_heading("App Configuration")
                for key, value in service.public_configuration().items():
                    print(f"{key:<28}: {value}")
            elif choice == "0":
                return
            else:
                print("Invalid menu selection. Please try again.")
                continue
            pause()
        except Exception as exc:
            handle_menu_error(exc)
            pause()

