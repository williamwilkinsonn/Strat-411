"""
Jersey Mike's US Store Location Scraper

This script scrapes all Jersey Mike's store locations in the United States
and saves the data (location name, street address, city, state, zip code)
to both CSV and JSON files.

Two scraping methods are supported:
1. API method (default): Uses Jersey Mike's internal API for reliable,
   structured data retrieval.
2. HTML method: Scrapes the website HTML directly using BeautifulSoup
   and configurable CSS selectors.

Usage:
    python scraper.py              # Uses the default method from config.py
    python scraper.py --method api  # Force API method
    python scraper.py --method html # Force HTML scraping method

For configuration options, see config.py.
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

import config

# ==============================================================================
# LOGGING SETUP
# ==============================================================================


def setup_logging():
    """Configure logging based on settings in config.py."""
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)

    handlers = [logging.StreamHandler(sys.stdout)]
    if config.LOG_FILE:
        handlers.append(logging.FileHandler(config.LOG_FILE))

    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)
    return logging.getLogger(__name__)


logger = setup_logging()


# ==============================================================================
# HTTP REQUEST HELPERS
# ==============================================================================


def make_request(url, headers=None, params=None):
    """
    Make an HTTP GET request with retry logic and rate limiting.

    Args:
        url: The URL to request.
        headers: Optional dict of HTTP headers.
        params: Optional dict of query parameters.

    Returns:
        requests.Response object on success.

    Raises:
        requests.RequestException: If all retries fail.
    """
    if headers is None:
        headers = config.REQUEST_HEADERS

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            logger.debug("Requesting: %s (attempt %d/%d)", url, attempt, config.MAX_RETRIES)
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            # Rate limiting: wait between requests to be respectful
            time.sleep(config.REQUEST_DELAY)
            return response

        except requests.RequestException as e:
            logger.warning(
                "Request failed (attempt %d/%d): %s - %s",
                attempt,
                config.MAX_RETRIES,
                url,
                e,
            )
            if attempt < config.MAX_RETRIES:
                wait_time = config.RETRY_DELAY * attempt
                logger.info("Retrying in %d seconds...", wait_time)
                time.sleep(wait_time)
            else:
                logger.error("All %d attempts failed for: %s", config.MAX_RETRIES, url)
                raise


# ==============================================================================
# API SCRAPING METHOD (Recommended)
# ==============================================================================


def scrape_via_api():
    """
    Scrape store locations using Jersey Mike's internal API.

    This method is more reliable than HTML scraping because it returns
    structured JSON data directly from the server.

    The API flow:
    1. GET /stores/subdivision -> returns list of US states/subdivisions
    2. For each state, GET /stores/bySubdivision?subdivisionCode={state}
       -> returns all stores in that state

    Returns:
        list of dict: Each dict contains location_name, street_address,
                      city, state, and zip_code.
    """
    locations = []

    # Step 1: Get all US state/subdivision codes
    logger.info("Fetching US state subdivision codes from API...")
    try:
        response = make_request(config.API_SUBDIVISIONS_URL, headers=config.API_HEADERS)
        data = response.json()
        subdivisions = data.get("data", {}).get("storeSubdivisionCounts", [])
        logger.info("Found %d state subdivisions", len(subdivisions))
    except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
        logger.error("Failed to fetch subdivision data: %s", e)
        return locations

    # Step 2: For each state, fetch all store locations
    for i, subdivision in enumerate(subdivisions, 1):
        state_code = subdivision.get("subdivisionCode", "")
        store_count = subdivision.get("count", 0)
        logger.info(
            "Fetching stores for %s (%d expected) [%d/%d states]",
            state_code,
            store_count,
            i,
            len(subdivisions),
        )

        try:
            response = make_request(
                config.API_STORES_BY_STATE_URL,
                headers=config.API_HEADERS,
                params={
                    "subdivisionCode": state_code,
                    "pageSize": config.API_PAGE_SIZE,
                    "pageNumber": 0,
                },
            )
            data = response.json()
            stores = data.get("data", {}).get("openStores", [])

            for store in stores:
                address = store.get("address", {})
                location = {
                    "location_name": store.get("name", "").strip(),
                    "street_address": address.get("street1", "").strip(),
                    "city": address.get("city", "").strip(),
                    "state": address.get("state", "").strip(),
                    "zip_code": address.get("zip", "").strip(),
                }

                # Append street2 to street_address if it exists
                street2 = address.get("street2", "").strip()
                if street2:
                    location["street_address"] += f", {street2}"

                locations.append(location)

            logger.info("  -> Retrieved %d stores for %s", len(stores), state_code)

        except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
            logger.error("Failed to fetch stores for %s: %s", state_code, e)
            continue

    return locations


# ==============================================================================
# HTML SCRAPING METHOD (Fallback)
# ==============================================================================


def get_max_pages(soup):
    """
    Determine the maximum number of pages for a state's location listing.

    Inspects the pagination links at the bottom of the page to find the
    highest page number.

    Args:
        soup: BeautifulSoup object of the state's location page.

    Returns:
        int: The maximum page number (at least 1).
    """
    max_page = 1
    pagination_links = soup.select(config.SELECTORS["pagination"])

    for link in pagination_links:
        text = link.get_text(strip=True)
        if text.isdigit():
            page_num = int(text)
            if page_num > max_page:
                max_page = page_num

    return max_page


def parse_location_card(card, state_code):
    """
    Parse a single location card element to extract store information.

    This function uses the CSS selectors defined in config.py to find
    each piece of information within the location card HTML.

    Args:
        card: BeautifulSoup element for a single store location.
        state_code: The state abbreviation being scraped.

    Returns:
        dict or None: Location data dict, or None if parsing fails.
    """
    try:
        # Extract each field using the CSS selectors from config.py
        # If a selector doesn't match, we use an empty string as fallback

        name_el = card.select_one(config.SELECTORS["store_name"])
        street_el = card.select_one(config.SELECTORS["street_address"])
        city_el = card.select_one(config.SELECTORS["city"])
        state_el = card.select_one(config.SELECTORS["state"])
        zip_el = card.select_one(config.SELECTORS["zip_code"])

        location = {
            "location_name": name_el.get_text(strip=True) if name_el else "",
            "street_address": street_el.get_text(strip=True) if street_el else "",
            "city": city_el.get_text(strip=True) if city_el else "",
            "state": state_el.get_text(strip=True) if state_el else state_code,
            "zip_code": zip_el.get_text(strip=True) if zip_el else "",
        }

        # Clean up: remove trailing commas from city names
        location["city"] = location["city"].rstrip(",").strip()

        # Only return if we got at least a street address
        if location["street_address"]:
            return location
        else:
            logger.debug("Skipping location with no street address found")
            return None

    except Exception as e:
        logger.debug("Error parsing location card: %s", e)
        return None


def scrape_state_html(state_code):
    """
    Scrape all store locations for a single US state using HTML parsing.

    Navigates through all pagination pages for the given state and extracts
    location data from each page.

    Args:
        state_code: Two-letter US state abbreviation (e.g., "CA", "NY").

    Returns:
        list of dict: Store locations found in this state.
    """
    locations = []
    state_url = f"{config.BASE_URL}/locations/{state_code}"

    # First, determine how many pages of results exist for this state
    try:
        response = make_request(f"{state_url}?page=1")
        soup = BeautifulSoup(response.text, "lxml")
        max_page = get_max_pages(soup)
        logger.info("  State %s has %d page(s) of locations", state_code, max_page)
    except requests.RequestException:
        logger.error("  Failed to load initial page for state %s", state_code)
        return locations

    # Scrape each page
    for page_num in range(1, max_page + 1):
        page_url = f"{state_url}?page={page_num}"
        logger.debug("  Scraping page %d/%d: %s", page_num, max_page, page_url)

        try:
            # For page 1, reuse the soup we already have
            if page_num > 1:
                response = make_request(page_url)
                soup = BeautifulSoup(response.text, "lxml")

            # Find all location/address containers on this page
            # The address_container selector targets the parent element of each
            # store's address block (typically <p itemprop="address"> or similar)
            address_containers = soup.select(config.SELECTORS["address_container"])

            if not address_containers:
                logger.warning(
                    "  No location containers found on page %d. "
                    "The CSS selectors in config.py may need updating.",
                    page_num,
                )
                continue

            for container in address_containers:
                # Walk up to the parent card element to get the store name
                # The name is often in a sibling or parent element
                card = container.parent
                location = parse_location_card(card, state_code)
                if location:
                    locations.append(location)

        except requests.RequestException:
            logger.error("  Failed to scrape page %d for state %s", page_num, state_code)
            continue

    return locations


def scrape_via_html():
    """
    Scrape store locations by parsing HTML pages for each US state.

    This method iterates through all US states listed in config.py,
    visits each state's location page, and extracts store information
    using the CSS selectors defined in config.py.

    Returns:
        list of dict: All store locations found across all states.
    """
    all_locations = []

    logger.info("Starting HTML scraping for %d states...", len(config.US_STATES))

    for i, state_code in enumerate(config.US_STATES, 1):
        logger.info("Scraping state %s [%d/%d]", state_code, i, len(config.US_STATES))
        state_locations = scrape_state_html(state_code)
        all_locations.extend(state_locations)
        logger.info("  -> Found %d locations in %s", len(state_locations), state_code)

    return all_locations


# ==============================================================================
# OUTPUT FUNCTIONS
# ==============================================================================


def save_to_csv(locations, filepath):
    """
    Save location data to a CSV file.

    Args:
        locations: list of dict with location data.
        filepath: Path to the output CSV file.
    """
    if not locations:
        logger.warning("No locations to save to CSV")
        return

    fieldnames = ["location_name", "street_address", "city", "state", "zip_code"]

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(locations)

    logger.info("Saved %d locations to CSV: %s", len(locations), filepath)


def save_to_json(locations, filepath):
    """
    Save location data to a JSON file.

    Args:
        locations: list of dict with location data.
        filepath: Path to the output JSON file.
    """
    if not locations:
        logger.warning("No locations to save to JSON")
        return

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(locations, f, indent=2, ensure_ascii=False)

    logger.info("Saved %d locations to JSON: %s", len(locations), filepath)


# ==============================================================================
# MAIN
# ==============================================================================


def main():
    """Main entry point for the scraper."""
    parser = argparse.ArgumentParser(
        description="Scrape Jersey Mike's US store locations"
    )
    parser.add_argument(
        "--method",
        choices=["api", "html"],
        default=config.SCRAPE_METHOD,
        help=(
            "Scraping method to use. "
            "'api' uses Jersey Mike's internal API (recommended). "
            "'html' scrapes the website HTML using CSS selectors. "
            f"Default: {config.SCRAPE_METHOD}"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=config.OUTPUT_DIR,
        help=f"Directory for output files. Default: {config.OUTPUT_DIR}",
    )

    args = parser.parse_args()

    # Update output paths if custom output directory provided
    csv_path = os.path.join(args.output_dir, config.CSV_FILENAME)
    json_path = os.path.join(args.output_dir, config.JSON_FILENAME)

    logger.info("=" * 60)
    logger.info("Jersey Mike's US Store Location Scraper")
    logger.info("=" * 60)
    logger.info("Method: %s", args.method)
    logger.info("Output directory: %s", args.output_dir)
    logger.info("Rate limit delay: %s seconds", config.REQUEST_DELAY)
    logger.info("=" * 60)

    # Run the selected scraping method
    start_time = time.time()

    if args.method == "api":
        logger.info("Using API method (recommended)...")
        locations = scrape_via_api()
    else:
        logger.info("Using HTML scraping method...")
        logger.info(
            "NOTE: If selectors don't match, update them in config.py. "
            "See README.md for instructions on finding correct selectors."
        )
        locations = scrape_via_html()

    elapsed = time.time() - start_time

    # Report results
    logger.info("=" * 60)
    logger.info("Scraping complete!")
    logger.info("Total locations found: %d", len(locations))
    logger.info("Time elapsed: %.1f seconds", elapsed)

    if not locations:
        logger.warning(
            "No locations were found. If using HTML method, the CSS selectors "
            "in config.py may need to be updated. See README.md for help."
        )
        return

    # Save output files
    save_to_csv(locations, csv_path)
    save_to_json(locations, json_path)

    logger.info("=" * 60)
    logger.info("Output files:")
    logger.info("  CSV: %s", csv_path)
    logger.info("  JSON: %s", json_path)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
