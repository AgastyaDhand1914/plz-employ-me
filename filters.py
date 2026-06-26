from db import is_seen

DELHI_NCR_KEYWORDS = [
    "delhi", "new delhi", "noida", "gurgaon", "gurugram",
    "faridabad", "ghaziabad", "greater noida", "ncr",
    "vasant kunj", "south delhi",
]

RELEVANT_KEYWORDS = [
    #tech roles
    "developer", "engineer", "software", "backend", "frontend", "full stack",
    "fullstack", "full-stack", "web",
    #data/ml
    "data", "machine learning", "ml", "ai", "deep learning", "nlp",
    "analyst", "science", "python", "agent", "agentic",
    #stack
    "react", "node", "flask", "api", "fast api", "fastapi", "express", "next",
    #research/tech adjacent
    "research", "product", "ui", "ux", "design",
    #languages
    "python", "c++", "c", "javascript", "typescript",
    #db
    "sql", "mysql", "postgres", "postgresql", "mongodb", "mongo", "prisma", "orm",
    #coursework
    "dsa", "data structures", "algorithms", "oops", "object oriented", "object-oriented",
    "computer networks", "network", "os", "operating system", "dbms", "database", "database management",
    "system"
]

def passes_keyword_filter(listing: dict) -> bool:
    """cheap pre filter before Gemini scoring
    returns true if title or description contains at least one relevant keyword"""

    haystack = (listing.get("title", "") + " " + listing.get("description", "")).lower()
    return any(kw in haystack for kw in RELEVANT_KEYWORDS)


def is_delhi_ncr(location: str) -> bool:
    """return true if the location string refers to delhi ncr region"""
    return any(kw in location.lower() for kw in DELHI_NCR_KEYWORDS)


def passes_location_filter(listing: dict) -> bool:
    """return true if the listing passes the location rules:
    -remote/wfh always pass
    -Offline in delhi ncr, pass
    -otherwise reject
    """
    if listing.get("is_remote"):
        return True
    location = listing.get("location", "")
    return is_delhi_ncr(location)


def is_duplicate(listing: dict) -> bool:
    """check seen_ids table in supabase, return true if present there"""
    return is_seen(listing["source"], listing["external_id"])


def filter_listings(listings: list[dict]) -> list[dict]:
    """apply location filter and deduplication to raw list of listings
    returns only listings that are new and pass the location filter"""
    
    passed = []
    seen_external_ids = set()
    for listing in listings:
        external_id = listing.get("external_id")
        if external_id and external_id in seen_external_ids:
            continue
        if is_duplicate(listing):
            continue
        if not passes_location_filter(listing):
            print(f"[filter] Skipped (location): {listing['title']} — {listing.get('location')}")
            continue
        if not passes_keyword_filter(listing):
            print(f"[filter] Skipped (keyword): {listing['title']}")
            continue
        if external_id:
            seen_external_ids.add(external_id)
        passed.append(listing)
    print(f"[filter] {len(passed)} listings passed out of {len(listings)} total.")
    return passed