# Jersey Mike's US Store Location Scraper

A Python web scraper that extracts all Jersey Mike's store locations across the
United States. Built for the **Strat 411** school project.

**Designed to run in Google Colab** — no local setup required!

## Data Collected

For each store location, the scraper extracts:

| Field            | Description                          |
|------------------|--------------------------------------|
| `location_name`  | Name of the store location           |
| `street_address` | Street address of the store          |
| `city`           | City where the store is located      |
| `state`          | Two-letter state abbreviation        |
| `zip_code`       | ZIP code of the store                |

## Quick Start (Google Colab)

### 1. Open the Notebook in Colab

Click the link below, or upload `jersey_mikes_scraper.ipynb` to Google Colab:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/williamwilkinsonn/Strat-411/blob/main/jersey_mikes_scraper/jersey_mikes_scraper.ipynb)

### 2. Run All Cells

Click **Runtime → Run all** (or press `Ctrl+F9`) to execute the entire notebook.

### 3. Get Your Data

- The CSV and JSON files will **automatically download** to your computer
- Optionally, save to Google Drive (see Section 9 in the notebook)

Output files:
- `jersey_mikes_locations.csv` — CSV format
- `jersey_mikes_locations.json` — JSON format

## Alternative: Run Locally (Command Line)

If you prefer to run the scraper outside of Colab:

### 1. Install Dependencies

```bash
cd jersey_mikes_scraper
pip install -r requirements.txt
```

### 2. Run the Scraper

```bash
# Recommended: Use the API method (faster and more reliable)
python scraper.py

# Or explicitly choose a method:
python scraper.py --method api    # Uses Jersey Mike's internal API
python scraper.py --method html   # Scrapes the website HTML directly

# Custom output directory:
python scraper.py --output-dir /path/to/output
```

### 3. Find Your Data

Output files are saved in the `output/` directory:

- `output/jersey_mikes_locations.csv` — CSV format
- `output/jersey_mikes_locations.json` — JSON format

## Scraping Methods

### API Method (Default — Recommended)

Uses Jersey Mike's internal API endpoints, which return structured JSON data.
This method is:

- **Faster**: Fetches all stores per state in a single request
- **More reliable**: No dependency on HTML structure or CSS selectors
- **Structured**: Data comes back in clean JSON format

API endpoints used:
- `https://bapi.prd.jerseymikes.com/api/v0/stores/subdivision` — Lists all US states
- `https://bapi.prd.jerseymikes.com/api/v0/stores/bySubdivision?subdivisionCode={state}` — Lists stores in a state

### HTML Method (Fallback)

Scrapes the Jersey Mike's website HTML using BeautifulSoup and CSS selectors.
Use this method if the API endpoints change or become unavailable.

This method:
- Visits each state's location page (e.g., `/locations/CA`)
- Handles pagination automatically
- Uses configurable CSS selectors (see [Updating Selectors](#updating-css-selectors))

## Configuration

All settings are in **`config.py`**:

| Setting          | Description                              | Default         |
|------------------|------------------------------------------|-----------------|
| `SCRAPE_METHOD`  | `"api"` or `"html"`                      | `"api"`         |
| `REQUEST_DELAY`  | Seconds between requests (rate limiting) | `1.5`           |
| `MAX_RETRIES`    | Retry attempts for failed requests       | `3`             |
| `REQUEST_TIMEOUT`| Request timeout in seconds               | `30`            |
| `OUTPUT_DIR`     | Where to save output files               | `./output/`     |
| `LOG_LEVEL`      | Logging verbosity                        | `"INFO"`        |

## Updating CSS Selectors

If the HTML method stops working because the website structure changed, you'll
need to update the CSS selectors in `config.py`. Here's how:

### Step 1: Inspect the Website

1. Open [https://www.jerseymikes.com/locations/usa](https://www.jerseymikes.com/locations/usa) in Chrome or Firefox
2. Click on any state to go to its location listing page
3. Right-click on a store's **name** and select **"Inspect"** (or press `F12`)
4. The browser DevTools will open, highlighting the HTML element

### Step 2: Identify the HTML Structure

Look at the HTML around the element. Jersey Mike's typically uses
[Schema.org microdata](https://schema.org/LocalBusiness) for their location
pages. Common patterns:

```html
<!-- Example store card structure -->
<div class="location-card">
  <h3 itemprop="name">Store Name</h3>
  <p itemprop="address" itemscope itemtype="http://schema.org/PostalAddress">
    <span itemprop="streetAddress">123 Main St</span>
    <span itemprop="addressLocality">Anytown</span>,
    <span itemprop="addressRegion">CA</span>
    <span itemprop="postalCode">90210</span>
  </p>
</div>
```

### Step 3: Update `config.py`

Edit the `SELECTORS` dictionary in `config.py`:

```python
SELECTORS = {
    "state_links": "a[href*='/locations/']",
    "address_container": "[itemprop='address']",
    "store_name": "[itemprop='name']",
    "street_address": "[itemprop='streetAddress']",
    "city": "[itemprop='addressLocality']",
    "state": "[itemprop='addressRegion']",
    "zip_code": "[itemprop='postalCode']",
    "pagination": "ul.pagination a",
}
```

### Common CSS Selector Patterns

| Selector Type    | Example                          | Matches                          |
|------------------|----------------------------------|----------------------------------|
| By tag           | `h3`                             | All `<h3>` elements              |
| By class         | `.location-card`                 | Elements with class `location-card` |
| By ID            | `#store-list`                    | Element with id `store-list`     |
| By attribute     | `[itemprop='name']`              | Elements with itemprop="name"    |
| Combined         | `div.location-card h3`           | `<h3>` inside div.location-card  |
| Direct child     | `div.card > h3`                  | `<h3>` that is direct child of div.card |

## Output Format

### CSV Example

```csv
location_name,street_address,city,state,zip_code
"Downtown Location","123 Main St","Anytown","CA","90210"
"Mall Store","456 Oak Ave, Suite 100","Springfield","IL","62701"
```

### JSON Example

```json
[
  {
    "location_name": "Downtown Location",
    "street_address": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zip_code": "90210"
  },
  {
    "location_name": "Mall Store",
    "street_address": "456 Oak Ave, Suite 100",
    "city": "Springfield",
    "state": "IL",
    "zip_code": "62701"
  }
]
```

## Troubleshooting

### "No locations found"
- If using the **HTML method**, the website structure may have changed. Follow
  the [Updating CSS Selectors](#updating-css-selectors) guide above.
- If using the **API method**, the API endpoints may have changed. Check for
  updated endpoints by inspecting the website's network requests in browser
  DevTools (Network tab).

### "Connection error" or "Timeout"
- Check your internet connection
- The website may be temporarily down
- Try increasing `REQUEST_TIMEOUT` in `config.py`
- Try increasing `REQUEST_DELAY` to be more respectful to the server

### "403 Forbidden" or "429 Too Many Requests"
- Increase `REQUEST_DELAY` in `config.py` (e.g., to `3` or `5` seconds)
- The server may be blocking automated requests temporarily

## Project Structure

```
jersey_mikes_scraper/
├── jersey_mikes_scraper.ipynb  # Main notebook (open in Google Colab)
├── config.py                   # Configuration (for command-line usage)
├── scraper.py                  # Command-line scraper script
├── requirements.txt            # Python dependencies (for local usage)
├── README.md                   # This file
└── output/                     # Output directory
    ├── .gitkeep
    ├── jersey_mikes_locations.csv   # (generated)
    └── jersey_mikes_locations.json  # (generated)
```

## Dependencies

- **requests** — HTTP library for making web requests
- **beautifulsoup4** — HTML parsing library
- **lxml** — Fast XML/HTML parser (used as BeautifulSoup's parser backend)

## License

This scraper is for educational use as part of the Strat 411 course project.
