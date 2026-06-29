from __future__ import annotations

import logging

from app.config import get_settings
from app.services.settings_service import SettingsService
from app.terminal.main_menu import run_main_menu
from app.utils.logger import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    settings.ensure_export_dir()
    logging.getLogger(__name__).info("Starting %s", settings.app_name)

    database_check = SettingsService().check_database_connection()
    if not database_check["ok"]:
        print("Warning: PostgreSQL is not ready.")
        print(f"Database error: {database_check['message']}")
        print("Run `alembic upgrade head` after PostgreSQL is available.\n")

    run_main_menu()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting Hermina Review Intelligence. Goodbye.")
    except Exception as exc:  # top-level safety net
        logging.getLogger(__name__).exception("Unexpected application error")
        print("An unexpected error occurred.")
        print(f"Error: {exc}")

