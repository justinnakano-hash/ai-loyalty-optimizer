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

# META is loaded at render time via get_metadata() — not at module level
# This ensures st.cache_data.clear() + st.rerun() picks up fresh data.

st.set_page_config(
    page_title="AI Loyalty Optimizer",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ══ HIDE STREAMLIT CHROME ══ */
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"],header[data-testid="stHeader"] { display:none!important; }

/* ══ BASE ══ */
.block-container { padding-top:.75rem!important; }

/* ══ DESKTOP NAV TAB UNDERLINE STYLE ══ */
.nav-tab-bar { display:flex; gap:0; border-bottom:1px solid #e8e8e8; margin-bottom:1rem; }
.nav-tab { flex:0; padding:10px 20px; font-size:14px; font-weight:500; color:#888;
           cursor:pointer; border-bottom:2px solid transparent; white-space:nowrap; }
.nav-tab.active { color:#111; border-bottom-color:#111; }

/* ══ RESULT CARDS ══ */
.plain-english { background:#f0faf0; border-radius:10px; padding:.9rem 1.1rem;
    font-size:14px; color:#1e5c2a; line-height:1.65; margin-bottom:1rem; }
.hero { border:1px solid #e8e8e8; border-radius:12px; overflow:hidden; margin-bottom:1rem; }
.hero-top { padding:1rem 1.25rem; }
.route { font-size:17px; font-weight:600; color:#111; display:flex;
    align-items:center; gap:10px; margin-bottom:4px; flex-wrap:wrap; }
.route-line { flex:1; min-width:16px; height:1px; background:#ddd; }
.tagline { font-size:13px; color:#666; }
.hero-bottom { display:grid; grid-template-columns:1fr 1fr 1fr; border-top:1px solid #e8e8e8; }
.hero-stat { padding:.8rem 1rem; border-right:1px solid #e8e8e8; }
.hero-stat:last-child { border-right:none; }
.hs-label { font-size:10px; color:#999; text-transform:uppercase; letter-spacing:.05em; margin-bottom:3px; }
.hs-val   { font-size:15px; font-weight:600; color:#111; }
.hs-sub   { font-size:11px; color:#888; margin-top:2px; }
.pts-wrap { background:#fff; border:1px solid #e8e8e8; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem; }
.pts-title { font-size:11px; font-weight:600; color:#999; text-transform:uppercase;
    letter-spacing:.05em; margin-bottom:10px; }
.pts-row  { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
.pts-name { font-size:12px; color:#111; min-width:110px; }
.pts-track{ flex:1; height:8px; background:#f0f0f0; border-radius:4px; overflow:hidden; }
.pts-fill { height:100%; border-radius:4px; }
.pts-amt  { font-size:11px; color:#888; min-width:80px; text-align:right; }
.legend   { display:flex; flex-wrap:wrap; gap:12px; margin-top:8px; }
.legend-item { font-size:11px; color:#999; display:flex; align-items:center; gap:5px; }
.legend-dot  { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.res-card { background:#fff; border:1px solid #e8e8e8; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem; }
.card-head { font-size:11px; font-weight:600; color:#999; text-transform:uppercase;
    letter-spacing:.05em; margin-bottom:10px; }
.dr { display:flex; justify-content:space-between; padding:6px 0;
    border-bottom:1px solid #f0f0f0; font-size:13px; gap:8px; }
.dr:last-child { border-bottom:none; }
.dr-l { color:#666; flex-shrink:0; }
.dr-v { font-weight:500; color:#111; text-align:right; }
.perks-row { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:1rem; }
.chip { background:#f5f5f5; border:1px solid #e8e8e8; border-radius:20px;
    padding:4px 11px; font-size:12px; color:#555; }
.steps-card { background:#fff; border:1px solid #e8e8e8; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem; }
.step { display:flex; gap:12px; padding:9px 0; border-bottom:1px solid #f5f5f5; align-items:flex-start; }
.step:last-child { border-bottom:none; }
.step-num { width:24px; height:24px; min-width:24px; border-radius:50%;
    background:#e8f0fe; display:flex; align-items:center; justify-content:center;
    font-size:12px; font-weight:600; color:#1a56cc; }
.step-title { font-size:13px; font-weight:600; color:#111; margin-bottom:2px; }
.step-desc  { font-size:12px; color:#666; line-height:1.5; }
.alt-chip { background:#f7f7f7; border:1px solid #e8e8e8; border-radius:10px;
    padding:.7rem 1rem; margin-bottom:8px; }
.alt-name  { font-size:13px; font-weight:600; color:#111; margin-bottom:3px; }
.alt-desc  { font-size:12px; color:#555; margin-bottom:3px; }
.alt-trade { font-size:12px; color:#aaa; }
.cc-wrap { background:#f0f7ff; border:2px solid #a8d0f5; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem; }
.cc-eye  { font-size:11px; color:#1a56cc; font-weight:600; text-transform:uppercase;
    letter-spacing:.05em; margin-bottom:6px; }
.cc-name { font-size:14px; font-weight:600; color:#111; margin-bottom:4px; }
.cc-bonus{ font-size:13px; color:#2d7a3a; margin-bottom:6px; }
.cc-why  { font-size:13px; color:#555; }
.mock-banner { background:#fff8e6; border:1px solid #ffe082; border-radius:8px;
    padding:.6rem 1rem; font-size:13px; color:#7a5700; margin-bottom:1rem; }

/* ══ PROFILE ROWS ══ */
.prog-row { padding:8px 0; border-bottom:1px solid #f5f5f5; }
.prog-row-inner { display:flex; align-items:flex-start; gap:8px; }
.prog-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; margin-top:5px; }
.prog-name { font-size:13px; font-weight:600; color:#111; flex:1; }
.prog-bal  { font-size:13px; color:#555; margin-right:8px; white-space:nowrap; }
.prog-pill { display:inline-block; padding:2px 8px; border-radius:20px;
    font-size:11px; font-weight:500; white-space:nowrap; }

/* ══ MOBILE ══ */
@media (max-width:768px) {
    /* Hide Streamlit sidebar entirely on mobile */
    [data-testid="stSidebar"]       { display:none!important; }
    [data-testid="collapsedControl"] { display:none!important; }
    .block-container { padding-left:.75rem!important; padding-right:.75rem!important;
                       padding-top:.5rem!important; max-width:100%!important; }

    /* Tab bar — slim, centered */
    .nav-tab { padding:9px 14px; font-size:13px; }

    /* Hero stats 2-col on narrow */
    .hero-bottom { grid-template-columns:1fr 1fr; }
    .hero-stat:nth-child(odd)  { border-right:1px solid #e8e8e8; }
    .hero-stat:nth-child(even) { border-right:none; }
    .hero-stat { border-bottom:1px solid #e8e8e8; }
    .hero-stat:nth-last-child(-n+2) { border-bottom:none; }

    /* Points name shorter */
    .pts-name { min-width:80px; font-size:11px; }
    .pts-amt  { min-width:60px; font-size:11px; }
}
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
if "profile"     not in st.session_state: st.session_state.profile     = {}
if "page"        not in st.session_state: st.session_state.page        = "profile"
if "editing"     not in st.session_state: st.session_state.editing     = None
if "admin_authed" not in st.session_state: st.session_state.admin_authed = False
if "mock_override" not in st.session_state: st.session_state.mock_override = None  # None | True | False

# ── Handle nav query param FIRST — before any page renders ──
# The hamburger menu posts ?nav=profile/trip/admin
_nav_qp = st.query_params.get("nav", None)
if _nav_qp in ("profile", "trip", "admin"):
    st.session_state.page = _nav_qp
    st.query_params.clear()
    st.rerun()

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
    st.caption("Set up once — reused for every trip.")

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
                    # ── View row — two-line layout survives narrow screens ──
                    is_active = status not in ["None", "Standard"]
                    pill_bg   = "#e6f4ea" if is_active else "#f0f0f0"
                    pill_col  = "#1e5c2a" if is_active else "#666"

                    r_info, r_edit, r_del = st.columns([7, 1, 1])
                    with r_info:
                        st.markdown(
                            f'<div style="padding:8px 0;border-bottom:1px solid #f5f5f5;">'
                            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:2px;">'
                            f'<span style="width:8px;height:8px;border-radius:50%;'
                            f'background:{color};flex-shrink:0;display:inline-block;"></span>'
                            f'<span style="font-size:13px;font-weight:600;color:#111;'
                            f'flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;'
                            f'white-space:nowrap;">{prog_name}</span>'
                            f'</div>'
                            f'<div style="display:flex;align-items:center;gap:6px;'
                            f'padding-left:16px;">'
                            f'<span style="font-size:12px;color:#555;">{bal:,} pts</span>'
                            f'<span style="display:inline-block;padding:1px 8px;'
                            f'border-radius:20px;font-size:11px;font-weight:500;'
                            f'background:{pill_bg};color:{pill_col};">{status}</span>'
                            f'</div></div>',
                            unsafe_allow_html=True)
                    with r_edit:
                        if st.button("✎", key=f"edit_{prog_name}",
                                     use_container_width=True,
                                     help=f"Edit {prog_name}"):
                            st.session_state.editing = prog_name
                            st.rerun()
                    with r_del:
                        if st.button("✕", key=f"del_{prog_name}",
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
    st.markdown("<hr style='margin:.5rem 0 .5rem;border:none;border-top:1px solid #f0f0f0;'>", unsafe_allow_html=True)
    st.markdown("**Add a program**")

    already_added = set(profile.keys())

    r1a, r1b = st.columns(2)
    with r1a:
        add_cat = st.selectbox("Category", list(PROGRAMS.keys()), key="add_cat")
    available = [p for p in PROGRAMS[add_cat] if p not in already_added]
    with r1b:
        if available:
            add_prog = st.selectbox("Program", available, key="add_prog")
        else:
            st.selectbox("Program", ["— all added —"], disabled=True, key="add_prog_dis")
            add_prog = None

    r2a, r2b = st.columns(2)
    with r2a:
        add_bal = st.number_input("Balance (pts)", min_value=0, step=1000,
                                  value=0, key="add_bal")
    with r2b:
        if add_prog:
            add_status = st.selectbox(
                "Status", PROGRAMS[add_cat][add_prog]["statuses"], key="add_status")
        else:
            st.selectbox("Status", ["—"], disabled=True, key="add_status_dis")
            add_status = None

    if st.button("+ Add program", use_container_width=True, type="primary",
                 disabled=not add_prog, key="add_btn"):
        st.session_state.profile[add_prog] = {
            "balance": add_bal, "status": add_status}
        st.rerun()


# ─────────────────────────────────────────────
#  PAGE: PLAN A TRIP
# ─────────────────────────────────────────────
def page_trip():
    profile = st.session_state.profile

    # API key from secrets only
    def get_api_key():
        try:    return st.secrets["admin"]["api_key"]
        except: return None
    api_key = get_api_key()

    # Mock mode — admin override or auto based on key presence
    _override = st.session_state.get("mock_override", None)
    mock_mode = _override if _override is not None else (api_key is None)

    if not profile:
        st.warning("Your loyalty profile is empty. Go to **My Profile** and add your programs first.")
        return

    # ── Compact status line ──
    gen_at    = get_metadata().get("generated_at", "")
    total_pts = sum(e["balance"] for e in profile.values())
    elite_ct  = sum(1 for e in profile.values() if e["status"] not in ["None","Standard"])
    prog_ct   = len(profile)
    _status_note = "Preview mode" if mock_mode else (f"Market data: {gen_at[:10]}" if gen_at and gen_at != "not-yet-refreshed" else "Market data not loaded")
    st.markdown(
        f'<div style="font-size:12px;color:#888;margin-bottom:.5rem;">' 
        f'<b>{prog_ct}</b> programs &nbsp;·&nbsp; <b>{total_pts:,}</b> pts &nbsp;·&nbsp; ' 
        f'<b>{elite_ct}</b> elite &nbsp;·&nbsp; {_status_note}</div>',
        unsafe_allow_html=True)

    # ════════════════════════════════════════
    #  TRIP INPUTS — sidebar (always reliable)
    # ════════════════════════════════════════
    with st.sidebar:

        # Scope
        scope_options = ["Flight + Hotel", "Flight only", "Hotel only"]
        search_scope = st.radio(
            "Optimize for", scope_options, horizontal=True,
            index=scope_options.index(
                st.session_state.get("trip_scope", "Flight + Hotel")),
            key="search_scope")
        include_flight = search_scope in ["Flight + Hotel", "Flight only"]
        include_hotel  = search_scope in ["Flight + Hotel", "Hotel only"]
        st.divider()

        # Defaults
        origin_city = origin_code = dest_city = dest_code = ""
        cabin = "Economy"; hotel_style = "Standard"
        depart_date = date(2026, 6, 10); return_date = None
        flight_nights = hotel_nights = None; is_roundtrip = True

        if include_flight:
            st.markdown("**Flight**")
            trip_type = st.radio(
                "Trip type", ["Round trip", "One way"], horizontal=True,
                key="form_trip_type")
            is_roundtrip = trip_type == "Round trip"

            fc1, fc2 = st.columns(2)
            with fc1:
                orig_default = st.session_state.get("origin_label", "San Francisco, CA — SFO (SFO)")
                orig_idx = AIRPORT_LABELS.index(orig_default) if orig_default in AIRPORT_LABELS else 0
                origin_label = st.selectbox("From", AIRPORT_LABELS, index=orig_idx, key="form_orig")
                origin_code  = AIRPORTS[origin_label]
                origin_city  = origin_label.split(" —")[0]
            with fc2:
                dest_default = st.session_state.get("dest_label", "Tokyo — Narita (NRT)")
                dest_idx = AIRPORT_LABELS.index(dest_default) if dest_default in AIRPORT_LABELS else 1
                dest_label = st.selectbox("To", AIRPORT_LABELS, index=dest_idx, key="form_dest")
                dest_code  = AIRPORTS[dest_label]
                dest_city  = dest_label.split(" —")[0]

            cabin = st.selectbox("Cabin class",
                ["Economy", "Premium Economy", "Business", "First"], key="form_cabin")

            if is_roundtrip:
                dc1, dc2 = st.columns(2)
                with dc1:
                    depart_date = st.date_input("Depart", value=date(2026, 6, 10),
                        min_value=date.today(), key="form_depart")
                with dc2:
                    return_date = st.date_input("Return",
                        value=date(2026, 6, 20),
                        min_value=depart_date + timedelta(days=1), key="form_return")
                flight_nights = (return_date - depart_date).days
                st.caption(f"{flight_nights} nights")
            else:
                depart_date = st.date_input("Departure", value=date(2026, 6, 10),
                    min_value=date.today(), key="form_depart_ow")

        if include_hotel:
            if include_flight:
                st.divider()
            st.markdown("**Hotel**")
            if not include_flight:
                dest_default = st.session_state.get("dest_label", "Tokyo — Narita (NRT)")
                dest_idx = AIRPORT_LABELS.index(dest_default) if dest_default in AIRPORT_LABELS else 1
                dest_label = st.selectbox("Destination", AIRPORT_LABELS,
                    index=dest_idx, key="form_hotel_dest")
                dest_city = dest_label.split(" —")[0]
                dest_code = AIRPORTS[dest_label]
                hc1, hc2 = st.columns(2)
                with hc1:
                    checkin_date = st.date_input("Check-in", value=date(2026, 6, 10),
                        min_value=date.today(), key="form_checkin")
                with hc2:
                    checkout_date = st.date_input("Check-out", value=date(2026, 6, 15),
                        min_value=checkin_date + timedelta(days=1), key="form_checkout")
                hotel_nights = (checkout_date - checkin_date).days
                depart_date  = checkin_date
            elif is_roundtrip and flight_nights:
                hotel_nights = flight_nights
                st.caption(f"Staying {hotel_nights} nights — matches flight")
            else:
                hotel_nights = st.number_input("Nights", min_value=1,
                    max_value=60, value=5, key="form_hotel_nights")

            hotel_style = st.selectbox("Hotel style",
                ["Budget", "Standard", "Luxury"], key="form_hotel_style")

        st.divider()
        val_exp = st.slider("Value ←→ Experience", 1, 10,
            st.session_state.get("val_exp", 5), key="form_val_exp",
            help="1 = max value · 10 = max experience")
        st.divider()
        run = st.button("🔍 Find My Best Trip", type="primary",
                        use_container_width=True, key="run_btn")
        
        # Status
        gen_at = get_metadata().get("generated_at", "")
        if mock_mode:
            st.caption("Preview mode — sample data")
        elif gen_at and gen_at != "not-yet-refreshed":
            st.caption(f"Market data: {gen_at[:10]}")
    # ── Date summary string ──
    if include_flight and is_roundtrip and return_date:
        dates_str = f"{depart_date.strftime('%b %d')} – {return_date.strftime('%b %d, %Y')}"
    elif include_flight:
        dates_str = f"{depart_date.strftime('%b %d, %Y')} (one way)"
    elif include_hotel and hotel_nights:
        dates_str = f"{depart_date.strftime('%b %d')} – {(depart_date + timedelta(days=hotel_nights)).strftime('%b %d, %Y')}"
    else:
        dates_str = ""

    nights = hotel_nights if hotel_nights else (flight_nights or 0)
    # ── Mobile trip summary card (hidden on desktop via CSS) ──
    _orig_disp = origin_city or "—"
    _dest_disp = dest_city   or "—"
    _dates_disp = dates_str  or "—"
    _scope_disp = search_scope
    _pref_disp  = " · ".join(filter(None, [
        cabin         if include_flight else "",
        hotel_style   if include_hotel  else "",
    ]))
    st.markdown(
        f'''<div class="mobile-trip-card" style="display:none;">
          <div style="background:#fff;border:1px solid #e5e7eb;border-radius:14px;
               overflow:hidden;margin-bottom:.75rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;
                 padding:12px 16px;border-bottom:1px solid #f3f4f6;cursor:pointer;"
                 onclick="document.querySelector('[data-testid=stSidebar]').style.display='block'">
              <span style="font-size:14px;font-weight:600;color:#111;">Optimize for</span>
              <span style="font-size:13px;color:#555;">{_scope_disp}</span>
            </div>
            <div style="padding:12px 16px;border-bottom:1px solid #f3f4f6;">
              <div style="font-size:14px;font-weight:600;color:#111;margin-bottom:6px;">Route</div>
              <div style="font-size:13px;color:#555;">{_orig_disp} → {_dest_disp}</div>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;
                 padding:12px 16px;border-bottom:1px solid #f3f4f6;">
              <span style="font-size:14px;font-weight:600;color:#111;">Dates</span>
              <span style="font-size:13px;color:#555;">{_dates_disp}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;
                 padding:12px 16px;">
              <span style="font-size:14px;font-weight:600;color:#111;">Preferences</span>
              <span style="font-size:13px;color:#555;">{_pref_disp}</span>
            </div>
          </div>
        </div>
        <style>@media(max-width:768px){{.mobile-trip-card{{display:block!important;}}}}</style>
        ''',
        unsafe_allow_html=True)

    if not run:
        st.caption("Configure your trip in the sidebar, then click **Find My Best Trip**.")
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

        cpp_data    = json.dumps(get_metadata().get("point_valuations", {}),  indent=2)
        xfr_data    = json.dumps(get_metadata().get("transfer_partners", {}), indent=2)
        promos      = json.dumps(get_metadata().get("promotions", []),         indent=2)
        benchmarks  = json.dumps(get_metadata().get("cash_rate_benchmarks", {}), indent=2)
        thresholds  = json.dumps(get_metadata().get("cpp_thresholds", {}),    indent=2)

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
      "cpp_alternatives": [{{"label":"","cpp":0.0}}],
      "bars": [{{"name":"","have":0,"need":0,"pct":0,"color":"","surplus_or_gap":""}}],
      "transfer_options": [{{"from_program":"","to_program":"","ratio":"","have":0,"need":0,"feasible":true}}]
    }},
    "hotel": {{
      "status": "covered|shortfall|not_applicable",
      "required_pts": 0,
      "program_recommended": "",
      "cpp_achieved": 0.0,
      "cpp_alternatives": [{{"label":"","cpp":0.0}}],
      "bars": [{{"name":"","have":0,"need":0,"pct":0,"color":"","surplus_or_gap":""}}],
      "transfer_options": [{{"from_program":"","to_program":"","ratio":"","have":0,"need":0,"feasible":true}}],
      "tip": "Actionable suggestion if shortfall exists"
    }}
  }},
  "cash_vs_points": {{
    "recommendation": "points|cash|similar",
    "points_option": {{"out_of_pocket": "e.g. ~$150","pts_used": 0,"pts_value_usd": "e.g. ~$1,560","cpp": 0.0}},
    "cash_option": {{"total_cost": "e.g. $1,240","pts_saved": 0,"pts_saved_value": "e.g. ~$1,560","net_vs_points": "e.g. +$320 better"}},
    "verdict": "Plain English explanation of which is better and why"
  }},
  "promotions": [
    {{"title":"","description":"","type":"transfer_bonus|sale_fare|earn_bonus|status_promo","tags":[],"expires":"","relevant_to_this_trip":true}}
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
                '<div class="mock-banner">Preview mode — showing sample data.</div>',
                unsafe_allow_html=True)

        st.markdown(
            f'<div class="plain-english"><b>In plain English:</b> '
            f'{r.get("plain_english","")}</div>',
            unsafe_allow_html=True)

        rd = r.get("route_display", {}); hero = r.get("hero", {})

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
        gen_at = get_metadata().get("generated_at","unknown")
        st.caption(f"Market data refreshed: {gen_at[:10] if len(gen_at) > 9 else gen_at}")

    # ── Execute ──
    if mock_mode:
        render(MOCK, is_mock=True)
    elif not api_key:
        st.warning(
            "This app is not yet configured. "
            "Please ask the administrator to set up the API key."
        )
    else:
        with st.spinner("Finding your best trip…"):
            try:
                render(call_claude(api_key, build_data()))
            except json.JSONDecodeError as e:
                st.error(f"Unexpected response: {e}")
            except anthropic.AuthenticationError:
                st.error("API key issue — please contact the administrator.")
            except anthropic.APIError as e:
                st.error(f"Service error: {e}")
            except Exception as e:
                st.error(f"Something went wrong: {e}")

def page_admin():
    """
    Admin panel — access controlled by a password stored in st.secrets.

    Required Streamlit secrets (set in Streamlit Cloud dashboard or .streamlit/secrets.toml):
        [admin]
        password   = "your-secret-password"
        api_key    = "sk-ant-..."        # master API key for metadata refreshes
    """

    # ── Helper: read secrets safely ──
    def get_secret(section, key, fallback=None):
        try:
            return st.secrets[section][key]
        except (KeyError, FileNotFoundError):
            return fallback

    admin_pw  = get_secret("admin", "password")
    master_key = get_secret("admin", "api_key")
    secrets_configured = bool(admin_pw and master_key)

    # ── Login wall ──
    if not st.session_state.admin_authed:
        st.markdown("## Admin")
        st.markdown(
            '<div style="max-width:360px;">',
            unsafe_allow_html=True)

        if not secrets_configured:
            st.error(
                "Admin secrets not configured. Add these to your Streamlit Cloud secrets:\n\n"
                "```toml\n[admin]\npassword = \"your-password\"\n"
                "api_key  = \"sk-ant-...\"\n```\n\n"
                "Go to: Streamlit Cloud → your app → Settings → Secrets"
            )
            return

        pw_input = st.text_input("Admin password", type="password",
                                 placeholder="Enter password", key="admin_pw_input")
        if st.button("Log in", type="primary", key="admin_login_btn"):
            if pw_input == admin_pw:
                st.session_state.admin_authed = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # ── Authenticated ──
    col_title, col_logout = st.columns([4, 1])
    with col_title:
        st.markdown("## Admin Panel")
    with col_logout:
        if st.button("Log out", key="admin_logout"):
            st.session_state.admin_authed = False
            st.session_state.page = "profile"
            st.rerun()

    st.caption(f"Logged in as admin · API key: {master_key[:12]}..." if master_key else "")
    st.markdown("---")

    # ── Section 1: Mock mode override ──
    st.markdown("### Mock mode")
    st.caption("Override the per-user mock mode toggle globally for all sessions.")

    current = st.session_state.mock_override
    label   = {None: "Follow user setting (default)", True: "Force ON for all users",
                False: "Force OFF for all users"}.get(current, "Unknown")
    st.info(f"Current override: **{label}**")

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        if st.button("Follow user setting", use_container_width=True,
                     type="primary" if current is None else "secondary",
                     key="mock_none"):
            st.session_state.mock_override = None
            st.rerun()
    with mc2:
        if st.button("Force mock ON", use_container_width=True,
                     type="primary" if current is True else "secondary",
                     key="mock_on"):
            st.session_state.mock_override = True
            st.rerun()
    with mc3:
        if st.button("Force mock OFF", use_container_width=True,
                     type="primary" if current is False else "secondary",
                     key="mock_off"):
            st.session_state.mock_override = False
            st.rerun()

    st.markdown("---")

    # ── Section 2: API key ──
    st.markdown("### API key")
    st.caption(
        "The master API key is stored securely in Streamlit secrets — never in the repo. "
        "Update it in Streamlit Cloud → Settings → Secrets."
    )
    if master_key:
        st.success(f"Master key configured: `{master_key[:16]}...{master_key[-4:]}`")
    else:
        st.error("No master API key found in secrets. Add `api_key` under `[admin]` in Streamlit secrets.")

    st.markdown("---")

    # ── Section 3: Metadata refresh ──
    st.markdown("### Market data refresh")

    gen_at    = get_metadata().get("generated_at", "never")
    stale     = is_stale()
    freshness = "Stale — older than 25 hours" if stale else "Fresh"
    cost      = get_metadata().get("refresh_cost_usd", "unknown")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Last refreshed", gen_at[:10] if len(gen_at) > 9 else gen_at)
    col_b.metric("Status",         freshness)
    col_c.metric("Last cost",      f"${cost}" if cost != "unknown" else "—")

    st.markdown("**What gets refreshed:**")
    st.markdown(
        "- Point valuations (CPP) for all 17 programs\n"
        "- Transfer partner ratios\n"
        "- Active promotions (transfer bonuses, sale fares, earn promos)\n"
        "- Cash rate benchmarks by route and cabin class\n"
        "- CPP decision thresholds"
    )

    if not master_key:
        st.warning("Cannot refresh — no API key configured in secrets.")
    else:
        if st.button(
            "Run metadata refresh now",
            type="primary",
            use_container_width=True,
            key="admin_refresh_btn"
        ):
            with st.spinner("Calling Claude to refresh market data… (~30 seconds)"):
                try:
                    import os
                    # Temporarily set the env var so metadata_refresh.py picks it up
                    original_key = os.environ.get("ANTHROPIC_API_KEY")
                    os.environ["ANTHROPIC_API_KEY"] = master_key
                    data = refresh_metadata()
                    save_metadata(data)
                    if original_key:
                        os.environ["ANTHROPIC_API_KEY"] = original_key
                    elif "ANTHROPIC_API_KEY" in os.environ:
                        del os.environ["ANTHROPIC_API_KEY"]

                    # Clear the cache so get_metadata() re-reads the new file
                    get_metadata.clear()

                    st.success(
                        f"Refresh complete! "
                        f"{len(data.get('promotions',[]))} promotions loaded · "
                        f"Cost: ${data.get('refresh_cost_usd','?')} · "
                        f"Commit metadata.json to your repo to persist."
                    )
                    st.json({
                        "generated_at":     data.get("generated_at"),
                        "programs_valued":  len(data.get("point_valuations",{})),
                        "promotions_found": len(data.get("promotions",[])),
                        "cost_usd":         data.get("refresh_cost_usd"),
                    })
                    st.rerun()  # re-render the page so all META references update
                except Exception as e:
                    st.error(f"Refresh failed: {e}")

    st.markdown("---")

    # ── Section 4: Current metadata preview ──
    with st.expander("View current metadata.json"):
        st.json(get_metadata())

    # ── Section 5: Setup instructions ──
    with st.expander("Setup instructions"):
        st.markdown("""
**1. Add secrets to Streamlit Cloud**

Go to your app → Settings → Secrets and add:

```toml
[admin]
password = "choose-a-strong-password"
api_key  = "sk-ant-your-anthropic-key"
```

**2. Schedule daily refresh (GitHub Actions)**

The workflow at `.github/workflows/refresh_metadata.yml` runs at midnight UTC.
Add your API key to GitHub repo secrets as `ANTHROPIC_API_KEY`.

**3. Access this page**

Navigate here via the Admin nav button and enter your password.
The session stays authenticated until you log out or close the browser.

**4. Security model**

- Password and API key live only in Streamlit secrets (encrypted, server-side)
- Nothing sensitive is stored in the repo or in `metadata.json`
- Admin session is per-browser (session state) — closing the tab logs you out
- The admin route is not hidden by URL — it's protected by password only
""")


# ─────────────────────────────────────────────
#  NAV + ROUTER
# ─────────────────────────────────────────────

cur_page = st.session_state.get("page", "profile")

# ── Header: app name left, tab nav right (desktop) / full-width tabs (mobile) ──
_hcol1, _hcol2 = st.columns([1, 3])
with _hcol1:
    st.markdown(
        "<p style='font-size:1.1rem;font-weight:700;color:#111;margin:.5rem 0 0;'>"
        "Loyalty Optimizer</p>",
        unsafe_allow_html=True)
with _hcol2:
    # Tab-style nav using st.buttons styled via CSS as underline tabs
    _t1, _t2, _t3, _tspc = st.columns([1, 1, 0.7, 3])
    with _t1:
        if st.button("My Profile", key="nav_profile", use_container_width=True,
                     type="primary" if cur_page == "profile" else "secondary"):
            st.session_state.page = "profile"; st.rerun()
    with _t2:
        if st.button("Plan a Trip", key="nav_trip", use_container_width=True,
                     type="primary" if cur_page == "trip" else "secondary"):
            st.session_state.page = "trip"; st.rerun()
    with _t3:
        if st.button("Admin", key="nav_admin", use_container_width=True,
                     type="primary" if cur_page == "admin" else "secondary"):
            st.session_state.page = "admin"; st.rerun()

st.markdown("<hr style='margin:.2rem 0 .75rem;border:none;border-top:1px solid #e8e8e8;'>",
            unsafe_allow_html=True)
if cur_page == "profile":
    page_profile()
elif cur_page == "admin":
    page_admin()
else:
    page_trip()
