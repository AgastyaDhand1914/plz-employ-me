from scrapers.internshala import scrape as scrape_internshala
from filters import filter_listings
from ai import score_listing, generate_digest
from db import (get_resume_profile, insert_listing, mark_seen, 
enqueue_listing, dequeue_one, delete_pending_score, queue_depth, get_recent_listings)
from notifier import send_digest_email
from config import SCORE_THRESHOLD
from datetime import datetime


def run_scrape_and_enqueue():
    """
    phase 1: runs once or twice a day

    scrapes all sources, applies location + keyword + dedup filters,
    pushes passing listings into pending_score queue
    """
    print("[scrape] starting scrape run >:)")

    raw_listings = scrape_internshala()
    #later: unstop, devfolio etc

    filtered = filter_listings(raw_listings)

    queued = 0
    for listing in filtered:
        #mark seen immediately so next scrape run doesn't re-enqueue (is that even a word)
        mark_seen(listing["source"], listing["external_id"])
        enqueue_listing(listing)
        queued += 1

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
        #un-mark processed so it enters the queue again next tick
        from db import supabase
        supabase.table("pending_score").update({"processed": False}).eq("id", row["id"]).execute()
        return

    if score < SCORE_THRESHOLD:
        print(f"[scorer] below threshold ({score}): {listing['title']}")
        delete_pending_score(row["id"])
        return

    listing["relevance_score"] = score
    listing["relevance_reason"] = reason
    insert_listing(listing, score, reason)
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