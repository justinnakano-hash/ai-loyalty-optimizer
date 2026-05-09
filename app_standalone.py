import streamlit as st
import anthropic
import json
import re

st.set_page_config(
    page_title="AI Loyalty Optimizer",
    page_icon="✈️",
    layout="centered",
)

st.markdown("""
<style>
.block-container { max-width:860px !important; padding-top:1.5rem !important; }
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

# ─────────────────────────────────────────────
#  AIRPORTS — city → (display label, IATA code)
# ─────────────────────────────────────────────
AIRPORTS = {
    "Atlanta, GA — Hartsfield-Jackson (ATL)":         "ATL",
    "Austin, TX — Austin-Bergstrom (AUS)":             "AUS",
    "Bangkok — Suvarnabhumi (BKK)":                    "BKK",
    "Barcelona — El Prat (BCN)":                       "BCN",
    "Beijing — Capital (PEK)":                         "PEK",
    "Boston, MA — Logan (BOS)":                        "BOS",
    "Buenos Aires — Ezeiza (EZE)":                     "EZE",
    "Cairo — Cairo International (CAI)":               "CAI",
    "Cancun — Cancun International (CUN)":             "CUN",
    "Cape Town — Cape Town International (CPT)":       "CPT",
    "Chicago, IL — O'Hare (ORD)":                      "ORD",
    "Chicago, IL — Midway (MDW)":                      "MDW",
    "Dallas, TX — DFW (DFW)":                          "DFW",
    "Denver, CO — Denver International (DEN)":         "DEN",
    "Dubai — Dubai International (DXB)":               "DXB",
    "Dublin — Dublin Airport (DUB)":                   "DUB",
    "Frankfurt — Frankfurt Airport (FRA)":             "FRA",
    "Honolulu, HI — Daniel K. Inouye (HNL)":          "HNL",
    "Hong Kong — Hong Kong International (HKG)":       "HKG",
    "Houston, TX — George Bush (IAH)":                 "IAH",
    "Istanbul — Istanbul Airport (IST)":               "IST",
    "Jakarta — Soekarno-Hatta (CGK)":                  "CGK",
    "Johannesburg — O.R. Tambo (JNB)":                 "JNB",
    "Kuala Lumpur — KL International (KUL)":           "KUL",
    "Las Vegas, NV — Harry Reid (LAS)":                "LAS",
    "Lisbon — Humberto Delgado (LIS)":                 "LIS",
    "London — Heathrow (LHR)":                         "LHR",
    "London — Gatwick (LGW)":                          "LGW",
    "Los Angeles, CA — LAX (LAX)":                     "LAX",
    "Madrid — Adolfo Suárez Barajas (MAD)":            "MAD",
    "Melbourne — Tullamarine (MEL)":                   "MEL",
    "Mexico City — Benito Juárez (MEX)":               "MEX",
    "Miami, FL — Miami International (MIA)":           "MIA",
    "Milan — Malpensa (MXP)":                          "MXP",
    "Minneapolis, MN — MSP (MSP)":                     "MSP",
    "Montreal — Trudeau (YUL)":                        "YUL",
    "Mumbai — Chhatrapati Shivaji (BOM)":              "BOM",
    "Munich — Franz Josef Strauss (MUC)":              "MUC",
    "Nairobi — Jomo Kenyatta (NBO)":                   "NBO",
    "New York, NY — JFK (JFK)":                        "JFK",
    "New York, NY — Newark (EWR)":                     "EWR",
    "New York, NY — LaGuardia (LGA)":                  "LGA",
    "Orlando, FL — Orlando International (MCO)":       "MCO",
    "Paris — Charles de Gaulle (CDG)":                 "CDG",
    "Paris — Orly (ORY)":                              "ORY",
    "Philadelphia, PA — PHL (PHL)":                    "PHL",
    "Phoenix, AZ — Sky Harbor (PHX)":                  "PHX",
    "Rome — Leonardo da Vinci (FCO)":                  "FCO",
    "San Francisco, CA — SFO (SFO)":                   "SFO",
    "San Jose, CA — Mineta (SJC)":                     "SJC",
    "Santiago — Comodoro Arturo Merino (SCL)":         "SCL",
    "São Paulo — Guarulhos (GRU)":                     "GRU",
    "Seattle, WA — Sea-Tac (SEA)":                     "SEA",
    "Seoul — Incheon (ICN)":                           "ICN",
    "Shanghai — Pudong (PVG)":                         "PVG",
    "Singapore — Changi (SIN)":                        "SIN",
    "Sydney — Kingsford Smith (SYD)":                  "SYD",
    "Tokyo — Narita (NRT)":                            "NRT",
    "Tokyo — Haneda (HND)":                            "HND",
    "Toronto — Pearson (YYZ)":                         "YYZ",
    "Vancouver — YVR (YVR)":                           "YVR",
    "Vienna — Vienna International (VIE)":             "VIE",
    "Warsaw — Chopin (WAW)":                           "WAW",
    "Washington DC — Dulles (IAD)":                    "IAD",
    "Washington DC — Reagan (DCA)":                    "DCA",
    "Zurich — Zurich Airport (ZRH)":                   "ZRH",
}
AIRPORT_LABELS = list(AIRPORTS.keys())

# ─────────────────────────────────────────────
#  PROGRAM CATALOGUE
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
if "profile" not in st.session_state: st.session_state.profile = {}
if "page"    not in st.session_state: st.session_state.page    = "profile"
if "editing" not in st.session_state: st.session_state.editing = None

# ─────────────────────────────────────────────
#  MOCK DATA
# ─────────────────────────────────────────────
MOCK = {
    "plain_english": "Use your Chase points for a lie-flat ANA business class seat — one of the best on this route. Transfer your Amex points for 4 hotel nights in central Tokyo; the 5th is free. Out of pocket: about $150 in taxes.",
    "route_display": {"origin": "San Francisco", "destination": "Tokyo"},
    "hero": {"flight_pts": "60,000 Chase pts", "hotel_nights": "4 nights paid, 5th free", "cash": "~$150"},
    "points_bars": [
        {"name": "Chase UR",  "pct": 100, "color": "#378ADD", "label": "60k → flight"},
        {"name": "Amex MR",   "pct": 100, "color": "#1D9E75", "label": "80k → hotel"},
        {"name": "Left over", "pct": 20,  "color": "#1D9E75", "label": "~16k saved"},
    ],
    "flight": {"airline": "ANA (direct)", "book_via": "Air Canada Aeroplan", "points": "60,000 Chase UR", "cash_fees": "~$150"},
    "hotel":  {"name": "Courtyard Tokyo Ginza", "book_via": "Marriott Bonvoy", "points": "~96,000 Bonvoy", "fifth_night": "Free"},
    "perks": ["Lie-flat bed", "Premium dining", "Airport lounge access", "5th hotel night free", "No fuel surcharges"],
    "booking_steps": [
        {"title": "Create a free Aeroplan account", "desc": "Go to aeroplan.com and sign up — takes 2 minutes."},
        {"title": "Move your Chase points to Aeroplan", "desc": "Transfer 60,000 Chase UR to Aeroplan (instant). Search ANA Business SFO → NRT on June 10."},
        {"title": "Move your Amex points to Marriott", "desc": "Transfer 80,000 Amex MR to Bonvoy — you get ~96,000 pts thanks to the 20% bonus. Search Bonvoy for Tokyo Ginza hotels."},
        {"title": "Book 5 nights to get the free night", "desc": "Book 5 consecutive award nights — Bonvoy makes the 5th free automatically."},
    ],
    "alternatives": [
        {"name": "United MileagePlus (simpler)", "desc": "Transfer Chase UR to United directly — easier but costs ~80,000 miles.", "trade": "Burns 20,000 more points for the same seat"},
        {"name": "Amex → ANA Mileage Club", "desc": "Transfer Amex MR directly to ANA at 1:1. Round-trip Business ~88,000 miles.", "trade": "Limited award space on own metal"},
    ],
    "card": {"name": "Marriott Bonvoy Brilliant (Amex)", "bonus": "185,000 bonus points — covers 2–3 nights at the St. Regis Tokyo", "why": "Closes the hotel gap. Comes with Gold status, $300 dining credit, and Priority Pass lounge access at SFO."},
    "confidence": "High for flight · Medium for hotel (book early)",
    "status": {"airline": "No elite status — ANA Business includes lounge access at NRT on arrival.", "hotel": "Standard room assignment. The Bonvoy Brilliant card grants automatic Gold status."},
}


# ─────────────────────────────────────────────
#  PAGE: MY PROFILE
# ─────────────────────────────────────────────
def page_profile():
    st.markdown("## My Loyalty Profile")
    st.caption("Set up once — used for every trip.")

    profile = st.session_state.profile
    editing = st.session_state.get("editing", None)

    if not profile:
        st.info("No programs added yet. Use the form below to get started.")
    else:
        for cat_name, cat_progs in PROGRAMS.items():
            cat_entries = {k: v for k, v in profile.items() if k in cat_progs}
            if not cat_entries:
                continue

            # Category heading
            st.markdown(
                f'<p style="font-size:11px;font-weight:700;color:#999;'
                f'text-transform:uppercase;letter-spacing:.06em;'
                f'margin:1rem 0 4px;">{cat_name}</p>',
                unsafe_allow_html=True)
            st.markdown(
                '<div style="border-top:1px solid #e8e8e8;margin-bottom:2px;"></div>',
                unsafe_allow_html=True)

            for prog_name, entry in cat_entries.items():
                pdata  = ALL_PROGRAMS[prog_name]
                color  = pdata["color"]
                status = entry["status"]
                bal    = entry["balance"]

                if editing == prog_name:
                    # ── Inline edit row ──
                    st.markdown(
                        f'<div style="background:#f0f6ff;border:1px solid #c5d8f7;'
                        f'border-radius:8px;padding:6px 10px;margin:4px 0;">' 
                        f'<span style="font-size:12px;color:#1a56cc;font-weight:500;">'
                        f'Editing — {prog_name}</span></div>',
                        unsafe_allow_html=True)
                    e1, e2, e3, e4 = st.columns([2, 2, 1, 1])
                    with e1:
                        new_bal = st.number_input(
                            "Balance", min_value=0, step=1000, value=bal,
                            key=f"ebal_{prog_name}", label_visibility="collapsed")
                    with e2:
                        idx = pdata["statuses"].index(status)                             if status in pdata["statuses"] else 0
                        new_status = st.selectbox(
                            "Status", pdata["statuses"], index=idx,
                            key=f"estat_{prog_name}", label_visibility="collapsed")
                    with e3:
                        if st.button("Save", key=f"save_{prog_name}",
                                     use_container_width=True, type="primary"):
                            st.session_state.profile[prog_name] = {
                                "balance": new_bal, "status": new_status}
                            st.session_state.editing = None
                            st.rerun()
                    with e4:
                        if st.button("Cancel", key=f"cancel_{prog_name}",
                                     use_container_width=True):
                            st.session_state.editing = None
                            st.rerun()

                else:
                    # ── View row ──
                    is_active = status not in ["None", "Standard"]
                    pill_bg   = "#e6f4ea" if is_active else "#f0f0f0"
                    pill_col  = "#1e5c2a" if is_active else "#666"

                    # Single st.columns call — info wide, two narrow icon buttons
                    r_info, r_edit, r_del = st.columns([7, 1, 1])

                    with r_info:
                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:10px;'
                            f'padding:8px 0;border-bottom:1px solid #f5f5f5;">'
                            f'<span style="width:9px;height:9px;border-radius:50%;'
                            f'background:{color};flex-shrink:0;display:inline-block;"></span>'
                            f'<span style="font-size:13px;font-weight:600;color:#111;'
                            f'flex:1;">{prog_name}</span>'
                            f'<span style="font-size:13px;color:#555;'
                            f'white-space:nowrap;">{bal:,} pts</span>'
                            f'<span style="display:inline-block;padding:2px 10px;'
                            f'border-radius:20px;font-size:11px;font-weight:500;'
                            f'background:{pill_bg};color:{pill_col};'
                            f'white-space:nowrap;margin-left:4px;">{status}</span>'
                            f'</div>',
                            unsafe_allow_html=True)

                    with r_edit:
                        if st.button("Edit", key=f"edit_{prog_name}",
                                     use_container_width=True,
                                     help=f"Edit {prog_name}"):
                            st.session_state.editing = prog_name
                            st.rerun()

                    with r_del:
                        if st.button("Remove", key=f"del_{prog_name}",
                                     use_container_width=True,
                                     help=f"Remove {prog_name}"):
                            del st.session_state.profile[prog_name]
                            if st.session_state.editing == prog_name:
                                st.session_state.editing = None
                            st.rerun()

        # Summary bar
        total = sum(e["balance"] for e in profile.values())
        elite = sum(1 for e in profile.values()
                    if e["status"] not in ["None", "Standard"])
        st.markdown(
            f'<div style="margin-top:1rem;padding:.75rem 1rem;background:#f7f7f7;'
            f'border-radius:8px;font-size:13px;color:#555;">'
            f'<b>{len(profile)}</b> programs &nbsp;&middot;&nbsp; '
            f'<b>{total:,}</b> total points &nbsp;&middot;&nbsp; '
            f'<b>{elite}</b> elite status(es)'
            f'</div>',
            unsafe_allow_html=True)

    # ── Add program ──
    st.markdown("---")
    st.markdown("**Add a program**")

    ac1, ac2, ac3, ac4, ac5 = st.columns([1.4, 1.8, 1.4, 1.8, 0.8])
    with ac1:
        add_cat = st.selectbox("Category", list(PROGRAMS.keys()),
                               key="add_cat", label_visibility="collapsed")
    already_added = set(profile.keys())
    available = [p for p in PROGRAMS[add_cat] if p not in already_added]
    with ac2:
        if available:
            add_prog = st.selectbox("Program", available,
                                    key="add_prog", label_visibility="collapsed")
        else:
            st.selectbox("Program", ["— all added —"], disabled=True,
                         key="add_prog_dis", label_visibility="collapsed")
            add_prog = None
    with ac3:
        add_bal = st.number_input("Balance (pts)", min_value=0, step=1000, value=0,
                                  key="add_bal", label_visibility="collapsed")
    with ac4:
        if add_prog:
            add_status = st.selectbox(
                "Status", PROGRAMS[add_cat][add_prog]["statuses"],
                key="add_status", label_visibility="collapsed")
        else:
            st.selectbox("Status", ["—"], disabled=True,
                         key="add_status_dis", label_visibility="collapsed")
            add_status = None
    with ac5:
        # Use empty label + markdown spacer to align button with inputs
        st.markdown("<div style='margin-top:4px;'>", unsafe_allow_html=True)
        if st.button("+ Add", use_container_width=True, type="primary",
                     disabled=not add_prog, key="add_btn"):
            st.session_state.profile[add_prog] = {
                "balance": add_bal, "status": add_status}
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Column hint labels
    st.markdown(
        '<div style="display:flex;gap:0;margin-top:.3rem;">' 
        '<span style="font-size:11px;color:#bbb;flex:1.4;">Category</span>'
        '<span style="font-size:11px;color:#bbb;flex:1.8;">Program</span>'
        '<span style="font-size:11px;color:#bbb;flex:1.4;">Balance</span>'
        '<span style="font-size:11px;color:#bbb;flex:1.8;">Status</span>'
        '</div>',
        unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  PAGE: PLAN A TRIP
# ─────────────────────────────────────────────
def page_trip():
    profile = st.session_state.profile

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("### Settings")
        api_key   = st.text_input("Anthropic API Key", type="password",
                                  placeholder="sk-ant-...")
        mock_mode = st.toggle("Mock mode", value=True,
                              help="Test the UI without using API tokens")
        if mock_mode:
            st.caption("Sample data — no API key needed.")
        st.divider()

        st.markdown("### Where are you flying?")

        # Origin — searchable selectbox
        origin_label = st.selectbox(
            "Flying from",
            AIRPORT_LABELS,
            index=AIRPORT_LABELS.index("San Francisco, CA — SFO (SFO)"),
            key="origin_sel")
        origin_code = AIRPORTS[origin_label]
        origin_city = origin_label.split(" —")[0]
        st.caption(f"Airport code: **{origin_code}**")

        # Destination — searchable selectbox
        dest_label = st.selectbox(
            "Flying to",
            AIRPORT_LABELS,
            index=AIRPORT_LABELS.index("Tokyo — Narita (NRT)"),
            key="dest_sel")
        dest_code = AIRPORTS[dest_label]
        dest_city = dest_label.split(" —")[0]
        st.caption(f"Airport code: **{dest_code}**")

        st.divider()
        st.markdown("### Trip details")
        dates       = st.text_input("Travel dates",  value="June 10–20, 2026")
        nights      = st.number_input("Nights", min_value=1, max_value=30, value=5)
        cabin       = st.selectbox("Cabin class",
                                   ["Economy", "Premium Economy", "Business", "First"])
        hotel_style = st.selectbox("Hotel style", ["Budget", "Standard", "Luxury"])
        val_exp     = st.slider("Priority", 1, 10, 5,
                                help="1 = maximize points value  ·  10 = maximize experience quality")
        st.caption("Value ← · → Experience")
        st.divider()
        run = st.button("Find My Best Trip", type="primary", use_container_width=True)

    # ── Main panel ──
    st.markdown("## Plan a Trip")

    if not profile:
        st.warning("Your loyalty profile is empty. Go to **My Profile** and add your programs first.")
        return

    # Profile summary strip
    total_pts = sum(e["balance"] for e in profile.values())
    elite_ct  = sum(1 for e in profile.values() if e["status"] not in ["None", "Standard"])
    m1, m2, m3 = st.columns(3)
    m1.metric("Programs loaded",  len(profile))
    m2.metric("Total points",     f"{total_pts:,}")
    m3.metric("Elite statuses",   elite_ct)
    st.markdown("---")

    if not run:
        st.info("Select your origin, destination, and trip details in the sidebar, then click **Find My Best Trip**.")
        return

    # ── Build API payload ──
    def build_data():
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
            "trip":        {
                "origin":      f"{origin_city} ({origin_code})",
                "destination": f"{dest_city} ({dest_code})",
                "dates":       dates,
                "nights":      int(nights),
            },
            "preferences": {
                "cabin":               cabin,
                "hotel_style":         hotel_style,
                "value_vs_experience": val_exp,
            },
        }

    SYSTEM = ("You are an expert travel strategist. "
              "Return ONLY valid JSON, no markdown, no extra text.")

    def build_prompt(d):
        return f"""Given the loyalty profile and trip, generate the optimal travel strategy in plain English.

USER PROFILE & TRIP:
{json.dumps(d, indent=2)}

Return EXACTLY this JSON:
{{
  "plain_english": "One friendly sentence — no jargon",
  "route_display": {{"origin": "{origin_city}", "destination": "{dest_city}"}},
  "hero": {{
    "flight_pts": "e.g. 60,000 Chase pts",
    "hotel_nights": "e.g. 4 nights paid, 5th free",
    "cash": "e.g. ~$150"
  }},
  "points_bars": [{{"name":"","pct":80,"color":"#378ADD","label":"60k → flight"}}],
  "flight": {{"airline":"","book_via":"","points":"","cash_fees":""}},
  "hotel":  {{"name":"","book_via":"","points":"","fifth_night":"Free or N/A"}},
  "perks": ["plain-English perk"],
  "booking_steps": [{{"title":"Short action","desc":"Plain English step"}}],
  "alternatives": [{{"name":"","desc":"","trade":""}}],
  "card": {{"name":"","bonus":"","why":""}},
  "status": {{"airline":"","hotel":""}},
  "confidence": ""
}}
Use city names not airport codes. Be friendly. Do NOT assume real-time availability."""

    def call_claude(key, data):
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-opus-4-5", max_tokens=2000, system=SYSTEM,
            messages=[{"role": "user", "content": build_prompt(data)}])
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    # ── Render results ──
    def render(r, is_mock=False):
        if is_mock:
            st.markdown(
                '<div class="mock-banner">Mock mode — sample data. '
                'Disable mock mode and add your API key for a real strategy.</div>',
                unsafe_allow_html=True)

        st.markdown(
            f'<div class="plain-english"><b>In plain English:</b> '
            f'{r.get("plain_english","")}</div>',
            unsafe_allow_html=True)

        rd = r.get("route_display", {}); hero = r.get("hero", {})
        st.markdown(f"""
        <div class="hero"><div class="hero-top">
          <div class="route">
            <span>{rd.get("origin", origin_city)}</span>
            <div class="route-line"></div>&rarr;<div class="route-line"></div>
            <span>{rd.get("destination", dest_city)}</span>
          </div>
          <p class="tagline">{dates} &middot; {cabin} class &middot; {int(nights)} nights</p>
        </div><div class="hero-bottom">
          <div class="hero-stat">
            <p class="hs-label">Flight</p>
            <p class="hs-val">{hero.get("flight_pts","—")}</p>
            <p class="hs-sub">points used</p>
          </div>
          <div class="hero-stat">
            <p class="hs-label">Hotel</p>
            <p class="hs-val">{hero.get("hotel_nights","—")}</p>
            <p class="hs-sub">award nights</p>
          </div>
          <div class="hero-stat">
            <p class="hs-label">Cash needed</p>
            <p class="hs-val">{hero.get("cash","—")}</p>
            <p class="hs-sub">taxes &amp; fees</p>
          </div>
        </div></div>""", unsafe_allow_html=True)

        bars = r.get("points_bars", [])
        if bars:
            bh = "".join(
                f'<div class="pts-row">'
                f'<span class="pts-name">{b["name"]}</span>'
                f'<div class="pts-track"><div class="pts-fill" '
                f'style="width:{b["pct"]}%;background:{b["color"]};"></div></div>'
                f'<span class="pts-amt">{b["label"]}</span></div>'
                for b in bars)
            st.markdown(
                f'<div class="pts-wrap"><p class="pts-title">Your points at a glance</p>{bh}'
                f'<div class="legend">'
                f'<span class="legend-item"><span class="legend-dot" style="background:#378ADD;"></span>Flight</span>'
                f'<span class="legend-item"><span class="legend-dot" style="background:#1D9E75;"></span>Hotel</span>'
                f'<span class="legend-item"><span class="legend-dot" style="background:#E24B4A;"></span>Shortfall</span>'
                f'</div></div>', unsafe_allow_html=True)

        f = r.get("flight", {}); h = r.get("hotel", {})
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f'<div class="res-card"><p class="card-head">Flight</p>'
                f'<div class="dr"><span class="dr-l">Airline</span><span class="dr-v">{f.get("airline","—")}</span></div>'
                f'<div class="dr"><span class="dr-l">Book through</span><span class="dr-v">{f.get("book_via","—")}</span></div>'
                f'<div class="dr"><span class="dr-l">Points used</span><span class="dr-v">{f.get("points","—")}</span></div>'
                f'<div class="dr"><span class="dr-l">Cash fees</span><span class="dr-v">{f.get("cash_fees","—")}</span></div>'
                f'</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(
                f'<div class="res-card"><p class="card-head">Hotel</p>'
                f'<div class="dr"><span class="dr-l">Property</span><span class="dr-v">{h.get("name","—")}</span></div>'
                f'<div class="dr"><span class="dr-l">Book through</span><span class="dr-v">{h.get("book_via","—")}</span></div>'
                f'<div class="dr"><span class="dr-l">Points used</span><span class="dr-v">{h.get("points","—")}</span></div>'
                f'<div class="dr"><span class="dr-l">5th night</span><span class="dr-v">{h.get("fifth_night","—")}</span></div>'
                f'</div>', unsafe_allow_html=True)

        perks = r.get("perks", [])
        if perks:
            chips = "".join(f'<div class="chip">&#10003; {p}</div>' for p in perks)
            st.markdown(f'<div class="perks-row">{chips}</div>', unsafe_allow_html=True)

        steps = r.get("booking_steps", [])
        if steps:
            sh = "".join(
                f'<div class="step"><div class="step-num">{i+1}</div>'
                f'<div><p class="step-title">{s["title"]}</p>'
                f'<p class="step-desc">{s["desc"]}</p></div></div>'
                for i, s in enumerate(steps))
            st.markdown(
                f'<div class="steps-card"><p class="card-head">How to book</p>{sh}</div>',
                unsafe_allow_html=True)

        si = r.get("status", {})
        if si.get("airline") or si.get("hotel"):
            sc1, sc2 = st.columns(2)
            if si.get("airline"): sc1.info(f"Airline: {si['airline']}")
            if si.get("hotel"):   sc2.info(f"Hotel: {si['hotel']}")

        alts = r.get("alternatives", [])
        if alts:
            st.markdown(
                "<br><small style='color:#999;font-weight:600;"
                "text-transform:uppercase;letter-spacing:.04em;'>Other options</small>",
                unsafe_allow_html=True)
            for a in alts:
                trade = (f'<p class="alt-trade">Tradeoff: {a["trade"]}</p>'
                         if a.get("trade") else "")
                st.markdown(
                    f'<div class="alt-chip">'
                    f'<p class="alt-name">{a.get("name","")}</p>'
                    f'<p class="alt-desc">{a.get("desc","")}</p>{trade}</div>',
                    unsafe_allow_html=True)

        cc = r.get("card", {})
        if cc.get("name"):
            bonus = f'<p class="cc-bonus">{cc["bonus"]}</p>' if cc.get("bonus") else ""
            st.markdown(
                f'<div class="cc-wrap"><p class="cc-eye">Worth considering</p>'
                f'<p class="cc-name">{cc["name"]}</p>{bonus}'
                f'<p class="cc-why">{cc.get("why","")}</p></div>',
                unsafe_allow_html=True)

        st.caption(f"Confidence: {r.get('confidence','')}")

    # ── Execute ──
    if mock_mode:
        render(MOCK, is_mock=True)
    elif not api_key:
        st.error("Add your Anthropic API key in the sidebar, or enable mock mode.")
    else:
        with st.spinner("Finding your best trip…"):
            try:
                render(call_claude(api_key, build_data()))
            except json.JSONDecodeError as e:
                st.error(f"Unexpected response from Claude: {e}")
            except anthropic.AuthenticationError:
                st.error("Invalid API key — check console.anthropic.com")
            except anthropic.APIError as e:
                st.error(f"API error: {e}")
            except Exception as e:
                st.error(f"Something went wrong: {e}")


# ─────────────────────────────────────────────
#  NAV + ROUTER
# ─────────────────────────────────────────────

# Title sits on its own line — clean and full width
st.markdown("# AI Loyalty Optimizer")

# Nav tabs rendered as inline buttons on one row below the title
nav_col1, nav_col2, nav_spacer = st.columns([1.4, 1.4, 4])
with nav_col1:
    if st.button("My Profile", key="nav_profile", use_container_width=True,
                 type="primary" if st.session_state.page == "profile" else "secondary"):
        st.session_state.page = "profile"
        st.rerun()
with nav_col2:
    if st.button("Plan a Trip", key="nav_trip", use_container_width=True,
                 type="primary" if st.session_state.page == "trip" else "secondary"):
        st.session_state.page = "trip"
        st.rerun()

st.markdown(
    "<hr style='margin:.5rem 0 1.5rem;border:none;border-top:1px solid #e8e8e8;'>",
    unsafe_allow_html=True)

if st.session_state.page == "profile":
    page_profile()
else:
    page_trip()
