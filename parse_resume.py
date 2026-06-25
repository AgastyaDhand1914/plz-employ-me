# parse_resume.py
import sys
from ai import parse_resume
from db import upsert_resume_profile

def main():

    pdf_path = "resume/resume.pdf"
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]

    print(f"Parsing resume from: {pdf_path}")
    profile, raw_text = parse_resume(pdf_path)

    print("Extracted profile:")
    print(f"Skills:   {profile['skills']}\n\n")
    print(f"Domains:  {profile['domains']}\n\n")
    print(f"Keywords: {profile['keywords']}\n\n")

    upsert_resume_profile(skills=profile["skills"], domains=profile["domains"], keywords=profile["keywords"], raw_text=raw_text,)
    print("Profile saved to Supabase")

if __name__ == "__main__":
    main()