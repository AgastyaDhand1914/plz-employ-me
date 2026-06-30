import requests
import re
import html
from datetime import datetime

from . import print_scraper_header, print_scraper_section, print_scraper_footer

BASE_URL = "https://unstop.com/api/public/opportunity/search-new"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://unstop.com/internships",
}

PAGE_SIZE_PER_PAGE = 10  # Unstop's default page size for this endpoint, observed from real response
MAX_PAGES = 8            # safety cap per query

# Base params common to all queries — opportunity=internships restricts to internships,
# filters=,All,Open,All keeps only currently-open listings.
BASE_PARAMS = {
    "opportunity": "internships",
    "filters": ",All,Open,All",
    "types": "teamsize,payment,oppstatus,eligible",
    "atype": "explore",
    "showOlderResultForSearch": "true",
}

# We run separate queries for different search terms since the API doesn't
# expose a clean "remote OR delhi" filter — we search broadly and rely on
# our own location/remote detection during parsing instead of query params.
# A single broad query (no search term) returns the full open internship feed,
# which we then filter ourselves using filters.py logic upstream.
QUERIES = [
    ("all open internships", {}),
]


def _strip_html(raw_html: str) -> str:
    """Strip HTML tags from the 'details' field and unescape entities."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_deadline(raw: str | None) -> str | None:
    """
    Unstop 'end_date' comes as full ISO timestamp, e.g. '2026-07-14T00:00:00+05:30'.
    Normalise to YYYY-MM-DD.
    """
    if not raw:
        return None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw.strip())
    return m.group(1) if m else None


def _is_remote(listing_data: dict) -> bool:
    """
    jobDetail.type appears to encode work mode — observed value 'wfh' for remote.
    Other likely values based on Unstop's UI: 'office' / 'hybrid'.
    Treat anything not explicitly office-based, with no city locations, as remote.
    """
    job_detail = listing_data.get("jobDetail") or {}
    work_type = (job_detail.get("type") or "").lower()

    if work_type in ("wfh", "remote", "work_from_home"):
        return True
    if work_type in ("office", "onsite", "in_office"):
        return False

    # Fallback: if no locations are specified at all, treat as remote
    locations = listing_data.get("locations") or job_detail.get("locations") or []
    return len(locations) == 0


def _extract_location(listing_data: dict) -> str:
    """
    Pull location string from 'locations' array (top-level or under jobDetail).
    Each location entry is expected to be a dict with a city/name field, but
    we handle plain strings defensively too.
    """
    locations = listing_data.get("locations") or (listing_data.get("jobDetail") or {}).get("locations") or []

    if not locations:
        # Some listings carry an address block instead
        addr = listing_data.get("address_with_country_logo") or {}
        city = addr.get("city") or ""
        state = addr.get("state") or ""
        combined = ", ".join(p for p in [city, state] if p)
        return combined

    parts = []
    for loc in locations:
        if isinstance(loc, dict):
            name = loc.get("city") or loc.get("name") or loc.get("location") or ""
            if name:
                parts.append(name)
        elif isinstance(loc, str):
            parts.append(loc)

    return ", ".join(parts)


def _extract_stipend(listing_data: dict) -> str:
    job_detail = listing_data.get("jobDetail") or {}
    paid_unpaid = (job_detail.get("paid_unpaid") or "").lower()

    if paid_unpaid == "unpaid":
        return "Unpaid"

    min_sal = job_detail.get("min_salary")
    max_sal = job_detail.get("max_salary")
    pay_in = job_detail.get("pay_in") or "monthly"
    pay_unit = "month" if pay_in == "monthly" else pay_in

    if min_sal is not None and max_sal is not None:
        return f"{min_sal}-{max_sal}/{pay_unit}"
    if min_sal is not None:
        return f"{min_sal}+/{pay_unit}"
    if max_sal is not None:
        return f"up to {max_sal}/{pay_unit}"

    if paid_unpaid == "paid":
        return "Paid (amount not disclosed)"

    return "Unpaid"


def _build_description(listing_data: dict) -> str:
    """
    Use the HTML 'details' field as the primary description, stripped to plain text.
    Append required skills if present, since they're useful signal for the AI scorer.
    """
    details = _strip_html(listing_data.get("details", ""))

    skills = listing_data.get("required_skills") or []
    skill_names = [s.get("skill_name") or s.get("skill", "") for s in skills if isinstance(s, dict)]
    skill_names = [s for s in skill_names if s]

    if skill_names:
        details += f" Skills: {', '.join(skill_names)}."

    if not details.strip():
        title = listing_data.get("title", "")
        org = (listing_data.get("organisation") or {}).get("name", "")
        details = f"{title} at {org}."

    return details.strip()


def _build_listing_url(listing_data: dict) -> str:
    """seo_url is the ready-made canonical URL. Fall back to public_url if missing."""
    seo_url = listing_data.get("seo_url") or ""
    if seo_url.startswith("http"):
        return seo_url

    public_url = listing_data.get("public_url") or ""
    if public_url:
        return f"https://unstop.com/{public_url.lstrip('/')}"

    return ""


def _parse_listing(listing_data: dict) -> dict | None:
    """
    Convert a raw Unstop API listing object into the scraper interface contract dict.
    Returns None for non-internship listings or listings missing critical fields.
    """
    # Only keep actual internships — type is 'jobs', subtype is 'internships'
    if listing_data.get("subtype") != "internships":
        return None

    listing_id = str(listing_data.get("id") or "")
    if not listing_id:
        return None

    url = _build_listing_url(listing_data)
    if not url:
        return None

    title = listing_data.get("title") or "Unknown"
    company = (listing_data.get("organisation") or {}).get("name") or "Unknown"

    location = _extract_location(listing_data)
    remote = _is_remote(listing_data)
    stipend = _extract_stipend(listing_data)
    deadline = _parse_deadline(listing_data.get("end_date"))
    description = _build_description(listing_data)

    return {
        "source": "unstop",
        "external_id": listing_id,
        "type": "internship",
        "title": title,
        "company_or_organiser": company,
        "url": url,
        "location": location if location else "India",
        "is_remote": remote,
        "stipend": stipend,
        "deadline": deadline,
        "description": description,
    }


def _fetch_page(extra_params: dict, page: int) -> dict:
    """
    Fetch a single page from the Unstop search-new API.
    Returns the raw 'data' object from the response, which includes
    current_page, data (listings), last_page, per_page, and total.
    Returns an empty dict on failure.
    """
    params = {**BASE_PARAMS, **extra_params, "page": page}

    try:
        resp = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[unstop] Request failed (page {page}): {e}")
        return {}

    try:
        payload = resp.json()
    except ValueError as e:
        print(f"[unstop] JSON decode failed (page {page}): {e}")
        return {}

    return payload.get("data") or {}


def _run_query(label: str, extra_params: dict, max_pages: int = MAX_PAGES) -> list[dict]:
    """
    Paginate through a single Unstop query and return parsed internship listings.
    Uses 'last_page' from the API response as the real stop signal, capped by
    max_pages so we don't crawl all the way through Unstop's (inflated) page count.
    Listings are assumed newest-first, so a low page cap is enough for daily runs.
    """
    results = []
    print_scraper_section("unstop", f"Query: {label}")

    last_page = None
    for page in range(1, max_pages + 1):
        page_data = _fetch_page(extra_params, page)

        raw_listings = page_data.get("data") or []
        if not raw_listings:
            print(f"[unstop] No data on page {page}, stopping.")
            break

        if last_page is None:
            last_page = page_data.get("last_page")
            per_page = page_data.get("per_page")
            total = page_data.get("total")
            print(f"[unstop] API reports last_page={last_page}, per_page={per_page}, total={total}")

        page_internships = 0
        for raw in raw_listings:
            parsed = _parse_listing(raw)
            if parsed:
                results.append(parsed)
                page_internships += 1

        print(f"[unstop] {label} — page {page}, {len(raw_listings)} items, "
              f"{page_internships} internships kept")

        if last_page is not None and page >= last_page:
            print(f"[unstop] Reached last_page={last_page}, stopping.")
            break

    return results


def scrape() -> list[dict]:
    """
    Run all configured queries against the Unstop internship API.
    Returns deduplicated listings conforming to the scraper interface contract.
    """
    print_scraper_header("unstop", "Starting Unstop scraper")
    all_results = []
    seen_ids = set()

    for label, extra_params in QUERIES:
        print_scraper_section("unstop", f"Query: {label}")
        page_results = _run_query(label, extra_params)
        for listing in page_results:
            ext_id = listing["external_id"]
            if ext_id not in seen_ids:
                seen_ids.add(ext_id)
                all_results.append(listing)

    print_scraper_footer("unstop", f"Found {len(all_results)} unique listings.")
    return all_results