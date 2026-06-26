import streamlit as st
import sys
import os
from datetime import datetime, date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import (
    get_listings,
    get_resume_profile,
    create_application,
    update_application_status,
    insert_listing,
    delete_listing,
    get_all_applications,
    queue_depth,
)

st.set_page_config(
    page_title="tracker",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

/* ── reset & base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0F0F0F;
    color: #F0EDE6;
}

.stApp {
    background-color: #0F0F0F;
}

/* ── hide default streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2.5rem 4rem; max-width: 1400px; }

/* ── monospace label class ── */
.mono { font-family: 'JetBrains Mono', monospace; }

/* ── top wordmark ── */
.wordmark {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.1rem;
    font-weight: 700;
    color: #C8FF57;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 0.1rem;
}
.tagline {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #555;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 2rem;
}

/* ── stat boxes ── */
.stat-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
}
.stat-box {
    background: #1A1A1A;
    border: 1px solid #2A2A2A;
    border-radius: 6px;
    padding: 1rem 1.4rem;
    flex: 1;
}
.stat-number {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #C8FF57;
    line-height: 1;
}
.stat-label {
    font-size: 0.7rem;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 0.3rem;
}

/* ── NL query bar ── */
.stTextInput > div > div > input {
    background-color: #1A1A1A !important;
    border: 1px solid #333 !important;
    border-radius: 6px !important;
    color: #F0EDE6 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    padding: 0.6rem 1rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #C8FF57 !important;
    box-shadow: 0 0 0 1px #C8FF57 !important;
}
.stTextInput > div > div > input::placeholder { color: #444 !important; }

/* ── filter pills (selectbox / multiselect) ── */
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background-color: #1A1A1A !important;
    border: 1px solid #2A2A2A !important;
    border-radius: 6px !important;
    color: #F0EDE6 !important;
}
.stSelectbox label, .stMultiSelect label, .stTextInput label,
.stSlider label, .stDateInput label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #555 !important;
}

/* ── slider ── */
.stSlider > div > div > div > div { background-color: #C8FF57 !important; }

/* ── buttons ── */
.stButton > button {
    background-color: transparent;
    border: 1px solid #2A2A2A;
    color: #F0EDE6;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    padding: 0.4rem 0.9rem;
    transition: all 0.15s;
}
.stButton > button:hover {
    border-color: #C8FF57;
    color: #C8FF57;
    background-color: rgba(200, 255, 87, 0.05);
}

/* ── listing card ── */
.listing-card {
    background: #151515;
    border: 1px solid #222;
    border-radius: 8px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.6rem;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    position: relative;
}
.listing-card:hover { border-color: #333; background: #1A1A1A; }
.listing-card.selected { border-color: #C8FF57; background: #171F08; }

.card-title {
    font-weight: 600;
    font-size: 0.95rem;
    margin-bottom: 0.2rem;
    color: #F0EDE6;
}
.card-company {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #888;
    margin-bottom: 0.7rem;
}
.card-meta {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    align-items: center;
}
.pill {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    padding: 0.15rem 0.5rem;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.pill-type-internship { background: #1A2840; color: #6BA3F5; }
.pill-type-hackathon  { background: #201A40; color: #A06BF5; }
.pill-remote          { background: #1A2820; color: #57C87A; }
.pill-offline         { background: #281A1A; color: #C85757; }
.pill-status          { background: #2A2A1A; color: #C8C057; }
.pill-source          { background: #1E1E1E; color: #666; border: 1px solid #2A2A2A; }

/* ── score bar ── */
.score-wrap {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin-top: 0.6rem;
}
.score-bar-bg {
    flex: 1;
    height: 4px;
    background: #222;
    border-radius: 2px;
    overflow: hidden;
}
.score-bar-fill {
    height: 100%;
    border-radius: 2px;
    background: linear-gradient(90deg, #4A8F00, #C8FF57);
    transition: width 0.4s;
}
.score-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    color: #C8FF57;
    min-width: 2.5rem;
    text-align: right;
}
.score-reason {
    font-size: 0.72rem;
    color: #555;
    margin-top: 0.35rem;
    font-style: italic;
}

/* ── detail panel (sidebar-style via expander) ── */
.detail-header {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 0.3rem;
}
.detail-company {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #888;
    margin-bottom: 1rem;
}
.detail-section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #444;
    margin-bottom: 0.3rem;
    margin-top: 1rem;
}
.detail-value {
    font-size: 0.85rem;
    color: #CCC;
    margin-bottom: 0.2rem;
}

/* ── section divider ── */
.divider {
    border: none;
    border-top: 1px solid #1E1E1E;
    margin: 1.5rem 0;
}

/* ── queue badge ── */
.queue-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    background: #1E2A0A;
    color: #C8FF57;
    border: 1px solid #3A5010;
    border-radius: 3px;
    padding: 0.2rem 0.6rem;
    display: inline-block;
}

/* ── empty state ── */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: #333;
}
.empty-state-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
.empty-state-msg { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }

/* ── tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background-color: transparent;
    border-bottom: 1px solid #222;
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #555;
    background: transparent;
    border-radius: 0;
    padding: 0.6rem 1.2rem;
}
.stTabs [aria-selected="true"] {
    color: #C8FF57 !important;
    border-bottom: 2px solid #C8FF57;
    background: transparent !important;
}

/* ── date input ── */
.stDateInput > div > div {
    background-color: #1A1A1A !important;
    border: 1px solid #2A2A2A !important;
    color: #F0EDE6 !important;
}
</style>
""", unsafe_allow_html=True)



STATUS_OPTIONS = ["interested", "applied", "shortlisted", "rejected", "accepted"]

STATUS_EMOJI = {
    "interested": "👀",
    "applied": "📤",
    "shortlisted": "⭐",
    "rejected": "✗",
    "accepted": "🎉",
    None: "",
}

def score_color(score: int) -> str:
    if score >= 8: return "#C8FF57"
    if score >= 6: return "#A0CC44"
    if score >= 4: return "#7A9E33"
    return "#505050"

def render_score_bar(score: int, reason: str = ""):
    pct = score * 10
    color = score_color(score)
    st.markdown(f"""
    <div class="score-wrap">
        <div class="score-bar-bg">
            <div class="score-bar-fill" style="width:{pct}%; background: linear-gradient(90deg, #4A8F00, {color});"></div>
        </div>
        <span class="score-num">{score}/10</span>
    </div>
    {"<div class='score-reason'>" + reason + "</div>" if reason else ""}
    """, unsafe_allow_html=True)

def render_card(listing: dict, app: dict | None, selected: bool = False) -> None:
    type_class = f"pill-type-{listing.get('type', 'internship')}"
    remote_class = "pill-remote" if listing.get("is_remote") else "pill-offline"
    remote_label = "Remote" if listing.get("is_remote") else listing.get("location", "Offline")[:20]
    deadline = listing.get("deadline") or "—"
    status_label = f"{STATUS_EMOJI.get(app.get('status') if app else None, '')} {app['status']}".strip() if app else ""
    card_class = "listing-card selected" if selected else "listing-card"

    status_html = f'<span class="pill pill-status">{status_label}</span>' if status_label else ""
    deadline_html = f'<span class="pill" style="font-family:\'JetBrains Mono\',monospace;font-size:0.62rem;color:#444;margin-left:auto;">deadline {deadline}</span>'

    html = (
        f'<div class="{card_class}">'
        f'<div class="card-title">{listing["title"]}</div>'
        f'<div class="card-company">{listing.get("company_or_organiser", "—")}</div>'
        f'<div class="card-meta">'
        f'<span class="pill {type_class}">{listing.get("type", "?")}</span>'
        f'<span class="pill {remote_class}">{remote_label}</span>'
        f'<span class="pill pill-source">{listing.get("source", "?")}</span>'
        f'{status_html}'
        f'{deadline_html}'
        '</div>'
        '</div>'
    )

    st.markdown(html, unsafe_allow_html=True)
    render_score_bar(listing.get("relevance_score", 0), listing.get("relevance_reason", ""))

def days_until(deadline_str: str | None) -> int | None:
    if not deadline_str:
        return None
    try:
        d = datetime.strptime(deadline_str[:10], "%Y-%m-%d").date()
        return (d - date.today()).days
    except Exception:
        return None


if "selected_id" not in st.session_state:
    st.session_state.selected_id = None


@st.cache_data(ttl=120)
def load_listings(listing_type, is_remote, min_score, deadline_before, location):
    return get_listings(
        listing_type=listing_type or None,
        is_remote=is_remote,
        min_score=min_score,
        deadline_before=deadline_before,
        location=location or None,
    )

@st.cache_data(ttl=60)
def load_all_applications():
    return get_all_applications()

@st.cache_data(ttl=30)
def load_queue_depth():
    return queue_depth()

@st.cache_data(ttl=300)
def load_profile():
    return get_resume_profile()

st.markdown("""
<div class="wordmark">⚡ tracker</div>
<div class="tagline">internships · hackathons · relevance-scored · ai-assisted</div>
""", unsafe_allow_html=True)


tab_listings, tab_applications, tab_profile = st.tabs(["Listings", "My Applications", "Profile"])


# LISTINGS

with tab_listings:


    fc1, fc2, fc3, fc4, fc5 = st.columns([1.5, 1.5, 1, 1, 2])
    with fc1:
        type_opts = ["all", "internship", "hackathon"]
        filter_type = st.selectbox("type", type_opts, index=0)

    with fc2:
        remote_opts = ["all", "remote only", "offline only"]
        filter_remote = st.selectbox("location", remote_opts, index=0)

    with fc3:
        filter_score = st.slider("min score", 0, 10, 0)

    with fc4:
        filter_deadline = st.date_input("deadline before", value=None)

    with fc5:
        filter_location = st.text_input("location contains", placeholder="delhi / remote / noida…",
                                        value="")

    #resolve filter values
    resolved_type = None if filter_type == "all" else filter_type
    resolved_remote = None
    if filter_remote == "remote only": resolved_remote = True
    elif filter_remote == "offline only": resolved_remote = False
    resolved_deadline = str(filter_deadline) if filter_deadline else None

    listings = load_listings(resolved_type, resolved_remote, filter_score, resolved_deadline, filter_location)

    #load app lookup dict: listing_id -> app
    all_apps_raw = load_all_applications()
    app_by_listing: dict = {}
    for a in all_apps_raw:
        lid = a.get("listing_id")
        if lid:
            app_by_listing[lid] = a


    q_depth = load_queue_depth()
    total = len(listings)
    avg_score = round(sum(l.get("relevance_score", 0) for l in listings) / total, 1) if total else 0
    urgent = sum(1 for l in listings if (days_until(l.get("deadline")) or 999) <= 7)

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-box">
            <div class="stat-number">{total}</div>
            <div class="stat-label">listings</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{avg_score}</div>
            <div class="stat-label">avg relevance</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{urgent}</div>
            <div class="stat-label">due in 7 days</div>
        </div>
        <div class="stat-box" style="display:flex;align-items:center;gap:0.7rem;">
            <div>
                <div class="stat-number">{q_depth}</div>
                <div class="stat-label">scoring queue</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Add custom opportunity", expanded=False):
        with st.form("custom_opportunity_form"):
            custom_title = st.text_input("Title")
            custom_company = st.text_input("Company / Organiser")
            custom_type = st.selectbox("Type", ["internship", "hackathon"], index=0)
            custom_remote = st.checkbox("Remote")
            custom_location = st.text_input("Location")
            custom_deadline = st.text_input("Deadline (YYYY-MM-DD)")
            custom_stipend = st.text_input("Stipend")
            custom_source = st.text_input("Source", value="manual")
            custom_description = st.text_area("Description")
            submit_custom = st.form_submit_button("Add opportunity")

        if submit_custom:
            listing_data = {
                "source": custom_source.strip() or "manual",
                "type": custom_type,
                "title": custom_title.strip() or "Untitled opportunity",
                "company_or_organiser": custom_company.strip() or "—",
                "url": "",
                "location": custom_location.strip() or "",
                "is_remote": custom_remote,
                "stipend": custom_stipend.strip() or None,
                "deadline": custom_deadline.strip() or None,
                "description": custom_description.strip() or None,
            }
            insert_listing(listing_data, 0, "manual entry")
            load_listings.clear()
            st.success("Custom opportunity added.")
            st.experimental_rerun()

    if not listings:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">◌</div>
            <div class="empty-state-msg">no listings match these filters</div>
        </div>
        """, unsafe_allow_html=True)
    else:

        list_col, detail_col = st.columns([2, 1.2], gap="large")

        with list_col:
            for listing in listings:
                lid = listing["id"]
                app = app_by_listing.get(lid)
                is_selected = st.session_state.selected_id == lid

                render_card(listing, app, selected=is_selected)

                btn_label = "✦ selected" if is_selected else "open →"
                if st.button(btn_label, key=f"open_{lid}"):
                    st.session_state.selected_id = None if is_selected else lid
                    st.rerun()

        with detail_col:
            sel_id = st.session_state.selected_id
            if sel_id:
                sel = next((l for l in listings if l["id"] == sel_id), None)
                if sel:
                    app = app_by_listing.get(sel_id)

                    st.markdown(f"""
                    <div class="detail-header">{sel['title']}</div>
                    <div class="detail-company">{sel.get('company_or_organiser', '—')}</div>
                    """, unsafe_allow_html=True)

                    render_score_bar(sel.get("relevance_score", 0), sel.get("relevance_reason", ""))

                    st.markdown("<div class='detail-section-label'>Details</div>", unsafe_allow_html=True)

                    deadline_str = sel.get("deadline") or "—"
                    days = days_until(sel.get("deadline"))
                    deadline_display = deadline_str
                    if days is not None:
                        urgency = f" ({days}d left)" if days >= 0 else f" (expired {abs(days)}d ago)"
                        deadline_display += urgency

                    st.markdown(f"""
                    <div class="detail-value">📅 {deadline_display}</div>
                    <div class="detail-value">📍 {'Remote' if sel.get('is_remote') else sel.get('location', '—')}</div>
                    <div class="detail-value">💰 {sel.get('stipend') or 'Not specified'}</div>
                    <div class="detail-value">🗂 {sel.get('source', '—')} · {sel.get('type', '—')}</div>
                    """, unsafe_allow_html=True)

                    st.markdown("<div class='detail-section-label'>Description</div>", unsafe_allow_html=True)
                    desc = sel.get("description") or "No description available."
                    with st.expander("read description", expanded=False):
                        st.markdown(f"<div style='font-size:0.82rem;color:#BBB;line-height:1.6;'>{desc[:3000]}</div>",
                                    unsafe_allow_html=True)

                    st.markdown(f"[open original listing →]({sel['url']})", unsafe_allow_html=False)
                    st.markdown("<hr class='divider'>", unsafe_allow_html=True)


                    st.markdown("<div class='detail-section-label'>Application Status</div>", unsafe_allow_html=True)

                    if st.button("delete listing", key=f"delete_{sel_id}"):
                        delete_listing(sel_id)
                        load_listings.clear()
                        load_all_applications.clear()
                        st.experimental_rerun()

                    if app:
                        current_status = app["status"]
                        new_status = st.selectbox(
                            "status",
                            STATUS_OPTIONS,
                            index=STATUS_OPTIONS.index(current_status),
                            key=f"status_{sel_id}",
                            label_visibility="collapsed",
                        )
                        if new_status != current_status:
                            update_application_status(app["id"], new_status)
                            load_all_applications.clear()
                            st.rerun()
                    else:
                        st.markdown("<div style='font-size:0.8rem;color:#555;'>not tracked yet</div>",
                                    unsafe_allow_html=True)
                        if st.button("✦ mark as interested", key=f"interest_{sel_id}"):
                            create_application(sel_id, "interested")
                            load_all_applications.clear()
                            st.rerun()
            else:
                st.markdown("""
                <div style="padding:3rem 1rem;text-align:center;">
                    <div style="font-size:1.5rem;margin-bottom:0.5rem;color:#222;">◎</div>
                    <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;
                         color:#333;text-transform:uppercase;letter-spacing:0.1em;">
                        select a listing
                    </div>
                </div>
                """, unsafe_allow_html=True)



# MY APPLICATIONS

with tab_applications:
    all_apps = load_all_applications()

    if not all_apps:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">◌</div>
            <div class="empty-state-msg">no applications tracked yet — mark a listing as interested to start</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # group by status
        for status in STATUS_OPTIONS:
            group = [a for a in all_apps if a.get("status") == status]
            if not group:
                continue

            st.markdown(f"""
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;
                 text-transform:uppercase;letter-spacing:0.1em;color:#555;
                 margin-top:1.5rem;margin-bottom:0.6rem;">
                {STATUS_EMOJI.get(status, '')} {status} ({len(group)})
            </div>
            """, unsafe_allow_html=True)

            for a in group:
                listing = a.get("listings") or {}
                title = listing.get("title", "—")
                company = listing.get("company_or_organiser", "—")
                url = listing.get("url", "#")
                deadline = listing.get("deadline") or "—"
                score = listing.get("relevance_score", 0)

                col_info, col_score, col_link = st.columns([4, 1, 1])
                with col_info:
                    st.markdown(f"""
                    <div style="font-weight:600;font-size:0.88rem;">{title}</div>
                    <div style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#666;">
                        {company} · deadline {deadline}
                    </div>
                    """, unsafe_allow_html=True)
                with col_score:
                    st.markdown(f"""
                    <div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;
                         font-weight:700;color:#C8FF57;text-align:center;padding-top:0.3rem;">
                        {score}
                    </div>
                    <div style="font-size:0.6rem;color:#444;text-align:center;">/10</div>
                    """, unsafe_allow_html=True)
                with col_link:
                    st.markdown(f"[open ↗]({url})")

                #status updater
                new_status = st.selectbox(
                    "update status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(status),
                    key=f"appstatus_{a['id']}",
                    label_visibility="collapsed",
                )
                if new_status != status:
                    update_application_status(a["id"], new_status)
                    load_all_applications.clear()
                    st.rerun()

                st.markdown("<hr class='divider'>", unsafe_allow_html=True)


# PROFILE

with tab_profile:
    profile = load_profile()

    if not profile:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">◌</div>
            <div class="empty-state-msg">no profile found — run <span style="color:#C8FF57;">python parse_resume.py</span> to extract from your resume</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        updated = profile.get("updated_at", "")[:10] if profile.get("updated_at") else "—"
        st.markdown(f"""
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;
             color:#555;margin-bottom:1.5rem;">last updated {updated}</div>
        """, unsafe_allow_html=True)

        p_col1, p_col2 = st.columns(2)

        with p_col1:
            st.markdown("<div class='detail-section-label'>Skills</div>", unsafe_allow_html=True)
            skills = profile.get("skills") or []
            skill_html = " ".join(
                f"<span class='pill pill-source' style='margin:2px;display:inline-block;'>{s}</span>"
                for s in skills
            )
            st.markdown(f"<div style='line-height:2.2;'>{skill_html}</div>", unsafe_allow_html=True)

            st.markdown("<div class='detail-section-label' style='margin-top:1.2rem;'>Domains</div>",
                        unsafe_allow_html=True)
            domains = profile.get("domains") or []
            domain_html = " ".join(
                f"<span class='pill pill-type-internship' style='margin:2px;display:inline-block;'>{d}</span>"
                for d in domains
            )
            st.markdown(f"<div style='line-height:2.2;'>{domain_html}</div>", unsafe_allow_html=True)

        with p_col2:
            st.markdown("<div class='detail-section-label'>Keywords</div>", unsafe_allow_html=True)
            keywords = profile.get("keywords") or []
            kw_html = " ".join(
                f"<span class='pill pill-type-hackathon' style='margin:2px;display:inline-block;'>{k}</span>"
                for k in keywords
            )
            st.markdown(f"<div style='line-height:2.2;'>{kw_html}</div>", unsafe_allow_html=True)

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.markdown("<div class='detail-section-label'>Raw Resume Text (preview)</div>", unsafe_allow_html=True)
        with st.expander("show raw text"):
            raw = profile.get("raw_text") or ""
            st.markdown(f"<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.72rem;"
                        f"color:#777;white-space:pre-wrap;line-height:1.6;'>{raw[:4000]}</div>",
                        unsafe_allow_html=True)