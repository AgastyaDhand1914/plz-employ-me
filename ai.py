import os
import json
from google import genai
from dotenv import load_dotenv
import time
import re

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.1-flash-lite"


def _generate(prompt: str, retries: int = 4) -> str:
    for attempt in range(retries):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            return response.text.strip().replace("```json", "").replace("```", "").strip()
        except Exception as e:
            error_msg = str(e)
            print(error_msg)
            if attempt < retries - 1:
                #try to extract the suggested retry delay from the error
                m = re.search(r"retryDelay.*?(\d+)s", error_msg)
                wait = int(m.group(1)) + 2 if m else 2 ** (attempt + 2)
                print(f"[ai] Gemini error, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

def parse_resume(pdf_path: str) -> dict:

    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(p.extract_text() for p in pdf.pages if p.extract_text())

    prompt = f"""
Extract a structured skill profile from this resume.
Respond ONLY with valid JSON, no explanation, no code fences.
Format:
{{
  "skills": ["Python", "React", ...],
  "domains": ["machine learning", "web development", ...],
  "keywords": ["REST API", "scikit-learn", "Django", ...]
}}

Resume:
{text}
"""
    return json.loads(_generate(prompt)), text


def score_listing(listing: dict, profile: dict) -> tuple[int, str]:

    prompt = f"""
You are helping a B.Tech undergraduate student find relevant internships and hackathons.
Given their skill profile and a listing, rate relevance from 1 to 10.
Respond ONLY with valid JSON, no explanation, no code fences.
Format: {{"score": 7, "reason": "Requires Python and ML, matches candidate's scikit-learn project"}}

Candidate profile:
Skills: {profile['skills']}
Domains: {profile['domains']}
Keywords: {profile['keywords']}

Listing:
Title: {listing['title']}
Description: {listing['description']}
"""
    result = json.loads(_generate(prompt))
    return result["score"], result["reason"]


def generate_digest(new_listings: list[dict]) -> str:

    prompt = f"""
Write a short, friendly digest email body (no subject line) for a B.Tech student
summarising these new internship and hackathon opportunities.
Highlight top picks and upcoming deadlines. 2-3 short paragraphs max.

Listings:
{json.dumps(new_listings, indent=2)}
"""
    return client.models.generate_content(model=MODEL, contents=prompt).text


def generate_checklist(listing: dict, profile: dict) -> str:

    prompt = f"""
A B.Tech student is preparing to apply for this opportunity.
Based on their profile and the listing, generate a short bullet-point checklist
of what to prepare, what to highlight from their resume, and any specific requirements.
Keep it concise — 5 to 7 bullets max.

Profile: {json.dumps(profile)}
Listing: {json.dumps(listing)}
"""
    return client.models.generate_content(model=MODEL, contents=prompt).text


def nl_to_filters(query: str) -> dict:

    prompt = f"""
Convert this natural language query into filter parameters for an internship/hackathon database.
Respond ONLY with valid JSON, no explanation, no code fences.
Available fields: type (hackathon/internship), is_remote (bool), location (string),
deadline_before (YYYY-MM-DD), min_score (int), status (interested/applied/etc).

Query: "{query}"
Example output: {{"type": "internship", "is_remote": true, "min_score": 7}}
"""
    return json.loads(_generate(prompt))