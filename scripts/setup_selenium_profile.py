"""Open the dedicated Selenium profile for one-time manual Google sign-in."""

from __future__ import annotations

import time

from selenium import webdriver
from selenium.webdriver.common.by import By

from app.config import get_settings
from app.services.location_service import LocationService


def main() -> None:
    settings = get_settings()
    locations = LocationService().get_all_locations(active_only=True)
    if not locations:
        raise SystemExit("No active location found.")
    location = locations[0]
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--lang=id-ID")
    if settings.selenium_user_data_dir:
        settings.selenium_user_data_dir.mkdir(parents=True, exist_ok=True)
        options.add_argument(
            f"--user-data-dir={settings.selenium_user_data_dir}"
        )

    driver = webdriver.Chrome(options=options)
    try:
        url = (
            location.google_reviews_url
            or location.google_maps_url
            or "https://www.google.com/maps"
        )
        driver.get(url)
        print("Browser setup window opened.")
        print("1. Sign in to Google manually.")
        print("2. If shown, complete 'Optimize Google Maps' settings.")
        print("3. Return to the Hermina place page and open its Reviews panel.")
        print("Waiting up to 180 seconds...")
        started = time.time()
        while time.time() - started < 180:
            review_cards = driver.find_elements(
                By.CSS_SELECTOR, "div[data-review-id], div.jftiEf"
            )
            review_controls = [
                element
                for element in driver.find_elements(
                    By.CSS_SELECTOR,
                    "button[aria-label*='ulasan' i],"
                    "button[aria-label*='reviews' i],"
                    "[role='button'][aria-label*='ulasan' i],"
                    "[role='button'][aria-label*='reviews' i]",
                )
                if "tulis ulasan"
                not in (
                    (element.text or "")
                    + " "
                    + (element.get_attribute("aria-label") or "")
                ).lower()
            ]
            if review_cards or review_controls:
                print("selenium-profile-login-ready")
                return
            time.sleep(3)
        print("selenium-profile-login-not-detected")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
