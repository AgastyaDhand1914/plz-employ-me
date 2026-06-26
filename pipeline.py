from scrapers.internshala import scrape as scrape_internshala
from filters import filter_listings
from ai import score_listing, generate_digest
from db import (get_resume_profile, insert_listing, mark_seen, enqueue_listing, dequeue_one,
    delete_pending_score, requeue_pending_score, pending_score_has_unprocessed,
    queue_depth, get_recent_listings,)
from notifier import send_digest_email
from config import SCORE_THRESHOLD
from datetime import datetime, timedelta
import json
import os


STATE_FILE = os.path.join(os.path.dirname(__file__), "pending_score_state.json")
EMPTY_SCRAPE_DELAY = timedelta(hours=24)


def _load_pending_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_pending_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def _get_last_empty_scrape() -> datetime | None:
    state = _load_pending_state()
    ts = state.get("last_empty_scrape")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _set_last_empty_scrape(dt: datetime):
    state = _load_pending_state()
    state["last_empty_scrape"] = dt.isoformat()
    _save_pending_state(state)


def _should_scrape_now() -> bool:
    last_empty = _get_last_empty_scrape()
    if last_empty is None:
        return True
    return datetime.utcnow() - last_empty >= EMPTY_SCRAPE_DELAY


def run_scrape_and_enqueue():
    """
    phase 1: runs repeatedly while pending_score has no pending rows

    scrapes all sources, applies location + keyword + dedup filters,
    pushes passing listings into pending_score queue
    """

    #check if any listings are pending to be scored and skip
    if pending_score_has_unprocessed():
        print("[scrape] pending_score still has pending rows, skipping scrape")
        return

    if not _should_scrape_now():
        print("[scrape] empty scrape cooldown active, skipping scrape")
        return

    print("[scrape] starting scrape run >:)")

    raw_listings = scrape_internshala()
    #later: unstop, devfolio etc

    filtered = filter_listings(raw_listings)

    if not filtered:
        print("[scrape] no listings found, waiting 24 hours before next scrape")
        _set_last_empty_scrape(datetime.utcnow())
        return

    queued = 0
    for listing in filtered:
        enqueue_listing(listing)
        queued += 1
        try:
            mark_seen(listing["source"], listing["external_id"])
        except Exception as e:
            print(f"[scrape] warning: could not mark seen for {listing.get('external_id')} : {e}")

    print(f"[scrape] done, {queued} listings queued for scoring :|")


def score_one_from_queue():
    """
    phase 2: runs every few minutes via APScheduler

    picks exactly one listing from the queue, scores it with gemini,
    stores it if above threshold. one api call per invocation
    """
    profile = get_resume_profile()
    if not profile:
        print("[scorer] no resume profile found, what are you doing gng?")
        return

    row = dequeue_one()
    if row is None:
        return    #queue empty, nothing to do (silent return)

    listing = row["listing"]
    print(f"[scorer] scoring: {listing['title']} @ {listing.get('company_or_organiser', '?')}")

    try:
        score, reason = score_listing(listing, profile)
    except Exception as e:
        print(f"[scorer] gemini error, will retry next tick: {e}")
        requeue_pending_score(row["id"])
        return

    if score < SCORE_THRESHOLD:
        print(f"[scorer] below threshold ({score}): {listing['title']}")
        delete_pending_score(row["id"])
        return

    listing["relevance_score"] = score
    listing["relevance_reason"] = reason
    try:
        insert_listing(listing, score, reason)
    except Exception as e:
        print(f"[scorer] failed to persist listing, will retry next tick: {e}")
        requeue_pending_score(row["id"])
        return

    delete_pending_score(row["id"])
    print(f"[scorer] stored ({score}/10): {listing['title']}")


def run_morning_digest():
    """
    phase 3: runs {chosen amt} a day at {chosen time}

    pulls recent high score listings, generates a digest and emails it via SMTP
    """
    profile = get_resume_profile()
    if not profile:
        print("[digest] no profile found, what are you doing gng?")
        return

    depth = queue_depth()
    listings = get_recent_listings(limit=30)

    if not listings:
        print("[digest] no listings to digest, we might be cooked")
        return

    body = generate_digest(listings)

    if depth > 0:
        body += f"\n\n---\n[{depth} more listings are still being scored. Updates will keep showing in the dashbaord :)]"

    today = datetime.now().strftime("%d %b %Y")
    send_digest_email(
        subject=f"you might be employable after all. lock innnnn ({today})",
        body=body,
    )
    print(f"[digest] sent digest covering {len(listings)} listings")