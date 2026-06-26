from apscheduler.schedulers.blocking import BlockingScheduler
from pipeline import run_scrape_and_enqueue, score_one_from_queue, run_morning_digest

scheduler = BlockingScheduler(timezone="Asia/Kolkata")

schdeuler.add_job(run_scrape_and_enqueue, "cron", hour="6,18", minute=0, id="scraper")
schdeuler.add_job(score_one_from_queue, "interval", seconds=90, id="scorer")
schdeuler.add_job(run_morning_digest, "cron", hour=8, minute=0, id="digest")

if __name__ ==  "__main__":
    print("[main] scheduler starting: timezone Asia/Kolkata")
    print("  scraper:  06:00 and 18:00 daily")
    print("  scorer:   every 90 seconds")
    print("  digest:   08:00 daily")
    scheduler.start()