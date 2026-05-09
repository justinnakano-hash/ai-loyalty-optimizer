import streamlit as st
import anthropic
import json
import re
from datetime import date, timedelta
from metadata_refresh import load_metadata, is_stale, refresh_metadata, save_metadata

# ── Load shared metadata (cached 24h, zero per-user cost) ──
@st.cache_data(ttl=86400)  # 24 hours
def get_metadata():
    return load_metadata()

META = get_metadata()

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

        # ── Metadata status ──
        gen_at = META.get("generated_at", "not yet generated")
        if gen_at == "not-yet-refreshed":
            st.warning("Market data not loaded. Run `python metadata_refresh.py` once to populate.")
        else:
            st.caption(f"Market data: {gen_at[:10]}")
            if is_stale():
                if st.button("Refresh market data", use_container_width=True):
                    with st.spinner("Refreshing…"):
                        try:
                            data = refresh_metadata()
                            save_metadata(data)
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Refresh failed: {e}")
        st.divider()

        # ── What to search ──
        st.markdown("### What are you planning?")
        search_scope = st.radio(
            "Optimize for",
            ["Flight + Hotel", "Flight only", "Hotel only"],
            horizontal=True, key="search_scope")
        include_flight = search_scope in ["Flight + Hotel", "Flight only"]
        include_hotel  = search_scope in ["Flight + Hotel", "Hotel only"]

        st.divider()

        # ── Flight options ──
        if include_flight:
            st.markdown("### Flight")

            trip_type = st.radio(
                "Trip type", ["Round trip", "One way"],
                horizontal=True, key="trip_type")
            is_roundtrip = trip_type == "Round trip"

            origin_label = st.selectbox(
                "Flying from", AIRPORT_LABELS,
                index=AIRPORT_LABELS.index("San Francisco, CA — SFO (SFO)"),
                key="origin_sel")
            origin_code = AIRPORTS[origin_label]
            origin_city = origin_label.split(" —")[0]
            st.caption(f"Airport: **{origin_code}**")

            dest_label = st.selectbox(
                "Flying to", AIRPORT_LABELS,
                index=AIRPORT_LABELS.index("Tokyo — Narita (NRT)"),
                key="dest_sel")
            dest_code = AIRPORTS[dest_label]
            dest_city = dest_label.split(" —")[0]
            st.caption(f"Airport: **{dest_code}**")

            cabin = st.selectbox("Cabin class",
                                 ["Economy", "Premium Economy", "Business", "First"],
                                 key="cabin_sel")

            # ── Date picker ──
            st.markdown("**Departure date**")
            depart_date = st.date_input(
                "Departure", value=date(2026, 6, 10),
                min_value=date.today(),
                label_visibility="collapsed", key="depart_date")

            if is_roundtrip:
                st.markdown("**Return date**")
                return_date = st.date_input(
                    "Return",
                    value=depart_date + timedelta(days=10),
                    min_value=depart_date + timedelta(days=1),
                    label_visibility="collapsed", key="return_date")
                flight_nights = (return_date - depart_date).days
                st.caption(f"{flight_nights} nights away")
            else:
                return_date  = None
                flight_nights = None

        else:
            # Defaults when flight not selected
            origin_city = ""; origin_code = ""
            dest_city   = ""; dest_code   = ""
            cabin = "Economy"
            depart_date   = date.today()
            return_date   = None
            flight_nights = None
            is_roundtrip  = False

        st.divider()

        # ── Hotel options ──
        if include_hotel:
            st.markdown("### Hotel")
            hotel_style = st.selectbox("Hotel style",
                                       ["Budget", "Standard", "Luxury"],
                                       key="hotel_style_sel")

            if include_flight and is_roundtrip:
                # Auto-fill nights from flight dates
                hotel_nights = flight_nights
                st.caption(f"Staying **{hotel_nights} nights** (matches your flight dates)")
            elif include_flight and not is_roundtrip:
                hotel_nights = st.number_input(
                    "Nights", min_value=1, max_value=60, value=5,
                    key="hotel_nights_input")
            else:
                # Hotel only — need own date range
                st.markdown("**Check-in date**")
                checkin_date = st.date_input(
                    "Check-in", value=date(2026, 6, 10),
                    min_value=date.today(),
                    label_visibility="collapsed", key="checkin_date")
                st.markdown("**Check-out date**")
                checkout_date = st.date_input(
                    "Check-out",
                    value=checkin_date + timedelta(days=5),
                    min_value=checkin_date + timedelta(days=1),
                    label_visibility="collapsed", key="checkout_date")
                hotel_nights = (checkout_date - checkin_date).days
                depart_date  = checkin_date
                st.caption(f"{hotel_nights} nights")

                # For hotel-only, ask destination city
                if not include_flight:
                    dest_label = st.selectbox(
                        "Destination city", AIRPORT_LABELS,
                        index=AIRPORT_LABELS.index("Tokyo — Narita (NRT)"),
                        key="hotel_dest_sel")
                    dest_city = dest_label.split(" —")[0]
                    dest_code = AIRPORTS[dest_label]
        else:
            hotel_style  = "Standard"
            hotel_nights = None

        st.divider()

        # ── Shared preference ──
        val_exp = st.slider("Value ← · → Experience", 1, 10, 5,
                            help="1 = maximize points value  ·  10 = maximize experience quality")

        st.divider()
        run = st.button("Find My Best Trip", type="primary", use_container_width=True)

        # Build a clean date summary string for the prompt
        if include_flight and is_roundtrip:
            dates_str = f"{depart_date.strftime('%b %d')} – {return_date.strftime('%b %d, %Y')}"
        elif include_flight:
            dates_str = f"{depart_date.strftime('%b %d, %Y')} (one way)"
        elif include_hotel:
            dates_str = f"{depart_date.strftime('%b %d')} – {(depart_date + timedelta(days=hotel_nights)).strftime('%b %d, %Y')}"
        else:
            dates_str = ""

        nights = hotel_nights if hotel_nights else (flight_nights or 0)

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
        st.info("Configure your trip in the sidebar — choose flight, hotel, or both — then click **Find My Best Trip**.")
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
                "origin":        f"{origin_city} ({origin_code})" if origin_city else "",
                "destination":   f"{dest_city} ({dest_code})" if dest_city else "",
                "dates":         dates_str,
                "nights":        int(nights) if nights else 0,
                "trip_type":     "Round trip" if is_roundtrip else "One way",
                "include_flight": include_flight,
                "include_hotel":  include_hotel,
            },
            "preferences": {
                "cabin":               cabin if include_flight else "N/A",
                "hotel_style":         hotel_style if include_hotel else "N/A",
                "value_vs_experience": val_exp,
            },
        }

    SYSTEM = ("You are an expert travel strategist. "
              "Return ONLY valid JSON, no markdown, no extra text.")

    def build_prompt(d):
        scope = []
        if include_flight: scope.append("flight")
        if include_hotel:  scope.append("hotel")
        scope_str = " and ".join(scope)

        # Pull relevant metadata to inject — keeps prompt focused
        cpp_data    = json.dumps(META.get("point_valuations", {}),  indent=2)
        xfr_data    = json.dumps(META.get("transfer_partners", {}), indent=2)
        promos      = json.dumps(META.get("promotions", []),         indent=2)
        benchmarks  = json.dumps(META.get("cash_rate_benchmarks", {}), indent=2)
        thresholds  = json.dumps(META.get("cpp_thresholds", {}),    indent=2)

        return f"""Generate the optimal {scope_str} loyalty strategy. Use the metadata below to calculate
exact cent-per-point values, identify transfer paths, flag promotions, and decide if cash beats points.

USER PROFILE & TRIP:
{json.dumps(d, indent=2)}

CURRENT POINT VALUATIONS (cpp = cents per point at best redemption):
{cpp_data}

TRANSFER PARTNERS & RATIOS:
{xfr_data}

ACTIVE PROMOTIONS:
{promos}

CASH RATE BENCHMARKS:
{benchmarks}

CPP DECISION THRESHOLDS:
{thresholds}

Return EXACTLY this JSON (no markdown, no extra text):
{{
  "plain_english": "One friendly sentence summarising the strategy — no jargon",
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
  "confidence": "",
  "points_analysis": {{
    "flight": {{
      "status": "covered|shortfall|not_applicable",
      "required_pts": 0,
      "program_recommended": "",
      "cpp_achieved": 0.0,
      "cpp_alternatives": [
        {{"label":"","cpp":0.0}}
      ],
      "bars": [
        {{"name":"","have":0,"need":0,"pct":0,"color":"","surplus_or_gap":""}}
      ],
      "transfer_options": [
        {{"from_program":"","to_program":"","ratio":"","have":0,"need":0,"feasible":true}}
      ]
    }},
    "hotel": {{
      "status": "covered|shortfall|not_applicable",
      "required_pts": 0,
      "program_recommended": "",
      "cpp_achieved": 0.0,
      "cpp_alternatives": [
        {{"label":"","cpp":0.0}}
      ],
      "bars": [
        {{"name":"","have":0,"need":0,"pct":0,"color":"","surplus_or_gap":""}}
      ],
      "transfer_options": [
        {{"from_program":"","to_program":"","ratio":"","have":0,"need":0,"feasible":true}}
      ],
      "tip": "Actionable suggestion if shortfall exists"
    }}
  }},
  "cash_vs_points": {{
    "recommendation": "points|cash|similar",
    "points_option": {{
      "out_of_pocket": "e.g. ~$150",
      "pts_used": 0,
      "pts_value_usd": "e.g. ~$1,560",
      "cpp": 0.0
    }},
    "cash_option": {{
      "total_cost": "e.g. $1,240",
      "pts_saved": 0,
      "pts_saved_value": "e.g. ~$1,560",
      "net_vs_points": "e.g. +$320 better"
    }},
    "verdict": "Plain English explanation of which is better and why"
  }},
  "promotions": [
    {{
      "title": "",
      "description": "",
      "type": "transfer_bonus|sale_fare|earn_bonus|status_promo",
      "tags": [],
      "expires": "",
      "relevant_to_this_trip": true
    }}
  ]
}}
Use city names not airport codes. Keep everything friendly. Do NOT assume real-time seat availability.
Use the metadata CPP values and thresholds to make the cash vs points recommendation mathematically."""

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

        # Build dynamic tagline and hero stats based on scope
        tagline_parts = []
        if include_flight:
            tagline_parts.append(f"{cabin} class")
            if is_roundtrip:
                tagline_parts.append("round trip")
            else:
                tagline_parts.append("one way")
        if nights:
            tagline_parts.append(f"{int(nights)} nights")
        tagline_parts.append(dates_str)
        tagline = " &middot; ".join(tagline_parts)

        # Route display
        if include_flight:
            route_html = (
                f'<span>{rd.get("origin", origin_city)}</span>'
                f'<div class="route-line"></div>&rarr;'
                + ('<div class="route-line"></div>&larr;' if is_roundtrip else '')
                + ('<div class="route-line"></div>' if not is_roundtrip else '')
                + f'<span>{rd.get("destination", dest_city)}</span>'
            )
        else:
            route_html = f'<span>Hotel in {rd.get("destination", dest_city)}</span>'

        # Hero stats — only show relevant ones
        stats_html = ""
        if include_flight:
            stats_html += (
                f'<div class="hero-stat">'
                f'<p class="hs-label">Flight</p>'
                f'<p class="hs-val">{hero.get("flight_pts","—")}</p>'
                f'<p class="hs-sub">points used</p></div>'
            )
        if include_hotel:
            stats_html += (
                f'<div class="hero-stat">'
                f'<p class="hs-label">Hotel</p>'
                f'<p class="hs-val">{hero.get("hotel_nights","—")}</p>'
                f'<p class="hs-sub">award nights</p></div>'
            )
        stats_html += (
            f'<div class="hero-stat">'
            f'<p class="hs-label">Cash needed</p>'
            f'<p class="hs-val">{hero.get("cash","—")}</p>'
            f'<p class="hs-sub">taxes &amp; fees</p></div>'
        )

        st.markdown(
            f'<div class="hero"><div class="hero-top">'
            f'<div class="route">{route_html}</div>'
            f'<p class="tagline">{tagline}</p>'
            f'</div><div class="hero-bottom">{stats_html}</div></div>',
            unsafe_allow_html=True)

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
        cards = []
        if include_flight:
            cards.append(
                f'<div class="res-card"><p class="card-head">Flight</p>'
                f'<div class="dr"><span class="dr-l">Airline</span><span class="dr-v">{f.get("airline","—")}</span></div>'
                f'<div class="dr"><span class="dr-l">Book through</span><span class="dr-v">{f.get("book_via","—")}</span></div>'
                f'<div class="dr"><span class="dr-l">Points used</span><span class="dr-v">{f.get("points","—")}</span></div>'
                f'<div class="dr"><span class="dr-l">Cash fees</span><span class="dr-v">{f.get("cash_fees","—")}</span></div>'
                f'</div>'
            )
        if include_hotel:
            cards.append(
                f'<div class="res-card"><p class="card-head">Hotel</p>'
                f'<div class="dr"><span class="dr-l">Property</span><span class="dr-v">{h.get("name","—")}</span></div>'
                f'<div class="dr"><span class="dr-l">Book through</span><span class="dr-v">{h.get("book_via","—")}</span></div>'
                f'<div class="dr"><span class="dr-l">Points used</span><span class="dr-v">{h.get("points","—")}</span></div>'
                f'<div class="dr"><span class="dr-l">5th night</span><span class="dr-v">{h.get("fifth_night","—")}</span></div>'
                f'</div>'
            )
        if len(cards) == 2:
            c1, c2 = st.columns(2)
            with c1: st.markdown(cards[0], unsafe_allow_html=True)
            with c2: st.markdown(cards[1], unsafe_allow_html=True)
        elif len(cards) == 1:
            st.markdown(cards[0], unsafe_allow_html=True)

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

        # ── Points gap analysis ──
        pa = r.get("points_analysis", {})
        if pa:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                '<p style="font-size:11px;font-weight:700;color:#999;text-transform:uppercase;'
                'letter-spacing:.06em;margin:0 0 8px;">Points gap analysis</p>',
                unsafe_allow_html=True)
            for section_key, section_label in [("flight","Flight"), ("hotel","Hotel")]:
                sec = pa.get(section_key, {})
                if not sec or sec.get("status") == "not_applicable":
                    continue
                status    = sec.get("status","")
                pill_html = {
                    "covered":  '<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:500;background:#e6f4ea;color:#1e5c2a;">&#10003; Covered</span>',
                    "shortfall":'<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:500;background:#fff3e0;color:#7a5700;">&#9650; Shortfall</span>',
                }.get(status, "")
                # Bars
                bars_html = ""
                for b in sec.get("bars", []):
                    pct  = min(int(b.get("pct", 0)), 100)
                    sg   = b.get("surplus_or_gap","")
                    sg_c = "#1e5c2a" if "+" in sg else "#cc3333"
                    bars_html += (
                        f'<div style="margin-bottom:12px;">'
                        f'<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
                        f'<span style="font-size:12px;font-weight:500;color:#111;">{b.get("name","")}</span>'
                        f'<span style="font-size:11px;color:#888;">{b.get("have",0):,} pts available</span>'
                        f'</div>'
                        f'<div style="height:9px;background:#f0f0f0;border-radius:5px;position:relative;">'
                        f'<div style="position:absolute;height:100%;width:{pct}%;background:{b.get("color","#378ADD")};border-radius:5px;"></div>'
                        f'</div>'
                        f'<div style="display:flex;justify-content:space-between;margin-top:3px;">'
                        f'<span style="font-size:11px;color:#888;">Need {b.get("need",0):,} pts</span>'
                        f'<span style="font-size:11px;font-weight:500;color:{sg_c};">{sg}</span>'
                        f'</div></div>'
                    )
                # CPP alternatives
                cpp_html = ""
                best_cpp = max((c.get("cpp",0) for c in sec.get("cpp_alternatives",[])), default=0)
                for c in sec.get("cpp_alternatives",[]):
                    is_best = c.get("cpp",0) == best_cpp
                    bg  = "#e6f4ea" if is_best else "#f7f7f7"
                    fc  = "#1e5c2a" if is_best else "#555"
                    badge = '<span style="font-size:9px;font-weight:700;color:#1e5c2a;text-transform:uppercase;letter-spacing:.04em;display:block;">Best value</span>' if is_best else ""
                    cpp_html += (
                        f'<div style="flex:1;background:{bg};border-radius:8px;padding:.65rem .85rem;">'
                        f'{badge}'
                        f'<p style="font-size:11px;color:{fc};margin:0 0 2px;">{c.get("label","")}</p>'
                        f'<p style="font-size:18px;font-weight:500;color:{fc};margin:0;">{c.get("cpp",0):.1f}¢/pt</p>'
                        f'</div>'
                    )
                # Transfer options
                xfr_html = ""
                for x in sec.get("transfer_options",[]):
                    ok  = x.get("feasible", False)
                    fc  = "#1e5c2a" if ok else "#cc3333"
                    xfr_html += (
                        f'<div style="display:flex;align-items:center;gap:8px;padding:6px 0;'
                        f'border-bottom:0.5px solid #f0f0f0;font-size:12px;">'
                        f'<span style="font-weight:500;color:#111;flex:1.3;">{x.get("from_program","")}</span>'
                        f'<span style="color:#bbb;">→</span>'
                        f'<span style="color:#111;flex:1.3;">{x.get("to_program","")}</span>'
                        f'<span style="color:#888;flex:.6;text-align:center;">{x.get("ratio","")}</span>'
                        f'<span style="font-weight:500;color:{fc};flex:1;text-align:right;">'
                        f'Need {x.get("need",0):,} · have {x.get("have",0):,}</span>'
                        f'</div>'
                    )
                tip_html = ""
                if sec.get("tip"):
                    tip_html = (
                        f'<div style="margin:.75rem 0 0;padding:.65rem .9rem;background:#fff8e6;'
                        f'border-radius:8px;font-size:12px;color:#7a5700;line-height:1.5;">'
                        f'<strong>Tip:</strong> {sec["tip"]}</div>'
                    )
                st.markdown(
                    f'<div style="background:#fff;border:0.5px solid #e8e8e8;border-radius:12px;'
                    f'overflow:hidden;margin-bottom:.75rem;">'
                    f'<div style="padding:.9rem 1.1rem;border-bottom:0.5px solid #e8e8e8;'
                    f'display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">'
                    f'<div><p style="font-size:14px;font-weight:500;color:#111;margin:0 0 2px;">'
                    f'{section_label} — {sec.get("program_recommended","")}</p>'
                    f'<p style="font-size:12px;color:#888;margin:0;">Need {sec.get("required_pts",0):,} pts</p>'
                    f'</div>{pill_html}</div>'
                    f'<div style="padding:.9rem 1.1rem;">{bars_html}</div>'
                    f'{"<div style=padding:0 1.1rem .9rem;><p style=font-size:11px;font-weight:500;color:#888;margin:0 0 6px;>Transfer options to close the gap</p>" + xfr_html + "</div>" if xfr_html else ""}'
                    f'<div style="display:flex;gap:8px;padding:.75rem 1.1rem;'
                    f'border-top:0.5px solid #e8e8e8;">{cpp_html}</div>'
                    f'{tip_html}'
                    f'</div>',
                    unsafe_allow_html=True)

        # ── Cash vs Points ──
        cvp = r.get("cash_vs_points", {})
        if cvp:
            rec  = cvp.get("recommendation","")
            po   = cvp.get("points_option",{})
            co   = cvp.get("cash_option",{})
            pts_winner  = rec == "points"
            cash_winner = rec == "cash"
            def cmp_card(winner, label, main_val, main_sub, details, badge="Better deal"):
                bdr   = "2px solid #3B6D11" if winner else "0.5px solid #e8e8e8"
                bdge  = f'<span style="font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;background:#e6f4ea;color:#1e5c2a;">{badge}</span>' if winner else ""
                rows  = "".join(
                    f'<div style="display:flex;justify-content:space-between;font-size:12px;color:#888;margin-bottom:2px;">'
                    f'<span>{k}</span><span style="font-weight:500;color:#111;">{v}</span></div>'
                    for k,v in details.items())
                return (
                    f'<div style="flex:1;border:{bdr};border-radius:12px;padding:.9rem 1.1rem;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                    f'<span style="font-size:12px;font-weight:500;color:#888;text-transform:uppercase;letter-spacing:.04em;">{label}</span>{bdge}</div>'
                    f'<p style="font-size:22px;font-weight:500;color:#111;margin-bottom:2px;">{main_val}</p>'
                    f'<p style="font-size:12px;color:#888;margin-bottom:10px;">{main_sub}</p>'
                    f'<div style="border-top:0.5px solid #f0f0f0;padding-top:8px;">{rows}</div>'
                    f'</div>'
                )
            pts_card  = cmp_card(
                pts_winner, "Burn points",
                po.get("out_of_pocket","—"), "out of pocket",
                {"Points used": f'{po.get("pts_used",0):,}',
                 "Points value": po.get("pts_value_usd","—"),
                 "Effective CPP": f'{po.get("cpp",0):.1f}¢'})
            cash_card = cmp_card(
                cash_winner, "Pay cash",
                co.get("total_cost","—"), "total cost",
                {"Points saved": f'{co.get("pts_saved",0):,}',
                 "Points kept value": co.get("pts_saved_value","—"),
                 "Net vs points": co.get("net_vs_points","—")})
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                '<p style="font-size:11px;font-weight:700;color:#999;text-transform:uppercase;'
                'letter-spacing:.06em;margin:0 0 8px;">Cash vs points</p>',
                unsafe_allow_html=True)
            st.markdown(
                f'<div style="display:flex;gap:.75rem;margin-bottom:.75rem;">{pts_card}{cash_card}</div>',
                unsafe_allow_html=True)
            if cvp.get("verdict"):
                st.markdown(
                    f'<div style="background:#f7f7f7;border-radius:8px;padding:.75rem 1rem;'
                    f'font-size:13px;color:#555;line-height:1.6;">{cvp["verdict"]}</div>',
                    unsafe_allow_html=True)

        # ── Active promotions ──
        promos = r.get("promotions", [])
        relevant = [p for p in promos if p.get("relevant_to_this_trip", True)]
        if relevant:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                '<p style="font-size:11px;font-weight:700;color:#999;text-transform:uppercase;'
                'letter-spacing:.06em;margin:0 0 8px;">Active promotions worth knowing</p>',
                unsafe_allow_html=True)
            for p in relevant:
                tags_html = "".join(
                    f'<span style="font-size:11px;padding:2px 8px;border-radius:20px;'
                    f'background:#e8f0fe;color:#1a56cc;margin-right:4px;">{t}</span>'
                    for t in p.get("tags",[]))
                expires = f'<p style="font-size:11px;color:#bbb;margin:5px 0 0;">Expires: {p["expires"]}</p>' if p.get("expires") else ""
                st.markdown(
                    f'<div style="border:0.5px solid #e8e8e8;border-radius:12px;'
                    f'padding:.9rem 1.1rem;margin-bottom:.5rem;display:flex;gap:12px;">'
                    f'<div style="width:34px;height:34px;border-radius:8px;background:#e8f0fe;'
                    f'display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:16px;">&#9889;</div>'
                    f'<div><p style="font-size:13px;font-weight:500;color:#111;margin:0 0 3px;">{p.get("title","")}</p>'
                    f'<p style="font-size:12px;color:#666;margin:0 0 6px;line-height:1.5;">{p.get("description","")}</p>'
                    f'{tags_html}{expires}</div></div>',
                    unsafe_allow_html=True)

        # ── Metadata freshness note ──
        gen_at = META.get("generated_at","unknown")
        st.caption(f"Market data refreshed: {gen_at[:10] if len(gen_at) > 9 else gen_at}")

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
