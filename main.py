from apscheduler.schedulers.blocking import BlockingScheduler
from pipeline import run_scrape_and_enqueue, score_one_from_queue, run_morning_digest

scheduler = BlockingScheduler(timezone="Asia/Kolkata")

scheduler.add_job(run_scrape_and_enqueue, "interval", seconds=60, id="scraper")
scheduler.add_job(score_one_from_queue, "interval", seconds=90, id="scorer")
scheduler.add_job(run_morning_digest, "cron", hour=8, minute=0, id="digest")

if __name__ ==  "__main__":
    print("[main] scheduler starting: timezone Asia/Kolkata")
    print("  scraper:  every 60 seconds, only when pending_score is empty")
    print("  scorer:   every 90 seconds")
    print("  digest:   08:00 daily")

    #immediate scraping on deployment, cron schedule takes over after this
    run_scrape_and_enqueue()

    scheduler.start()