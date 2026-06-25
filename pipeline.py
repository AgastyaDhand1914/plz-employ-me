from scrapers.internshala import scrape as scrape_internshala
from filters import filter_listings
from ai import score_listing
from db import get_resume_profile, insert_listing, mark_seen
from config import SCORE_THRESHOLD
import time


def run_pipeline() -> list[dict]:

    #full phase pipeline for testing:
    # get resume prfile
    # scrape data from forums
    # location filter + deduplication
    # score lisitng
    # tally and store relevant listings
    # return the stored listings (notifier stuff)


    print("[pipeline] Starting run.")

    # load resume profile
    profile = get_resume_profile()
    if not profile:
        print("[pipeline] ERROR: No resume profile found. Run parse_resume.py first.")
        return []

    # scrape
    raw_listings = scrape_internshala()
    # later add: scrape_unstop(), scrape_devfolio() etc

    # location filter + deduplication
    filtered = filter_listings(raw_listings)

    # score and store
    stored = []
    for listing in filtered:
        score, reason = score_listing(listing, profile)
        time.sleep(5)

        #always mark as seen so we don't wanna score it again in next run,
        #even if it didn't meet the threshold
        mark_seen(listing["source"], listing["external_id"])

        if score < SCORE_THRESHOLD:
            print(
                f"[pipeline] Below threshold (score {score}): {listing['title']}"
            )
            continue

        listing["relevance_score"] = score
        listing["relevance_reason"] = reason

        listing_id = insert_listing(listing, score, reason)
        if listing_id:
            listing["id"] = listing_id
            stored.append(listing)
            print(
                f"[pipeline] Stored (score {score}): {listing['title']} @ {listing['company_or_organiser']}"
            )

    print(f"[pipeline] Run complete. {len(stored)} new listings stored.")
    return stored



# FOR MANUAL TEST RUN ONLY
if __name__ == "__main__":
    results = run_pipeline()
    print(f"\nSummary: {len(results)} listings stored this run.")
    for r in results:
        print(f"  [{r['relevance_score']}/10] {r['title']} — {r['company_or_organiser']}")