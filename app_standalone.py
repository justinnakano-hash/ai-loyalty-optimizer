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
.block-container { max-width: 900px !important; padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

/* Profile table */
.prog-table { width:100%; border-collapse:collapse; font-size:14px; }
.prog-table th { font-size:11px; font-weight:600; color:#999; text-transform:uppercase;
    letter-spacing:.05em; padding:8px 12px; border-bottom:2px solid #e8e8e8;
    text-align:left; background:#fafafa; }
.prog-table td { padding:10px 12px; border-bottom:1px solid #f0f0f0; vertical-align:middle; }
.prog-table tr:last-child td { border-bottom:none; }
.prog-table tr:hover td { background:#fafafa; }
.dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:8px; vertical-align:middle; }
.status-pill { display:inline-block; padding:2px 10px; border-radius:20px; font-size:12px;
    font-weight:500; background:#f0f0f0; color:#555; }
.status-pill.active { background:#e6f4ea; color:#1e5c2a; }
.cat-header { font-size:11px; font-weight:700; color:#999; text-transform:uppercase;
    letter-spacing:.06em; padding:14px 12px 6px; }

/* Add form */
.add-form { background:#fafafa; border:1px solid #e8e8e8; border-radius:12px;
    padding:1.25rem; margin-top:1.5rem; }

/* Results */
.plain-english { background:#e6f4ea; border-radius:10px; padding:.9rem 1.1rem;
    font-size:14px; color:#1e5c2a; line-height:1.65; margin-bottom:1.1rem; }
.hero { border:1px solid #e8e8e8; border-radius:12px; overflow:hidden; margin-bottom:1rem; }
.hero-top { padding:1.1rem 1.25rem; }
.route { font-size:19px; font-weight:600; color:#111; display:flex;
    align-items:center; gap:10px; margin-bottom:4px; }
.route-line { flex:1; height:1px; background:#ddd; }
.tagline { font-size:13px; color:#666; }
.hero-bottom { display:grid; grid-template-columns:1fr 1fr 1fr; border-top:1px solid #e8e8e8; }
.hero-stat { padding:.9rem 1.1rem; border-right:1px solid #e8e8e8; }
.hero-stat:last-child { border-right:none; }
.hs-label { font-size:11px; color:#999; text-transform:uppercase; letter-spacing:.05em; margin-bottom:3px; }
.hs-val { font-size:18px; font-weight:600; color:#111; }
.hs-sub { font-size:12px; color:#888; margin-top:2px; }
.pts-wrap { background:#fff; border:1px solid #e8e8e8; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem; }
.pts-title { font-size:11px; font-weight:600; color:#999; text-transform:uppercase;
    letter-spacing:.05em; margin-bottom:10px; }
.pts-row { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
.pts-name { font-size:13px; color:#111; min-width:130px; }
.pts-track { flex:1; height:8px; background:#f0f0f0; border-radius:4px; overflow:hidden; }
.pts-fill { height:100%; border-radius:4px; }
.pts-amt { font-size:12px; color:#888; min-width:90px; text-align:right; }
.legend { display:flex; gap:16px; margin-top:10px; }
.legend-item { font-size:11px; color:#999; display:flex; align-items:center; gap:5px; }
.legend-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.res-card { background:#fff; border:1px solid #e8e8e8; border-radius:12px; padding:1rem 1.25rem; }
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
.step { display:flex; gap:12px; padding:10px 0; border-bottom:1px solid #f5f5f5; align-items:flex-start; }
.step:last-child { border-bottom:none; }
.step-num { width:28px; height:28px; min-width:28px; border-radius:50%; background:#e8f0fe;
    display:flex; align-items:center; justify-content:center;
    font-size:12px; font-weight:600; color:#1a56cc; }
.step-title { font-size:13px; font-weight:600; color:#111; margin-bottom:3px; }
.step-desc { font-size:12px; color:#666; line-height:1.55; }
.alt-chip { background:#f7f7f7; border:1px solid #e8e8e8; border-radius:10px;
    padding:.75rem 1rem; margin-bottom:8px; }
.alt-name { font-size:13px; font-weight:600; color:#111; margin-bottom:3px; }
.alt-desc { font-size:12px; color:#555; margin-bottom:3px; }
.alt-trade { font-size:12px; color:#aaa; }
.cc-wrap { background:#f0f7ff; border:2px solid #a8d0f5; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem; }
.cc-eye { font-size:11px; color:#1a56cc; font-weight:600; text-transform:uppercase;
    letter-spacing:.05em; margin-bottom:6px; }
.cc-name { font-size:15px; font-weight:600; color:#111; margin-bottom:4px; }
.cc-bonus { font-size:13px; color:#2d7a3a; margin-bottom:6px; }
.cc-why { font-size:13px; color:#555; }
.mock-banner { background:#fff3e0; border:1px solid #ffcc80; border-radius:8px;
    padding:.6rem 1rem; font-size:13px; color:#e65100; margin-bottom:1rem; }
</style>
""", unsafe_allow_html=True)

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
for key, default in [("profile", {}), ("editing", None), ("page", "profile")]:
    if key not in st.session_state:
        st.session_state[key] = default

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
    st.caption("Your programs, balances, and status levels. Edit any row inline.")

    profile = st.session_state.profile

    if not profile:
        st.info("No programs added yet. Use the form below to get started.")
    else:
        # ── Table per category ──
        for cat_name, cat_progs in PROGRAMS.items():
            cat_entries = {k: v for k, v in profile.items() if k in cat_progs}
            if not cat_entries:
                continue

            st.markdown(f"**{cat_name}**")

            # Header row
            h1, h2, h3, h4, h5 = st.columns([3, 1.5, 1.8, 0.8, 0.8])
            h1.markdown("<small style='color:#999;font-weight:600;text-transform:uppercase;letter-spacing:.04em;'>Program</small>", unsafe_allow_html=True)
            h2.markdown("<small style='color:#999;font-weight:600;text-transform:uppercase;letter-spacing:.04em;'>Balance</small>", unsafe_allow_html=True)
            h3.markdown("<small style='color:#999;font-weight:600;text-transform:uppercase;letter-spacing:.04em;'>Status</small>", unsafe_allow_html=True)
            st.markdown("<hr style='margin:4px 0 0;border:none;border-top:1px solid #e8e8e8;'>", unsafe_allow_html=True)

            for prog_name, entry in cat_entries.items():
                pdata  = ALL_PROGRAMS[prog_name]
                color  = pdata["color"]

                if st.session_state.editing == prog_name:
                    # ── Inline edit row ──
                    with st.container():
                        st.markdown(f"<small style='color:#1a56cc;font-weight:500;'>Editing: {prog_name}</small>", unsafe_allow_html=True)
                        e1, e2, e3, e4 = st.columns([1.8, 1.8, 0.9, 0.9])
                        with e1:
                            new_bal = st.number_input("Balance", min_value=0, step=1000,
                                value=entry["balance"], key=f"ebal_{prog_name}", label_visibility="collapsed")
                        with e2:
                            idx = pdata["statuses"].index(entry["status"]) if entry["status"] in pdata["statuses"] else 0
                            new_status = st.selectbox("Status", pdata["statuses"], index=idx,
                                key=f"estat_{prog_name}", label_visibility="collapsed")
                        with e3:
                            if st.button("Save", key=f"save_{prog_name}", use_container_width=True, type="primary"):
                                st.session_state.profile[prog_name] = {"balance": new_bal, "status": new_status}
                                st.session_state.editing = None
                                st.rerun()
                        with e4:
                            if st.button("Cancel", key=f"cancel_{prog_name}", use_container_width=True):
                                st.session_state.editing = None
                                st.rerun()
                    st.markdown("<hr style='margin:4px 0;border:none;border-top:1px solid #f0f0f0;'>", unsafe_allow_html=True)

                else:
                    # ── View row ──
                    status = entry["status"]
                    is_active = status not in ["None", "Standard"]
                    pill_bg  = "#e6f4ea" if is_active else "#f0f0f0"
                    pill_col = "#1e5c2a" if is_active else "#666"

                    c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.8, 0.8, 0.8])
                    with c1:
                        st.markdown(
                            f'<div style="padding:8px 0;font-size:14px;">'
                            f'<span style="display:inline-block;width:9px;height:9px;border-radius:50%;'
                            f'background:{color};margin-right:8px;vertical-align:middle;"></span>'
                            f'<b>{prog_name}</b></div>',
                            unsafe_allow_html=True)
                    with c2:
                        st.markdown(
                            f'<div style="padding:8px 0;font-size:14px;font-weight:600;color:#111;">'
                            f'{entry["balance"]:,} pts</div>',
                            unsafe_allow_html=True)
                    with c3:
                        st.markdown(
                            f'<div style="padding:8px 0;">'
                            f'<span style="display:inline-block;padding:3px 10px;border-radius:20px;'
                            f'font-size:12px;font-weight:500;background:{pill_bg};color:{pill_col};">'
                            f'{status}</span></div>',
                            unsafe_allow_html=True)
                    with c4:
                        if st.button("Edit", key=f"edit_{prog_name}", use_container_width=True):
                            st.session_state.editing = prog_name
                            st.rerun()
                    with c5:
                        if st.button("Remove", key=f"del_{prog_name}", use_container_width=True):
                            del st.session_state.profile[prog_name]
                            if st.session_state.editing == prog_name:
                                st.session_state.editing = None
                            st.rerun()
                    st.markdown("<hr style='margin:0;border:none;border-top:1px solid #f0f0f0;'>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

    # ── Add program form ──
    st.markdown("---")
    st.markdown("**Add a program**")

    a1, a2, a3, a4, a5 = st.columns([2, 2, 2, 2, 1])
    with a1:
        add_cat = st.selectbox("Category", list(PROGRAMS.keys()), label_visibility="visible", key="add_cat")
    available = [p for p in PROGRAMS[add_cat] if p not in profile]
    with a2:
        if available:
            add_prog = st.selectbox("Program", available, key="add_prog")
        else:
            st.selectbox("Program", ["All added"], disabled=True, key="add_prog_dis")
            add_prog = None
    with a3:
        add_bal = st.number_input("Balance", min_value=0, step=1000, value=0, key="add_bal")
    with a4:
        if add_prog:
            pdata = PROGRAMS[add_cat][add_prog]
            add_status = st.selectbox("Status", pdata["statuses"], key="add_status")
        else:
            st.selectbox("Status", ["—"], disabled=True, key="add_status_dis")
            add_status = None
    with a5:
        st.markdown("<div style='padding-top:24px;'>", unsafe_allow_html=True)
        if st.button("Add", use_container_width=True, type="primary", disabled=not add_prog):
            st.session_state.profile[add_prog] = {"balance": add_bal, "status": add_status}
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════
#  PAGE: PLAN A TRIP
# ════════════════════════════════
def page_trip():
    profile = st.session_state.profile

    # Sidebar: trip inputs only
    with st.sidebar:
        st.markdown("### Settings")
        api_key   = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
        mock_mode = st.toggle("Mock mode", value=True, help="Test UI without API calls")
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

    # Main panel
    st.markdown("## Plan a Trip")

    if not profile:
        st.warning("Your loyalty profile is empty. Go to **My Profile** and add your programs first.")
        return

    # Profile summary strip
    total_programs = len(profile)
    total_pts      = sum(e["balance"] for e in profile.values())
    s1, s2, s3 = st.columns(3)
    s1.metric("Programs loaded", total_programs)
    s2.metric("Total points", f"{total_pts:,}")
    s3.metric("Elite statuses", sum(1 for e in profile.values() if e["status"] not in ["None", "Standard"]))

    st.markdown("---")

    if not run:
        st.info("Enter your trip details in the sidebar and click **Find My Best Trip**.")
        return

    def build_user_data():
        credit_cards, airlines, hotels = {}, {}, {}
        airline_statuses, hotel_statuses = {}, {}
        for prog_name, entry in profile.items():
            bal    = entry["balance"]
            status = entry["status"]
            cat    = get_cat(prog_name)
            if cat == "Credit Cards":
                credit_cards[prog_name] = bal
            elif cat == "Airlines":
                airlines[prog_name] = bal
                if status != "None": airline_statuses[prog_name] = status
            elif cat == "Hotels":
                hotels[prog_name] = bal
                if status != "None": hotel_statuses[prog_name] = status
        return {
            "points":      {"credit_cards": credit_cards, "airline_miles": airlines, "hotel_points": hotels},
            "status":      {"airlines": airline_statuses, "hotels": hotel_statuses},
            "trip":        {"origin": f"{origin} ({origin_code})", "destination": f"{destination} ({dest_code})", "dates": dates, "nights": int(nights)},
            "preferences": {"cabin": cabin, "hotel_style": hotel_style, "value_vs_experience": val_exp},
        }

    SYSTEM = "You are an expert travel strategist. Return ONLY valid JSON, no markdown, no extra text."

    def build_prompt(d):
        return f"""Given the user loyalty profile and trip below, generate the most optimal travel strategy in plain, friendly English.

USER PROFILE & TRIP:
{json.dumps(d, indent=2)}

Return EXACTLY this JSON (plain English, no jargon):
{{
  "plain_english": "One friendly sentence summarising the strategy",
  "route_display": {{"origin": "{origin}", "destination": "{destination}"}},
  "hero": {{"flight_pts": "e.g. 60,000 Chase pts", "hotel_nights": "e.g. 4 nights paid, 5th free", "cash": "e.g. ~$150"}},
  "points_bars": [
    {{"name": "Program", "pct": 80, "color": "#378ADD", "label": "60k → flight"}},
    {{"name": "Program", "pct": 60, "color": "#1D9E75", "label": "80k → hotel"}}
  ],
  "flight": {{"airline": "", "book_via": "", "points": "", "cash_fees": ""}},
  "hotel":  {{"name": "", "book_via": "", "points": "", "fifth_night": "Free or N/A"}},
  "perks": ["short plain-English perk"],
  "booking_steps": [{{"title": "Action", "desc": "Plain English explanation"}}],
  "alternatives": [{{"name": "", "desc": "", "trade": ""}}],
  "card": {{"name": "", "bonus": "", "why": ""}},
  "status": {{"airline": "", "hotel": ""}},
  "confidence": ""
}}
Use city names not codes. Keep everything friendly and simple. Do NOT assume real-time availability."""

    def call_claude(key, data):
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-opus-4-5", max_tokens=2000, system=SYSTEM,
            messages=[{"role": "user", "content": build_prompt(data)}]
        )
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    def render(r, is_mock=False):
        if is_mock:
            st.markdown('<div class="mock-banner">Mock mode — sample data. Disable mock mode and add your API key for a real strategy.</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="plain-english"><b>In plain English:</b> {r.get("plain_english","")}</div>', unsafe_allow_html=True)

        rd = r.get("route_display", {}); hero = r.get("hero", {})
        st.markdown(f"""
        <div class="hero">
          <div class="hero-top">
            <div class="route"><span>{rd.get("origin", origin)}</span><div class="route-line"></div>&rarr;<div class="route-line"></div><span>{rd.get("destination", destination)}</span></div>
            <p class="tagline">{dates} · {cabin.title()} class · {int(nights)} nights</p>
          </div>
          <div class="hero-bottom">
            <div class="hero-stat"><p class="hs-label">Flight</p><p class="hs-val">{hero.get("flight_pts","—")}</p><p class="hs-sub">points used</p></div>
            <div class="hero-stat"><p class="hs-label">Hotel</p><p class="hs-val">{hero.get("hotel_nights","—")}</p><p class="hs-sub">award nights</p></div>
            <div class="hero-stat"><p class="hs-label">Cash needed</p><p class="hs-val">{hero.get("cash","—")}</p><p class="hs-sub">taxes &amp; fees</p></div>
          </div>
        </div>""", unsafe_allow_html=True)

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
            st.markdown(f'<div class="perks-row">{"".join(f"<div class=chip>✓ {p}</div>" for p in perks)}</div>', unsafe_allow_html=True)

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

    # Run
    if mock_mode:
        render(MOCK, is_mock=True)
    else:
        if not api_key:
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
#  NAV
# ════════════════════════════════
col_logo, col_nav = st.columns([3, 2])
with col_logo:
    st.markdown("# AI Loyalty Optimizer")
with col_nav:
    st.markdown("<div style='padding-top:18px;text-align:right;'>", unsafe_allow_html=True)
    n1, n2 = st.columns(2)
    with n1:
        if st.button("My Profile", use_container_width=True,
                     type="primary" if st.session_state.page == "profile" else "secondary"):
            st.session_state.page = "profile"
            st.rerun()
    with n2:
        if st.button("Plan a Trip", use_container_width=True,
                     type="primary" if st.session_state.page == "trip" else "secondary"):
            st.session_state.page = "trip"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin:0 0 1.5rem;'>", unsafe_allow_html=True)

if st.session_state.page == "profile":
    page_profile()
else:
    page_trip()
