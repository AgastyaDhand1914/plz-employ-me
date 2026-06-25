import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

SCRAPE_URLS = [
    # WFH/remote internships — all categories
    "https://internshala.com/internships/work-from-home-internships/",
    # Delhi NCR internships — all categories
    "https://internshala.com/internships/internships-in-delhi/",
    "https://internshala.com/internships/internships-in-noida/",
    "https://internshala.com/internships/internships-in-gurgaon/",
]


def _parse_deadline(text: str) -> str | None:
    """
    Internshala shows deadlines as 'X days left', a date string, or 'Ongoing'.
    We normalise to ISO date or None.
    """
    if not text:
        return None
    text = text.strip().lower()
    if "ongoing" in text:
        return None
    # Pattern: "5 days left"
    m = re.search(r"(\d+)\s+day", text)
    if m:
        days = int(m.group(1))
        return (datetime.today() + timedelta(days=days)).strftime("%Y-%m-%d")
    # Pattern: "15 jul" or "15 jul '25" — normalise
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    m = re.search(r"(\d{1,2})\s+([a-z]{3})", text)
    if m:
        day = int(m.group(1))
        month = months.get(m.group(2))
        if month:
            year = datetime.today().year
            # If the parsed date is in the past, it's probably next year
            candidate = datetime(year, month, day)
            if candidate < datetime.today():
                candidate = datetime(year + 1, month, day)
            return candidate.strftime("%Y-%m-%d")
    return None


def _extract_listing_id(url: str) -> str:
    """
    Extract a stable external ID from the internshala listing URL.
    URLs look like: /internship/detail/python-developer-intern-at-xyz-12345678
    The trailing numeric segment is the ID.
    """
    m = re.search(r"-(\d+)/?$", url)
    if m:
        return m.group(1)
    # Fallback: use last path segment
    return url.rstrip("/").split("/")[-1]


def _scrape_page(url: str) -> list[dict]:
    """Scrape a single Internshala listing-card page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[internshala] Failed to fetch {url}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Each internship card has class "internship_meta" nested inside
    # a container with id prefixed "internshiplist" or class "individual_internship"
    cards = soup.select(".individual_internship")
    if not cards:
        print(f"[internshala] No cards found at {url} — site structure may have changed.")
        return []

    results = []
    for card in cards:
        try:
            # Title
            title_tag = card.select_one(".job-internship-name") or card.select_one("h3")
            title = title_tag.get_text(strip=True) if title_tag else "Unknown"

            # Company
            company_tag = card.select_one(".company-name") or card.select_one(".internship_other_details_container .company")
            company = company_tag.get_text(strip=True) if company_tag else "Unknown"

            # URL — the card itself or its heading anchor
            link_tag = card.select_one("a.job-title-href") or card.select_one("h3 a") or card.find("a", href=re.compile(r"/internship/detail/"))
            if not link_tag:
                continue
            relative_url = link_tag.get("href", "")
            listing_url = "https://internshala.com" + relative_url if relative_url.startswith("/") else relative_url

            external_id = _extract_listing_id(relative_url)

            # Location / remote flag
            location_tags = card.select(".location_link") or card.select(".locations_strip a")
            location_texts = [t.get_text(strip=True) for t in location_tags]
            raw_location = ", ".join(location_texts) if location_texts else ""

            # Check WFH
            wfh_badge = card.select_one(".work_from_home") or card.find(string=re.compile(r"work from home", re.I))
            is_remote = bool(wfh_badge) or "work from home" in raw_location.lower() or "wfh" in raw_location.lower()

            # Stipend
            stipend_tag = card.select_one(".stipend") or card.select_one(".stipend_container .stipend")
            stipend = stipend_tag.get_text(strip=True) if stipend_tag else "Unpaid"

            # Deadline
            deadline_tag = card.select_one(".apply-by-text") or card.select_one(".application_deadline") or card.select_one("span.status-success")
            deadline = _parse_deadline(deadline_tag.get_text(strip=True) if deadline_tag else "")

            # Description — short summary visible on card; we'll note to fetch full detail separately
            # For the AI scorer, the card-level info (title + company + location + stipend) is enough
            # for a reasonable score. A fuller description improves accuracy.
            desc_tag = card.select_one(".internship_other_details_container") or card.select_one(".detail-row")
            description = desc_tag.get_text(separator=" ", strip=True) if desc_tag else f"{title} at {company}. Location: {raw_location}. Stipend: {stipend}."

            results.append({
                "source": "internshala",
                "external_id": external_id,
                "type": "internship",
                "title": title,
                "company_or_organiser": company,
                "url": listing_url,
                "location": raw_location if raw_location else "Delhi",
                "is_remote": is_remote,
                "stipend": stipend,
                "deadline": deadline,
                "description": description,
            })

        except Exception as e:
            print(f"[internshala] Error parsing card: {e}")
            continue

    return results


def scrape() -> list[dict]:
    """
    Scrape all configured Internshala URLs and return deduplicated listings
    conforming to the scraper interface contract.
    """
    all_results = []
    seen_urls = set()

    for url in SCRAPE_URLS:
        print(f"[internshala] Scraping {url}")
        page_results = _scrape_page(url)
        for listing in page_results:
            if listing["url"] not in seen_urls:
                seen_urls.add(listing["url"])
                all_results.append(listing)

    print(f"[internshala] Found {len(all_results)} unique listings.")
    return all_results