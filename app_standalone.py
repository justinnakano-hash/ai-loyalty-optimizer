import streamlit as st
import anthropic
import json
import re

st.set_page_config(
    page_title="AI Loyalty Optimizer",
    page_icon="✈️",
    layout="centered",
)

# ── CSS ──
st.markdown("""
<style>
.block-container { max-width:860px !important; padding-top:1.5rem !important; }

/* Profile rows */
.prog-row { display:flex; align-items:center; gap:12px; padding:10px 2px;
    border-bottom:1px solid #f0f0f0; }
.prog-row:last-child { border-bottom:none; }
.prog-dot { width:9px; height:9px; border-radius:50%; flex-shrink:0; }
.prog-name { font-size:13px; font-weight:600; color:#111; flex:2; min-width:0; }
.prog-bal  { font-size:13px; color:#333; flex:1; white-space:nowrap; }
.prog-pill { display:inline-block; padding:2px 10px; border-radius:20px;
    font-size:11px; font-weight:500; flex:1; white-space:nowrap; }
.prog-pill.std { background:#f0f0f0; color:#666; }
.prog-pill.act { background:#e6f4ea; color:#1e5c2a; }
.prog-actions { display:flex; gap:6px; flex-shrink:0; }

/* Icon buttons — rendered as <a> tags to avoid st.button wrapping issues */
.icon-btn {
    display:inline-flex; align-items:center; justify-content:center;
    width:30px; height:30px; border-radius:6px;
    border:1px solid #e0e0e0; background:#fff;
    text-decoration:none; cursor:pointer; flex-shrink:0;
}
.icon-btn:hover { background:#f5f5f5; border-color:#bbb; }
.icon-btn.del:hover { background:#fff0f0; border-color:#fca5a5; }
.icon-btn svg { display:block; }

/* Col headers */
.col-hdr { font-size:11px; font-weight:600; color:#999;
    text-transform:uppercase; letter-spacing:.05em; padding:0 2px 6px; }

/* Results */
.plain-english { background:#e6f4ea; border-radius:10px; padding:.9rem 1.1rem;
    font-size:14px; color:#1e5c2a; line-height:1.65; margin-bottom:1rem; }
.hero { border:1px solid #e8e8e8; border-radius:12px; overflow:hidden; margin-bottom:1rem; }
.hero-top { padding:1rem 1.25rem; }
.route { font-size:18px; font-weight:600; color:#111;
    display:flex; align-items:center; gap:10px; margin-bottom:4px; }
.route-line { flex:1; height:1px; background:#ddd; }
.tagline { font-size:13px; color:#666; }
.hero-bottom { display:grid; grid-template-columns:1fr 1fr 1fr; border-top:1px solid #e8e8e8; }
.hero-stat { padding:.85rem 1.1rem; border-right:1px solid #e8e8e8; }
.hero-stat:last-child { border-right:none; }
.hs-label { font-size:11px; color:#999; text-transform:uppercase; letter-spacing:.05em; margin-bottom:3px; }
.hs-val   { font-size:17px; font-weight:600; color:#111; }
.hs-sub   { font-size:12px; color:#888; margin-top:2px; }
.pts-wrap { background:#fff; border:1px solid #e8e8e8; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem; }
.pts-title { font-size:11px; font-weight:600; color:#999; text-transform:uppercase;
    letter-spacing:.05em; margin-bottom:10px; }
.pts-row  { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
.pts-name { font-size:13px; color:#111; min-width:130px; }
.pts-track{ flex:1; height:8px; background:#f0f0f0; border-radius:4px; overflow:hidden; }
.pts-fill { height:100%; border-radius:4px; }
.pts-amt  { font-size:12px; color:#888; min-width:90px; text-align:right; }
.legend   { display:flex; gap:16px; margin-top:10px; }
.legend-item { font-size:11px; color:#999; display:flex; align-items:center; gap:5px; }
.legend-dot  { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.res-card { background:#fff; border:1px solid #e8e8e8; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem; }
.card-head { font-size:11px; font-weight:600; color:#999; text-transform:uppercase;
    letter-spacing:.05em; margin-bottom:10px; }
.dr { display:flex; justify-content:space-between; padding:6px 0;
    border-bottom:1px solid #f0f0f0; font-size:13px; }
.dr:last-child { border-bottom:none; }
.dr-l { color:#666; }
.dr-v { font-weight:500; color:#111; text-align:right; }
.perks-row { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:1rem; }
.chip { background:#f5f5f5; border:1px solid #e8e8e8; border-radius:20px;
    padding:5px 12px; font-size:12px; color:#555; }
.steps-card { background:#fff; border:1px solid #e8e8e8; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem; }
.step { display:flex; gap:12px; padding:10px 0;
    border-bottom:1px solid #f5f5f5; align-items:flex-start; }
.step:last-child { border-bottom:none; }
.step-num { width:26px; height:26px; min-width:26px; border-radius:50%;
    background:#e8f0fe; display:flex; align-items:center; justify-content:center;
    font-size:12px; font-weight:600; color:#1a56cc; }
.step-title { font-size:13px; font-weight:600; color:#111; margin-bottom:3px; }
.step-desc  { font-size:12px; color:#666; line-height:1.55; }
.alt-chip { background:#f7f7f7; border:1px solid #e8e8e8; border-radius:10px;
    padding:.75rem 1rem; margin-bottom:8px; }
.alt-name  { font-size:13px; font-weight:600; color:#111; margin-bottom:3px; }
.alt-desc  { font-size:12px; color:#555; margin-bottom:3px; }
.alt-trade { font-size:12px; color:#aaa; }
.cc-wrap { background:#f0f7ff; border:2px solid #a8d0f5; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem; }
.cc-eye  { font-size:11px; color:#1a56cc; font-weight:600; text-transform:uppercase;
    letter-spacing:.05em; margin-bottom:6px; }
.cc-name { font-size:15px; font-weight:600; color:#111; margin-bottom:4px; }
.cc-bonus{ font-size:13px; color:#2d7a3a; margin-bottom:6px; }
.cc-why  { font-size:13px; color:#555; }
.mock-banner { background:#fff3e0; border:1px solid #ffcc80; border-radius:8px;
    padding:.6rem 1rem; font-size:13px; color:#e65100; margin-bottom:1rem; }
</style>
""", unsafe_allow_html=True)

# ── SVG icons (inline, hardcoded colors so they always render) ──
SVG_EDIT = """<svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="11.8" width="12" height="1.1" rx=".55" fill="#555"/>
  <path d="M3.5 10.5l6-6 2.2 2.2-6 6H3.5v-2.2z" stroke="#555" stroke-width="1.2"
    stroke-linecap="round" stroke-linejoin="round" fill="#dde8ff"/>
  <path d="M9.5 4.5l2.2 2.2" stroke="#555" stroke-width="1.2" stroke-linecap="round"/>
  <path d="M11.2 2.8a1.1 1.1 0 011.6 1.6l-.9.9-1.6-1.6.9-.9z" fill="#555"/>
</svg>"""

SVG_REMOVE = """<svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M2.5 4.5h11" stroke="#888" stroke-width="1.3" stroke-linecap="round"/>
  <path d="M5.5 4.5V3.2a.8.8 0 01.8-.7h3.4a.8.8 0 01.8.7V4.5"
    stroke="#888" stroke-width="1.2" stroke-linecap="round"/>
  <path d="M4.2 4.5l.8 8h6l.8-8" stroke="#888" stroke-width="1.2"
    stroke-linecap="round" stroke-linejoin="round" fill="#f0f0f0"/>
  <path d="M6.5 7v4M9.5 7v4" stroke="#aaa" stroke-width="1.1" stroke-linecap="round"/>
</svg>"""

# ── Program catalogue ──
PROGRAMS = {
    "Credit Cards": {
        "Chase Ultimate Rewards":  {"color": "#1a56cc", "statuses": ["Standard"]},
        "Amex Membership Rewards": {"color": "#007bc1", "statuses": ["Standard", "Gold Card", "Platinum Card", "Centurion"]},
        "Capital One Miles":       {"color": "#c8102e", "statuses": ["Standard", "Venture", "Venture X"]},
        "Citi ThankYou Points":    {"color": "#003b70", "statuses": ["Standard", "Preferred", "Premier", "Prestige"]},
        "Bilt Rewards":            {"color": "#222",    "statuses": ["Standard", "Silver", "Gold", "Platinum"]},
    },
    "Airlines": {
        "United MileagePlus":      {"color": "#005daa", "statuses": ["None", "Silver", "Gold", "Platinum", "1K"]},
        "Delta SkyMiles":          {"color": "#c8102e", "statuses": ["None", "Silver Medallion", "Gold Medallion", "Platinum Medallion", "Diamond Medallion"]},
        "American AAdvantage":     {"color": "#0078d2", "statuses": ["None", "Gold", "Platinum", "Platinum Pro", "Executive Platinum"]},
        "Alaska Mileage Plan":     {"color": "#01426a", "statuses": ["None", "MVP", "MVP Gold", "MVP Gold 75K"]},
        "Southwest Rapid Rewards": {"color": "#304cb2", "statuses": ["None", "A-List", "A-List Preferred", "Companion Pass"]},
        "Air Canada Aeroplan":     {"color": "#c8102e", "statuses": ["None", "25K", "35K", "50K", "75K", "Super Elite"]},
        "British Airways Avios":   {"color": "#075aaa", "statuses": ["None", "Bronze", "Silver", "Gold"]},
        "Singapore KrisFlyer":     {"color": "#00338d", "statuses": ["None", "Elite Silver", "Elite Gold", "PPS Club"]},
    },
    "Hotels": {
        "Marriott Bonvoy":         {"color": "#c8a84b", "statuses": ["None", "Silver Elite", "Gold Elite", "Platinum Elite", "Titanium Elite", "Ambassador Elite"]},
        "Hilton Honors":           {"color": "#00205b", "statuses": ["None", "Silver", "Gold", "Diamond"]},
        "World of Hyatt":          {"color": "#8b1a1a", "statuses": ["None", "Discoverist", "Explorist", "Globalist"]},
        "IHG One Rewards":         {"color": "#006747", "statuses": ["None", "Silver Elite", "Gold Elite", "Platinum Elite", "Diamond Elite"]},
        "Wyndham Rewards":         {"color": "#0066b2", "statuses": ["None", "Blue", "Gold", "Platinum", "Diamond"]},
    },
}
ALL_PROGRAMS = {n: d for cat in PROGRAMS.values() for n, d in cat.items()}

def get_cat(name):
    for cat, progs in PROGRAMS.items():
        if name in progs: return cat
    return None

# ── Session state ──
for key, val in [("profile", {}), ("editing", None), ("page", "profile")]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Handle query-param actions from icon button links ──
qp = st.query_params
if "edit" in qp:
    prog = qp["edit"]
    if prog in st.session_state.profile:
        st.session_state.editing = prog
    st.query_params.clear()
    st.rerun()
if "remove" in qp:
    prog = qp["remove"]
    if prog in st.session_state.profile:
        del st.session_state.profile[prog]
        if st.session_state.editing == prog:
            st.session_state.editing = None
    st.query_params.clear()
    st.rerun()
if "page" in qp:
    st.session_state.page = qp["page"]
    st.query_params.clear()
    st.rerun()

# ── Mock result ──
MOCK = {
    "plain_english": "Use your Chase points for a lie-flat business class seat on ANA — one of the best flights in the world on this route. Transfer your Amex points to cover 4 hotel nights in central Tokyo, and the 5th night is free. Total out of pocket: about $150 in taxes.",
    "route_display": {"origin": "San Francisco", "destination": "Tokyo"},
    "hero": {"flight_pts": "60,000 Chase pts", "hotel_nights": "4 nights paid, 5th free", "cash": "~$150"},
    "points_bars": [
        {"name": "Chase UR",  "pct": 100, "color": "#378ADD", "label": "60k → flight"},
        {"name": "Amex MR",   "pct": 100, "color": "#1D9E75", "label": "80k → hotel"},
        {"name": "Left over", "pct": 20,  "color": "#1D9E75", "label": "~16k saved"},
    ],
    "flight": {"airline": "ANA (direct)", "book_via": "Air Canada Aeroplan", "points": "60,000 Chase UR", "cash_fees": "~$150"},
    "hotel":  {"name": "Courtyard Tokyo Ginza", "book_via": "Marriott Bonvoy", "points": "~96,000 Bonvoy", "fifth_night": "Free"},
    "perks": ["Lie-flat bed", "Premium dining", "Airport lounge", "5th night free", "No fuel surcharges"],
    "booking_steps": [
        {"title": "Create a free Aeroplan account", "desc": "Go to aeroplan.com and sign up — takes 2 minutes."},
        {"title": "Move your Chase points to Aeroplan", "desc": "Transfer 60,000 Chase UR to Aeroplan (instant). Search ANA Business SFO → NRT on June 10."},
        {"title": "Move your Amex points to Marriott", "desc": "Transfer 80,000 Amex MR to Bonvoy — you get ~96,000 pts thanks to the 20% bonus."},
        {"title": "Book 5 nights to unlock the free night", "desc": "Book 5 consecutive award nights and the 5th is automatically free."},
    ],
    "alternatives": [
        {"name": "United MileagePlus (simpler)", "desc": "Transfer Chase UR to United directly. Easier but costs ~80,000 miles.", "trade": "Burns 20,000 more points for the same seat"},
        {"name": "Amex → ANA Mileage Club", "desc": "Transfer Amex directly to ANA at 1:1. Round-trip Business ~88,000 miles.", "trade": "Limited award space on own metal"},
    ],
    "card": {"name": "Marriott Bonvoy Brilliant (Amex)", "bonus": "185,000 bonus points — covers 2–3 nights at the St. Regis Tokyo", "why": "Closes the hotel points gap. Also gets you Gold status, a $300 dining credit, and lounge access at SFO."},
    "confidence": "High for flight · Medium for hotel (book early)",
    "status": {"airline": "No elite status — ANA Business includes lounge access at NRT on arrival.", "hotel": "Standard room assignment without status. Bonvoy Brilliant grants automatic Gold."},
}


# ════════════════════════════════
#  PAGE: MY PROFILE
# ════════════════════════════════
def page_profile():
    st.markdown("## My Loyalty Profile")
    st.caption("Set up once — used for every trip. Click the pencil to edit, bin to remove.")

    profile = st.session_state.profile

    if not profile:
        st.info("No programs added yet. Use the form below to get started.")
    else:
        for cat_name, cat_progs in PROGRAMS.items():
            cat_entries = {k: v for k, v in profile.items() if k in cat_progs}
            if not cat_entries:
                continue

            st.markdown(f"**{cat_name}**")

            # Column header row
            st.markdown(
                '<div style="display:flex;gap:12px;padding:4px 2px 6px;">'
                '<div style="width:9px;flex-shrink:0;"></div>'
                '<div class="col-hdr" style="flex:2;">Program</div>'
                '<div class="col-hdr" style="flex:1;">Balance</div>'
                '<div class="col-hdr" style="flex:1;">Status</div>'
                '<div style="width:66px;flex-shrink:0;"></div>'
                '</div>',
                unsafe_allow_html=True)
            st.markdown("<div style='border-top:1px solid #e8e8e8;margin-bottom:2px;'></div>",
                        unsafe_allow_html=True)

            for prog_name, entry in cat_entries.items():
                pdata     = ALL_PROGRAMS[prog_name]
                color     = pdata["color"]
                status    = entry["status"]
                is_active = status not in ["None", "Standard"]
                pill_cls  = "act" if is_active else "std"
                # URL-encode the program name for query params
                import urllib.parse
                enc = urllib.parse.quote(prog_name)

                if st.session_state.editing == prog_name:
                    # ── Inline edit form ──
                    st.markdown(
                        f'<div style="background:#f8faff;border:1px solid #c5d8f7;'
                        f'border-radius:8px;padding:10px 12px;margin:4px 0;">'
                        f'<span style="font-size:12px;color:#1a56cc;font-weight:500;">'
                        f'Editing: {prog_name}</span></div>',
                        unsafe_allow_html=True)
                    ec1, ec2, ec3, ec4 = st.columns([2, 2, 1, 1])
                    with ec1:
                        new_bal = st.number_input(
                            "Balance", min_value=0, step=1000,
                            value=entry["balance"],
                            key=f"ebal_{prog_name}",
                            label_visibility="collapsed")
                    with ec2:
                        idx = pdata["statuses"].index(status) if status in pdata["statuses"] else 0
                        new_status = st.selectbox(
                            "Status", pdata["statuses"], index=idx,
                            key=f"estat_{prog_name}",
                            label_visibility="collapsed")
                    with ec3:
                        if st.button("Save", key=f"save_{prog_name}",
                                     use_container_width=True, type="primary"):
                            st.session_state.profile[prog_name] = {
                                "balance": new_bal, "status": new_status}
                            st.session_state.editing = None
                            st.rerun()
                    with ec4:
                        if st.button("Cancel", key=f"cancel_{prog_name}",
                                     use_container_width=True):
                            st.session_state.editing = None
                            st.rerun()
                else:
                    # ── View row — HTML with inline SVG icon links ──
                    st.markdown(
                        f'<div class="prog-row">'
                        f'<span class="prog-dot" style="background:{color};"></span>'
                        f'<span class="prog-name">{prog_name}</span>'
                        f'<span class="prog-bal">{entry["balance"]:,} pts</span>'
                        f'<span class="prog-pill {pill_cls}">{status}</span>'
                        f'<span class="prog-actions">'
                        f'<a class="icon-btn" href="?edit={enc}" title="Edit {prog_name}">{SVG_EDIT}</a>'
                        f'<a class="icon-btn del" href="?remove={enc}" title="Remove {prog_name}">{SVG_REMOVE}</a>'
                        f'</span>'
                        f'</div>',
                        unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

    # ── Add program ──
    st.markdown("---")
    st.markdown("**Add a program**")

    fc1, fc2, fc3, fc4, fc5 = st.columns([1.4, 1.8, 1.4, 1.8, 0.7])
    with fc1:
        add_cat = st.selectbox("Category", list(PROGRAMS.keys()),
                               key="prof_add_cat", label_visibility="collapsed")
    available = [p for p in PROGRAMS[add_cat] if p not in profile]
    with fc2:
        if available:
            add_prog = st.selectbox("Program", available,
                                    key="prof_add_prog", label_visibility="collapsed")
        else:
            st.selectbox("Program", ["— all added —"], disabled=True,
                         key="prof_add_prog_dis", label_visibility="collapsed")
            add_prog = None
    with fc3:
        add_bal = st.number_input("Balance", min_value=0, step=1000, value=0,
                                  key="prof_add_bal", label_visibility="collapsed")
    with fc4:
        if add_prog:
            add_status = st.selectbox("Status", PROGRAMS[add_cat][add_prog]["statuses"],
                                      key="prof_add_status", label_visibility="collapsed")
        else:
            st.selectbox("Status", ["—"], disabled=True,
                         key="prof_add_status_dis", label_visibility="collapsed")
            add_status = None
    with fc5:
        st.markdown("<div style='padding-top:4px;'>", unsafe_allow_html=True)
        if st.button("Add", use_container_width=True, type="primary",
                     disabled=not add_prog, key="prof_add_btn"):
            st.session_state.profile[add_prog] = {"balance": add_bal, "status": add_status}
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Column labels above the add form
    st.markdown(
        '<div style="display:flex;gap:0;margin-top:-2.5rem;margin-bottom:.25rem;">'
        '<div class="col-hdr" style="flex:1.4;">Category</div>'
        '<div class="col-hdr" style="flex:1.8;">Program</div>'
        '<div class="col-hdr" style="flex:1.4;">Balance</div>'
        '<div class="col-hdr" style="flex:1.8;">Status</div>'
        '</div>',
        unsafe_allow_html=True)


# ════════════════════════════════
#  PAGE: PLAN A TRIP
# ════════════════════════════════
def page_trip():
    profile = st.session_state.profile

    with st.sidebar:
        st.markdown("### Settings")
        api_key   = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
        mock_mode = st.toggle("Mock mode", value=True, help="Test without API calls")
        if mock_mode:
            st.caption("Sample data — no API key needed.")
        st.divider()

        st.markdown("### Trip details")
        origin      = st.text_input("From (city)",   value="San Francisco")
        origin_code = st.text_input("Airport code",  value="SFO", max_chars=4).upper()
        destination = st.text_input("To (city)",     value="Tokyo")
        dest_code   = st.text_input("Airport code ", value="NRT", max_chars=4).upper()
        dates       = st.text_input("Travel dates",  value="June 10–20, 2026")
        nights      = st.number_input("Nights", min_value=1, max_value=30, value=5)
        cabin       = st.selectbox("Cabin",       ["economy", "premium economy", "business", "first"])
        hotel_style = st.selectbox("Hotel style", ["budget", "standard", "luxury"])
        val_exp     = st.slider("Value ← → Experience", 1, 10, 5)
        st.divider()
        run = st.button("Find My Best Trip", type="primary", use_container_width=True)

    st.markdown("## Plan a Trip")

    if not profile:
        st.warning("Your loyalty profile is empty — go to **My Profile** and add your programs first.")
        return

    total_pts = sum(e["balance"] for e in profile.values())
    elite_ct  = sum(1 for e in profile.values() if e["status"] not in ["None", "Standard"])
    m1, m2, m3 = st.columns(3)
    m1.metric("Programs loaded", len(profile))
    m2.metric("Total points",    f"{total_pts:,}")
    m3.metric("Elite statuses",  elite_ct)
    st.markdown("---")

    if not run:
        st.info("Enter your trip details in the sidebar and click **Find My Best Trip**.")
        return

    def build_user_data():
        cc, al, ht, ast, hst = {}, {}, {}, {}, {}
        for pn, entry in profile.items():
            bal = entry["balance"]; s = entry["status"]; cat = get_cat(pn)
            if cat == "Credit Cards": cc[pn] = bal
            elif cat == "Airlines":
                al[pn] = bal
                if s != "None": ast[pn] = s
            elif cat == "Hotels":
                ht[pn] = bal
                if s != "None": hst[pn] = s
        return {
            "points":      {"credit_cards": cc, "airline_miles": al, "hotel_points": ht},
            "status":      {"airlines": ast, "hotels": hst},
            "trip":        {"origin": f"{origin} ({origin_code})", "destination": f"{destination} ({dest_code})",
                            "dates": dates, "nights": int(nights)},
            "preferences": {"cabin": cabin, "hotel_style": hotel_style, "value_vs_experience": val_exp},
        }

    SYSTEM = "You are an expert travel strategist. Return ONLY valid JSON, no markdown, no extra text."

    def build_prompt(d):
        return f"""Given the loyalty profile and trip below, generate the optimal travel strategy in plain friendly English.

USER PROFILE & TRIP:
{json.dumps(d, indent=2)}

Return EXACTLY this JSON:
{{
  "plain_english": "One friendly sentence summarising the strategy",
  "route_display": {{"origin": "{origin}", "destination": "{destination}"}},
  "hero": {{"flight_pts": "e.g. 60,000 Chase pts", "hotel_nights": "e.g. 4 nights paid, 5th free", "cash": "e.g. ~$150"}},
  "points_bars": [{{"name":"","pct":80,"color":"#378ADD","label":"60k → flight"}}],
  "flight": {{"airline":"","book_via":"","points":"","cash_fees":""}},
  "hotel":  {{"name":"","book_via":"","points":"","fifth_night":"Free or N/A"}},
  "perks": ["plain-English perk"],
  "booking_steps": [{{"title":"Action","desc":"Plain English explanation"}}],
  "alternatives": [{{"name":"","desc":"","trade":""}}],
  "card": {{"name":"","bonus":"","why":""}},
  "status": {{"airline":"","hotel":""}},
  "confidence": ""
}}
Use city names not codes. Keep it friendly. Do NOT assume real-time availability."""

    def call_claude(key, data):
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-opus-4-5", max_tokens=2000, system=SYSTEM,
            messages=[{"role": "user", "content": build_prompt(data)}])
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    def render(r, is_mock=False):
        if is_mock:
            st.markdown('<div class="mock-banner">Mock mode — sample data. Disable mock mode and add your API key for a real strategy.</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="plain-english"><b>In plain English:</b> {r.get("plain_english","")}</div>', unsafe_allow_html=True)

        rd = r.get("route_display", {}); hero = r.get("hero", {})
        st.markdown(f"""<div class="hero"><div class="hero-top">
          <div class="route"><span>{rd.get("origin",origin)}</span><div class="route-line"></div>&rarr;<div class="route-line"></div><span>{rd.get("destination",destination)}</span></div>
          <p class="tagline">{dates} &middot; {cabin.title()} class &middot; {int(nights)} nights</p>
        </div><div class="hero-bottom">
          <div class="hero-stat"><p class="hs-label">Flight</p><p class="hs-val">{hero.get("flight_pts","—")}</p><p class="hs-sub">points used</p></div>
          <div class="hero-stat"><p class="hs-label">Hotel</p><p class="hs-val">{hero.get("hotel_nights","—")}</p><p class="hs-sub">award nights</p></div>
          <div class="hero-stat"><p class="hs-label">Cash needed</p><p class="hs-val">{hero.get("cash","—")}</p><p class="hs-sub">taxes &amp; fees</p></div>
        </div></div>""", unsafe_allow_html=True)

        bars = r.get("points_bars", [])
        if bars:
            bh = "".join(f'<div class="pts-row"><span class="pts-name">{b["name"]}</span><div class="pts-track"><div class="pts-fill" style="width:{b["pct"]}%;background:{b["color"]};"></div></div><span class="pts-amt">{b["label"]}</span></div>' for b in bars)
            st.markdown(f'<div class="pts-wrap"><p class="pts-title">Your points at a glance</p>{bh}<div class="legend"><span class="legend-item"><span class="legend-dot" style="background:#378ADD;"></span>Flight</span><span class="legend-item"><span class="legend-dot" style="background:#1D9E75;"></span>Hotel</span><span class="legend-item"><span class="legend-dot" style="background:#E24B4A;"></span>Shortfall</span></div></div>', unsafe_allow_html=True)

        f = r.get("flight", {}); h = r.get("hotel", {})
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="res-card"><p class="card-head">Flight</p><div class="dr"><span class="dr-l">Airline</span><span class="dr-v">{f.get("airline","—")}</span></div><div class="dr"><span class="dr-l">Book through</span><span class="dr-v">{f.get("book_via","—")}</span></div><div class="dr"><span class="dr-l">Points used</span><span class="dr-v">{f.get("points","—")}</span></div><div class="dr"><span class="dr-l">Cash fees</span><span class="dr-v">{f.get("cash_fees","—")}</span></div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="res-card"><p class="card-head">Hotel</p><div class="dr"><span class="dr-l">Property</span><span class="dr-v">{h.get("name","—")}</span></div><div class="dr"><span class="dr-l">Book through</span><span class="dr-v">{h.get("book_via","—")}</span></div><div class="dr"><span class="dr-l">Points used</span><span class="dr-v">{h.get("points","—")}</span></div><div class="dr"><span class="dr-l">5th night</span><span class="dr-v">{h.get("fifth_night","—")}</span></div></div>', unsafe_allow_html=True)

        perks = r.get("perks", [])
        if perks:
            chips = "".join(f'<div class="chip">&#10003; {p}</div>' for p in perks)
            st.markdown(f'<div class="perks-row">{chips}</div>', unsafe_allow_html=True)

        steps = r.get("booking_steps", [])
        if steps:
            sh = "".join(f'<div class="step"><div class="step-num">{i+1}</div><div><p class="step-title">{s["title"]}</p><p class="step-desc">{s["desc"]}</p></div></div>' for i, s in enumerate(steps))
            st.markdown(f'<div class="steps-card"><p class="card-head">How to book</p>{sh}</div>', unsafe_allow_html=True)

        si = r.get("status", {})
        if si.get("airline") or si.get("hotel"):
            sc1, sc2 = st.columns(2)
            if si.get("airline"): sc1.info(f"Airline: {si['airline']}")
            if si.get("hotel"):   sc2.info(f"Hotel: {si['hotel']}")

        alts = r.get("alternatives", [])
        if alts:
            st.markdown("<br><small style='color:#999;font-weight:600;text-transform:uppercase;letter-spacing:.04em;'>Other options</small>", unsafe_allow_html=True)
            for a in alts:
                trade = f'<p class="alt-trade">Tradeoff: {a["trade"]}</p>' if a.get("trade") else ""
                st.markdown(f'<div class="alt-chip"><p class="alt-name">{a.get("name","")}</p><p class="alt-desc">{a.get("desc","")}</p>{trade}</div>', unsafe_allow_html=True)

        cc = r.get("card", {})
        if cc.get("name"):
            bonus = f'<p class="cc-bonus">{cc["bonus"]}</p>' if cc.get("bonus") else ""
            st.markdown(f'<div class="cc-wrap"><p class="cc-eye">Worth considering</p><p class="cc-name">{cc["name"]}</p>{bonus}<p class="cc-why">{cc.get("why","")}</p></div>', unsafe_allow_html=True)

        st.caption(f"Confidence: {r.get('confidence','')}")

    if mock_mode:
        render(MOCK, is_mock=True)
    elif not api_key:
        st.error("Add your Anthropic API key in the sidebar, or turn on mock mode.")
    else:
        with st.spinner("Finding your best trip…"):
            try:
                render(call_claude(api_key, build_user_data()))
            except json.JSONDecodeError as e:
                st.error(f"Unexpected response from Claude: {e}")
            except anthropic.AuthenticationError:
                st.error("Invalid API key — check console.anthropic.com")
            except anthropic.APIError as e:
                st.error(f"API error: {e}")
            except Exception as e:
                st.error(f"Something went wrong: {e}")


# ════════════════════════════════
#  NAV + ROUTER
# ════════════════════════════════
col_logo, col_nav = st.columns([3, 2])
with col_logo:
    st.markdown("# AI Loyalty Optimizer")
with col_nav:
    st.markdown("<div style='padding-top:20px;'>", unsafe_allow_html=True)
    nb1, nb2 = st.columns(2)
    with nb1:
        if st.button("My Profile", use_container_width=True,
                     type="primary" if st.session_state.page == "profile" else "secondary",
                     key="nav_profile"):
            st.session_state.page = "profile"
            st.rerun()
    with nb2:
        if st.button("Plan a Trip", use_container_width=True,
                     type="primary" if st.session_state.page == "trip" else "secondary",
                     key="nav_trip"):
            st.session_state.page = "trip"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin:.5rem 0 1.5rem;border:none;border-top:1px solid #e8e8e8;'>",
            unsafe_allow_html=True)

if st.session_state.page == "profile":
    page_profile()
else:
    page_trip()
