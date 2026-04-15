"""
Configuration for the Jersey Mike's US Store Location Scraper.

This file contains all configurable settings for the scraper, including:
- Target URLs and API endpoints
- CSS selectors for HTML parsing
- Rate limiting and request settings
- Output file paths

HOW TO UPDATE CSS SELECTORS:
1. Open https://www.jerseymikes.com/locations/usa in your browser
2. Right-click on the element you want to scrape and select "Inspect"
3. In the Elements panel, identify the HTML tag and its attributes
4. Update the corresponding selector in this file

Example: If a store name is inside <h3 class="store-title">Store Name</h3>,
the CSS selector would be "h3.store-title".
"""

import os

# ==============================================================================
# BASE URLS
# ==============================================================================

# The main USA locations page that lists links to each state
BASE_URL = "https://www.jerseymikes.com"
USA_LOCATIONS_URL = f"{BASE_URL}/locations/usa"

# Jersey Mike's internal API endpoint (more reliable than HTML scraping)
# This API returns structured JSON data for all store locations
API_BASE_URL = "https://bapi.prd.jerseymikes.com/api/v0"
API_SUBDIVISIONS_URL = f"{API_BASE_URL}/stores/subdivision"
API_STORES_BY_STATE_URL = f"{API_BASE_URL}/stores/bySubdivision"

# ==============================================================================
# CSS SELECTORS (for HTML scraping fallback)
# ==============================================================================
# These selectors target the Jersey Mike's website HTML structure.
# If the website changes, update these selectors accordingly.
#
# HOW TO FIND SELECTORS:
# 1. Open the page in Chrome/Firefox
# 2. Right-click on the element -> "Inspect"
# 3. Look at the HTML tag, class names, and attributes
# 4. Build a CSS selector or use itemprop attributes (Schema.org microdata)

SELECTORS = {
    # On the /locations/usa page, each state is listed as a link.
    # Inspect a state link (e.g., "Alabama") and find its parent container.
    # The links typically follow the pattern /locations/{state_abbreviation}
    "state_links": "a[href*='/locations/']",

    # On each state page (e.g., /locations/AL), store locations are listed
    # in cards/containers. Each location card contains address info.
    # Look for elements with Schema.org microdata (itemprop attributes).

    # The address container wrapping each store's address info
    # Inspect any store address block and find the parent <p> or <div>
    "address_container": "[itemprop='address']",

    # Individual address fields within the address container
    # These use Schema.org itemprop attributes, which are standard
    "store_name": "[itemprop='name']",
    "street_address": "[itemprop='streetAddress']",
    "city": "[itemprop='addressLocality']",
    "state": "[itemprop='addressRegion']",
    "zip_code": "[itemprop='postalCode']",

    # Pagination controls on state pages (for navigating multiple pages)
    # Inspect the page number links at the bottom of the page
    "pagination": "ul.pagination a",
}

# ==============================================================================
# REQUEST SETTINGS
# ==============================================================================

# User-Agent header to identify the scraper
# Using a descriptive user agent so the server knows this is an automated request
USER_AGENT = (
    "JerseyMikesLocationScraper/1.0 "
    "(Strat 411 School Project; educational use only)"
)

# Additional request headers
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Headers specifically for API requests (JSON)
API_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}

# ==============================================================================
# RATE LIMITING
# ==============================================================================

# Delay (in seconds) between consecutive HTTP requests
# This is to be respectful to the server and avoid being blocked
REQUEST_DELAY = 1.5

# Maximum number of retry attempts for failed requests
MAX_RETRIES = 3

# Delay (in seconds) between retry attempts (increases with each retry)
RETRY_DELAY = 5

# Request timeout in seconds
REQUEST_TIMEOUT = 30

# ==============================================================================
# SCRAPING METHOD
# ==============================================================================

# Choose the scraping method:
#   "api"  - Use Jersey Mike's internal API (recommended, faster and more reliable)
#   "html" - Scrape the HTML pages directly (uses CSS selectors above)
SCRAPE_METHOD = "api"

# API pagination settings
API_PAGE_SIZE = 1000  # Number of stores to fetch per state (max per request)

# ==============================================================================
# OUTPUT SETTINGS
# ==============================================================================

# Directory where output files will be saved
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# Output file names
CSV_FILENAME = "jersey_mikes_locations.csv"
JSON_FILENAME = "jersey_mikes_locations.json"

# Full output paths
CSV_OUTPUT_PATH = os.path.join(OUTPUT_DIR, CSV_FILENAME)
JSON_OUTPUT_PATH = os.path.join(OUTPUT_DIR, JSON_FILENAME)

# ==============================================================================
# LOGGING
# ==============================================================================

# Log level: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
LOG_LEVEL = "INFO"

# Log file path (set to None to log only to console)
LOG_FILE = None

# ==============================================================================
# US STATES (used for HTML scraping fallback)
# ==============================================================================

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI",
    "WY",
]
