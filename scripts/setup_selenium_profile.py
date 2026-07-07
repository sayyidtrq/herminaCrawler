"""Open the dedicated Chrome profile for one-time manual Google sign-in.

Google often rejects account login from a WebDriver-controlled browser. This
setup helper intentionally opens normal Chrome with the same user data
directory that Selenium will reuse later.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app.config import get_settings
from app.services.location_service import LocationService


def _find_chrome() -> Path | None:
    candidates = [
        os.getenv("CHROME_PATH"),
        os.getenv("SELENIUM_CHROME_BINARY"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(
            Path.home()
            / "AppData"
            / "Local"
            / "Google"
            / "Chrome"
            / "Application"
            / "chrome.exe"
        ),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    return None


def _target_url() -> str:
    locations = LocationService().get_all_locations(active_only=True)
    if not locations:
        return "https://www.google.com/maps"
    location = locations[0]
    return (
        location.google_reviews_url
        or location.google_maps_url
        or "https://www.google.com/maps"
    )


def main() -> None:
    settings = get_settings()
    profile_dir = settings.selenium_user_data_dir
    if profile_dir is None:
        raise SystemExit(
            "SELENIUM_USER_DATA_DIR is empty. Set it to a dedicated folder "
            "such as .selenium-profile."
        )
    profile_dir.mkdir(parents=True, exist_ok=True)

    chrome_path = _find_chrome()
    if chrome_path is None:
        raise SystemExit(
            "Chrome executable was not found. Set CHROME_PATH to chrome.exe "
            "and run this command again."
        )

    url = _target_url()
    args = [
        str(chrome_path),
        f"--user-data-dir={profile_dir}",
        "--profile-directory=Default",
        "--lang=id-ID",
        "--new-window",
        url,
    ]
    subprocess.Popen(args)

    print("Normal Chrome setup window opened.")
    print(f"Profile directory: {profile_dir}")
    print("1. Sign in to Google manually in that Chrome window.")
    print("2. If shown, complete Google Maps setup/consent screens.")
    print("3. Open the target Google Maps place and its Reviews panel.")
    print("4. Close the Chrome window before running Selenium fetch.")
    print()
    input("Press Enter here after the setup Chrome window is closed...")
    print("selenium-profile-setup-ready")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Setup cancelled.")
