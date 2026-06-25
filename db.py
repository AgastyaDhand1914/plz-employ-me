import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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
    res = (
        supabase.table("seen_ids")
        .select("external_id")
        .eq("source", source)
        .eq("external_id", external_id)
        .execute()
    )
    return len(res.data) > 0


def mark_seen(source: str, external_id: str):
    supabase.table("seen_ids").insert({
        "source": source,
        "external_id": external_id,
    }).execute()


#LISTINGS

def insert_listing(listing: dict, relevance_score: int, relevance_reason: str) -> str:
    """
    inserts a scored listing and returns the new row's UUID
    `listing` must match the scraper interface contract
    """
    row = {
        "source": listing["source"],
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