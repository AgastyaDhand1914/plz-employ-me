import os
from datetime import datetime
from config import SUPABASE_KEY, SUPABASE_URL
from supabase import create_client, Client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


#RESUME PROFILE

def get_resume_profile() -> dict | None:
    res = supabase.table("resume_profile").select("*").order("id", desc=True).limit(1).execute()
    if res.data:
        return res.data[0]
    return None


def upsert_resume_profile(skills: list, domains: list, keywords: list, raw_text: str):
    #we always insert a fresh row; get_resume_profile() fetches the latest
    supabase.table("resume_profile").insert({
        "skills": skills,
        "domains": domains,
        "keywords": keywords,
        "raw_text": raw_text,
    }).execute()


#seen ids for DEDUPLICATION

def is_seen(source: str, external_id: str) -> bool:
    res = (supabase.table("seen_ids").select("external_id").eq("source", source).eq("external_id", external_id).execute())
    return len(res.data) > 0


def mark_seen(source: str, external_id: str):
    supabase.table("seen_ids").insert({
        "source": source,
        "external_id": external_id,
    }).execute()


#LISTINGS

def get_listing_by_source_external_id(source: str, external_id: str) -> dict | None:
    """return an existing listing matching a source and external id"""
    if not source or not external_id:
        return None

    res = (supabase.table("listings")
           .select("*")
           .eq("source", source)
           .eq("external_id", external_id)
           .limit(1)
           .execute())
    if res.data:
        return res.data[0]
    return None


def insert_listing(listing: dict, relevance_score: int, relevance_reason: str) -> str:
    """
    inserts a scored listing and returns the new row's UUID
    `listing` must match the scraper interface contract
    """
    existing = get_listing_by_source_external_id(listing.get("source"), listing.get("external_id"))
    if existing:
        supabase.table("listings").update({
            "relevance_score": relevance_score,
            "relevance_reason": relevance_reason,
        }).eq("id", existing["id"]).execute()
        return existing["id"]

    row = {
        "source": listing["source"],
        "external_id": listing.get("external_id"),
        "type": listing["type"],
        "title": listing["title"],
        "company_or_organiser": listing["company_or_organiser"],
        "url": listing["url"],
        "location": listing["location"],
        "is_remote": listing["is_remote"],
        "stipend": listing.get("stipend"),
        "deadline": listing.get("deadline"),
        "description": listing.get("description"),
        "relevance_score": relevance_score,
        "relevance_reason": relevance_reason,
    }
    res = supabase.table("listings").insert(row).execute()
    return res.data[0]["id"]


def get_listings(listing_type: str | None = None, is_remote: bool | None = None,
min_score: int = 0, deadline_before: str | None = None,   #ISO date string
location: str | None = None,) -> list[dict]:
    
    query = supabase.table("listings").select("*")

    if listing_type:
        query = query.eq("type", listing_type)
    if is_remote is not None:
        query = query.eq("is_remote", is_remote)
    if min_score:
        query = query.gte("relevance_score", min_score)
    if deadline_before:
        query = query.lte("deadline", deadline_before)
    if location:
        query = query.ilike("location", f"%{location}%")

    res = query.order("relevance_score", desc=True).execute()
    return res.data


def delete_listing(listing_id: str):
    supabase.table("listings").delete().eq("id", listing_id).execute()


def get_recent_listings(limit: int = 50) -> list[dict]:
    res = (supabase.table("listings").select("*").order("first_seen_at", desc=True).limit(limit).execute())
    return res.data


#APPLICATION AND TRACKING

def create_application(listing_id: str, status: str = "interested") -> str:
    """Creates an application row. Returns its UUID."""
    res = supabase.table("applications").insert({
        "listing_id": listing_id,
        "status": status,
    }).execute()
    return res.data[0]["id"]


def update_application_status(application_id: str, status: str):
    supabase.table("applications").update({"status": status}).eq("id", application_id).execute()


def save_checklist(application_id: str, checklist: str):
    supabase.table("applications").update({"checklist": checklist}).eq("id", application_id).execute()


def get_application_for_listing(listing_id: str) -> dict | None:
    res = (supabase.table("applications").select("*").eq("listing_id", listing_id).limit(1).execute())
    if res.data:
        return res.data[0]
    return None


def get_all_applications() -> list[dict]:
    res = (supabase.table("applications").select("*, listings(*)")    #joins listing details
           .order("applied_at", desc=True).execute())
    return res.data


#PUSH AND POP OPERATIONS FOR SCORING JOB QUEUE

def enqueue_listing(listing: dict):
    """push a new filtered listing into pending_score table which functions as a job queue"""
    supabase.table("pending_score").insert({
        "listing": listing,
        "processed": False,
        "queued_at": datetime.utcnow().isoformat(),
    }).execute()


def dequeue_one() -> dict | None:
    """claim the oldest unprocessed listing from scoring queue (pending_score table)"""

    res = (supabase.table("pending_score")
           .select("*")
           .eq("processed", False)
           .order("queued_at")
           .limit(1)
           .execute())

    if not res.data:
        return None

    row = res.data[0]
    update = (supabase.table("pending_score")
              .update({"processed": True})
              .eq("id", row["id"])
              .eq("processed", False)
              .execute())

    updated_rows = None
    if hasattr(update, "data"):
        updated_rows = update.data
    elif isinstance(update, dict):
        updated_rows = update.get("data")

    if not updated_rows:
        return None

    row["processed"] = True
    return row


def requeue_pending_score(queue_id: str):
    """mark a claimed queue row as unprocessed again so it can be retried"""
    supabase.table("pending_score").update({"processed": False}).eq("id", queue_id).execute()


def delete_pending_score(queue_id: str):
    """delete a processed or unwanted row from the pending_score table (queue)"""
    supabase.table("pending_score").delete().eq("id", queue_id).execute()


def clear_pending_score():
    """delete all rows from the pending_score table"""
    supabase.table("pending_score").delete().execute()


def pending_score_unprocessed_count() -> int:
    """returns no.of listings not yet claimed for scoring"""
    res = (supabase.table("pending_score").select("id", count="exact").eq("processed", False).execute())
    return res.count or 0


def pending_score_processed_count() -> int:
    """returns no.of claimed listings waiting for final completion"""
    res = (supabase.table("pending_score").select("id", count="exact").eq("processed", True).execute())
    return res.count or 0


def pending_score_has_unprocessed() -> bool:
    """return true when any queue rows exist, claimed or unclaimed"""
    res = supabase.table("pending_score").select("id", count="exact").execute()
    return (res.count or 0) > 0


def pending_score_has_processed_rows() -> bool:
    return pending_score_processed_count() > 0


def queue_depth() -> int:
    """no. of listings waiting in job queue, including claimed rows"""
    res = supabase.table("pending_score").select("id", count="exact").execute()
    return res.count or 0