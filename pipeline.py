from scrapers.internshala import scrape as scrape_internshala
from filters import filter_listings
from ai import score_listing, generate_digest
from db import (get_resume_profile, insert_listing, mark_seen, enqueue_listing, dequeue_one,
    delete_pending_score, requeue_pending_score, pending_score_has_unprocessed, queue_depth, 
    get_recent_listings, reset_stuck_rows, get_pipeline_state, set_pipeline_state,)
from notifier import send_digest_email
from config import SCORE_THRESHOLD
from datetime import datetime, timedelta

EMPTY_SCRAPE_DELAY = timedelta(hours=1)


def _get_last_empty_scrape() -> datetime | None:
    val = get_pipeline_state("last_empty_scrape")
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except Exception:
        return None


def _set_last_empty_scrape(dt: datetime):
    set_pipeline_state("last_empty_scrape", dt.isoformat())


def _clear_empty_scrape_state():
    set_pipeline_state("last_empty_scrape", "")


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

    _clear_empty_scrape_state()
    print(f"[scrape] done, {queued} listings queued for scoring :|")


def score_batch_from_queue(batch_size: int = 10):
    """
    phase 2: scores listings up to batch_size listings from the queue,
    resets any stuck rows first, then dequeues and scores one by one
    """
    reset_stuck_rows(older_than_minutes=15)

    profile = get_resume_profile()
    if not profile:
        print("[scorer] no resume profile found, what are you doing gng?")
        return

    scored = 0
    for _ in range(batch_size):
        row = dequeue_one()
        if row is None:
            break    # queue empty

        listing = row["listing"]
        print(f"[scorer] scoring: {listing['title']} @ {listing.get('company_or_organiser', '?')}")

        try:
            score, reason = score_listing(listing, profile)
        except Exception as e:
            print(f"[scorer] gemini error, requeueing: {e}")
            requeue_pending_score(row["id"])
            break    #if error, wait for next run instead of hammering API again

        if score < SCORE_THRESHOLD:
            print(f"[scorer] below threshold ({score}): {listing['title']}")
            delete_pending_score(row["id"])
            continue

        listing["relevance_score"] = score
        listing["relevance_reason"] = reason
        try:
            insert_listing(listing, score, reason)
        except Exception as e:
            print(f"[scorer] failed to persist, requeueing: {e}")
            requeue_pending_score(row["id"])
            continue

        delete_pending_score(row["id"])
        print(f"[scorer] stored ({score}/10): {listing['title']}")
        scored += 1

    print(f"[scorer] batch done, scored {scored} listings")


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