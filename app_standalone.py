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
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── Base layout ── */
.block-container { max-width:860px !important; padding-top:1.5rem !important; }

/* ── Sidebar always hidden — inputs live in main panel ── */
[data-testid="stSidebar"] { display:none !important; }
[data-testid="collapsedControl"] { display:none !important; }
@media (max-width:768px) {
    .block-container { padding-left:1rem !important; padding-right:1rem !important; padding-top:0.75rem !important; }
    h1 { font-size:1.4rem !important; }
}

/* ── Result cards ── */
.plain-english { background:#e6f4ea; border-radius:10px; padding:.9rem 1.1rem;
    font-size:14px; color:#1e5c2a; line-height:1.65; margin-bottom:1rem; }
.hero { border:1px solid #e8e8e8; border-radius:12px; overflow:hidden; margin-bottom:1rem; }
.hero-top { padding:1rem 1.25rem; }
.route { font-size:18px; font-weight:600; color:#111;
    display:flex; align-items:center; gap:10px; margin-bottom:4px; flex-wrap:wrap; }
.route-line { flex:1; min-width:20px; height:1px; background:#ddd; }
.tagline { font-size:13px; color:#666; }
.hero-bottom { display:grid; grid-template-columns:1fr 1fr 1fr; border-top:1px solid #e8e8e8; }
.hero-stat { padding:.85rem 1.1rem; border-right:1px solid #e8e8e8; }
.hero-stat:last-child { border-right:none; }
.hs-label { font-size:11px; color:#999; text-transform:uppercase; letter-spacing:.05em; margin-bottom:3px; }
.hs-val   { font-size:16px; font-weight:600; color:#111; }
.hs-sub   { font-size:11px; color:#888; margin-top:2px; }

/* Stack hero stats on very small screens */
@media (max-width:480px) {
    .hero-bottom { grid-template-columns:1fr 1fr; }
    .hero-stat { border-right:none; border-bottom:1px solid #e8e8e8; }
    .hero-stat:nth-child(odd) { border-right:1px solid #e8e8e8; }
    .hs-val { font-size:14px; }
}

.pts-wrap { background:#fff; border:1px solid #e8e8e8; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem; }
.pts-title { font-size:11px; font-weight:600; color:#999; text-transform:uppercase;
    letter-spacing:.05em; margin-bottom:10px; }
.pts-row  { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
.pts-name { font-size:13px; color:#111; width:120px; flex-shrink:0; }
.pts-track{ flex:1; height:8px; background:#f0f0f0; border-radius:4px; overflow:hidden; }
.pts-fill { height:100%; border-radius:4px; }
.pts-amt  { font-size:12px; color:#888; min-width:80px; text-align:right; }
@media (max-width:480px) {
    .pts-name { width:80px; font-size:11px; }
    .pts-amt  { min-width:60px; font-size:11px; }
}
.legend   { display:flex; flex-wrap:wrap; gap:12px; margin-top:10px; }
.legend-item { font-size:11px; color:#999; display:flex; align-items:center; gap:5px; }
.legend-dot  { width:8px; height:8px; border-radius:50%; flex-shrink:0; }

/* Result detail cards */
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

/* ── Profile rows — keep flex on mobile ── */
.prog-row { flex-wrap:nowrap !important; }
@media (max-width:480px) {
    .prog-name { font-size:12px !important; }
}

/* ── Cash vs points comparison — stack on mobile ── */
.cvp-grid { display:flex; gap:.75rem; }
@media (max-width:520px) {
    .cvp-grid { flex-direction:column; }
}

/* ── Nav and button sizing on mobile ── */
@media (max-width:480px) {
    h1 { font-size:1.2rem !important; margin-bottom:.25rem !important; }
    .stButton button { min-height:44px !important; font-size:14px !important; }
}

/* ── Two-col inputs stack to single col on narrow screens ── */
@media (max-width:480px) {
    [data-testid="stHorizontalBlock"] > div {
        min-width:100% !important;
    }
}

/* ════════════════════════════════════════
   SEARCH CARD — Expedia/Google Flights style
   Strip widget chrome, make rows feel tappable
   ════════════════════════════════════════ */

/* Outer card wrapper */
.search-card-wrap {
    border: 0.5px solid #e0e0e0;
    border-radius: 14px;
    overflow: hidden;
    margin-bottom: 1rem;
    background: #fff;
}

/* Each field row inside the card */
.search-field-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 16px;
    min-height: 56px;
    border-bottom: 0.5px solid #f0f0f0;
    cursor: pointer;
}
.search-field-row:last-child { border-bottom: none; }
.sfi { font-size: 18px; color: #999; flex-shrink: 0; width: 22px; }
.sfb { flex: 1; min-width: 0; }
.sfl { font-size: 10px; color: #aaa; margin-bottom: 1px; text-transform: uppercase; letter-spacing: .04em; }
.sfv { font-size: 14px; font-weight: 500; color: #111; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sfc { font-size: 16px; color: #ccc; flex-shrink: 0; }

/* Scope pills — styled like top toggle */
.scope-pills { display: flex; gap: 0; border: 0.5px solid #e0e0e0; border-radius: 10px; overflow: hidden; margin-bottom: 12px; }
.scope-pill { flex: 1; padding: 9px 0; text-align: center; font-size: 13px; font-weight: 500; color: #666; cursor: pointer; border-right: 0.5px solid #e0e0e0; background: #fff; }
.scope-pill:last-child { border-right: none; }
.scope-pill.active { background: #111; color: #fff; }

/* Trip type pills */
.tt-pills { display: flex; gap: 8px; margin-bottom: 10px; }
.tt-pill { flex: 1; padding: 7px 0; text-align: center; font-size: 12px; border-radius: 8px; border: 0.5px solid #e0e0e0; color: #555; background: #fff; cursor: pointer; }
.tt-pill.active { background: #e8f0fe; color: #1a56cc; border-color: #b8d0f8; font-weight: 500; }

/* Strip Streamlit widget labels inside the search card */
.search-card-inner [data-testid="stSelectbox"] label,
.search-card-inner [data-testid="stDateInput"] label,
.search-card-inner [data-testid="stNumberInput"] label,
.search-card-inner [data-testid="stSlider"] label { display: none !important; }

/* Compress widget internal padding */
.search-card-inner [data-testid="stSelectbox"] > div,
.search-card-inner [data-testid="stDateInput"] > div { margin: 0 !important; padding: 0 !important; }

/* Make selectbox fill the row */
.search-card-inner [data-testid="stSelectbox"] { margin-bottom: 0 !important; }

/* Global: on mobile compress the metric strip */
@media (max-width: 600px) {
    [data-testid="stMetric"] { padding: 6px 8px !important; }
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
    [data-testid="stMetricLabel"] { font-size: 11px !important; }
}

/* ── Mobile: compress all widget vertical padding ── */
@media (max-width: 768px) {
    /* Reduce top padding on page */
    .block-container { padding-top: 0.5rem !important; }

    /* Compress selectbox height */
    [data-testid="stSelectbox"] { margin-bottom: 6px !important; }
    [data-testid="stSelectbox"] > div > div { min-height: 36px !important; }

    /* Compress date inputs */
    [data-testid="stDateInput"] { margin-bottom: 6px !important; }
    [data-testid="stDateInput"] > div { min-height: 36px !important; }

    /* Compress radio buttons */
    [data-testid="stRadio"] { margin-bottom: 6px !important; }
    [data-testid="stRadio"] > div { gap: 4px !important; }

    /* Compress slider */
    [data-testid="stSlider"] { margin-bottom: 6px !important; padding: 0 !important; }

    /* Compress number input */
    [data-testid="stNumberInput"] { margin-bottom: 6px !important; }

    /* Tighten column gaps */
    [data-testid="stHorizontalBlock"] { gap: 8px !important; }

    /* Widget labels smaller */
    .search-card-inner label { font-size: 12px !important; margin-bottom: 2px !important; }

    /* Make radio look like pill tabs */
    [data-testid="stRadio"] label {
        padding: 6px 12px !important;
        border-radius: 20px !important;
        border: 0.5px solid #e0e0e0 !important;
        font-size: 12px !important;
    }

    /* Search button — tall and prominent */
    [data-testid="baseButton-primary"] {
        min-height: 52px !important;
        font-size: 16px !important;
        border-radius: 12px !important;
        margin-top: 4px !important;
    }

    /* Nav buttons — compact */
    [data-testid="baseButton-secondary"] {
        min-height: 36px !important;
        font-size: 13px !important;
    }

    /* Caption text smaller */
    [data-testid="stCaptionContainer"] { font-size: 11px !important; }
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

    # ── Add program — 2-col grid works on mobile and desktop ──
    st.markdown("---")
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

    st.markdown("## Plan a Trip")

    if not profile:
        st.warning("Your loyalty profile is empty. Go to **My Profile** and add your programs first.")
        return

    # ── Status strip ──
    gen_at = get_metadata().get("generated_at", "")
    if mock_mode:
        st.info("Preview mode — showing sample data.")
    elif gen_at and gen_at != "not-yet-refreshed":
        st.caption(f"Market data: {gen_at[:10]}")
    else:
        st.warning("Market data not yet loaded.")

    # ── Profile summary — pure HTML strip, renders perfectly on all screen sizes ──
    total_pts = sum(e["balance"] for e in profile.values())
    elite_ct  = sum(1 for e in profile.values() if e["status"] not in ["None","Standard"])
    prog_ct   = len(profile)
    st.markdown(
        f'''<div style="display:flex;gap:0;border:1px solid #e5e7eb;border-radius:12px;
                overflow:hidden;margin-bottom:1rem;background:#fff;">
          <div style="flex:1;padding:12px 14px;border-right:1px solid #e5e7eb;text-align:center;">
            <div style="font-size:11px;color:#9ca3af;text-transform:uppercase;
                 letter-spacing:.05em;margin-bottom:4px;">Programs</div>
            <div style="font-size:22px;font-weight:600;color:#111827;line-height:1;">{prog_ct}</div>
          </div>
          <div style="flex:1;padding:12px 14px;border-right:1px solid #e5e7eb;text-align:center;">
            <div style="font-size:11px;color:#9ca3af;text-transform:uppercase;
                 letter-spacing:.05em;margin-bottom:4px;">Total points</div>
            <div style="font-size:22px;font-weight:600;color:#111827;line-height:1;">{total_pts:,}</div>
          </div>
          <div style="flex:1;padding:12px 14px;text-align:center;">
            <div style="font-size:11px;color:#9ca3af;text-transform:uppercase;
                 letter-spacing:.05em;margin-bottom:4px;">Elite statuses</div>
            <div style="font-size:22px;font-weight:600;color:#111827;line-height:1;">{elite_ct}</div>
          </div>
        </div>''',
        unsafe_allow_html=True)
    st.markdown("---")

    # ════════════════════════════════════════
    #  SEARCH CARD — pure HTML component
    # ════════════════════════════════════════
    import streamlit.components.v1 as components

    # Read persisted values from session state (set on previous submit)
    ss = st.session_state
    _scope   = ss.get("trip_scope",    "Flight + Hotel")
    _tt      = ss.get("trip_type",     "Round trip")
    _orig    = ss.get("origin_label",  "San Francisco, CA — SFO (SFO)")
    _dest    = ss.get("dest_label",    "Tokyo — Narita (NRT)")
    _dep     = ss.get("depart_str",    "2026-06-10")
    _ret     = ss.get("return_str",    "2026-06-20")
    _cabin   = ss.get("cabin",         "Business")
    _hstyle  = ss.get("hotel_style",   "Standard")
    _nights  = ss.get("hotel_nights_n", 5)
    _valexp  = ss.get("val_exp",       5)

    # Build JS airport list
    airport_js = "[" + ",".join(f'"{k}"' for k in AIRPORT_LABELS) + "]"

    card_html = f"""<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}}
body{{background:transparent;padding:8px 0;}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;}}
.scope-bar{{display:flex;border-bottom:1px solid #e5e7eb;}}
.scope-btn{{flex:1;padding:11px 0;text-align:center;font-size:13px;font-weight:500;color:#6b7280;cursor:pointer;border:none;background:none;border-right:1px solid #e5e7eb;}}
.scope-btn:last-child{{border-right:none;}}
.scope-btn.active{{background:#111827;color:#fff;}}
.tt-bar{{display:flex;gap:8px;padding:10px 14px 6px;}}
.tt-btn{{flex:1;padding:7px 0;border-radius:8px;border:1px solid #e5e7eb;font-size:12px;font-weight:500;color:#6b7280;cursor:pointer;background:#fff;text-align:center;}}
.tt-btn.active{{background:#eff6ff;color:#2563eb;border-color:#bfdbfe;}}
.field{{display:flex;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid #f3f4f6;cursor:pointer;min-height:52px;position:relative;}}
.field:last-child{{border-bottom:none;}}
.field-icon{{font-size:17px;color:#9ca3af;width:20px;text-align:center;flex-shrink:0;}}
.field-body{{flex:1;min-width:0;}}
.field-label{{font-size:10px;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px;}}
.field-value{{font-size:14px;font-weight:500;color:#111827;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.field-chev{{color:#d1d5db;font-size:12px;flex-shrink:0;}}
.swap-row{{display:flex;align-items:center;justify-content:center;padding:6px;background:#f9fafb;border-bottom:1px solid #f3f4f6;border-top:1px solid #f3f4f6;}}
.swap-btn{{display:flex;align-items:center;gap:6px;font-size:11px;color:#6b7280;cursor:pointer;border:none;background:none;padding:4px 10px;border-radius:20px;}}
.swap-btn:hover{{background:#e5e7eb;}}
.nights-badge{{font-size:11px;color:#6b7280;background:#f3f4f6;padding:2px 8px;border-radius:10px;margin-left:8px;}}
select,input[type=date]{{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%;}}
.prefs-row{{display:grid;grid-template-columns:1fr 1fr;gap:0;border-top:1px solid #e5e7eb;}}
.pref-cell{{padding:10px 14px;border-right:1px solid #f3f4f6;}}
.pref-cell:last-child{{border-right:none;}}
.pref-label{{font-size:10px;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px;}}
.pref-select{{width:100%;border:none;font-size:13px;font-weight:500;color:#111827;background:none;cursor:pointer;padding:0;}}
.slider-wrap{{padding:10px 16px 14px;border-top:1px solid #f3f4f6;}}
.slider-label{{display:flex;justify-content:space-between;font-size:11px;color:#9ca3af;margin-bottom:6px;}}
input[type=range]{{width:100%;accent-color:#111827;}}
.btn{{display:block;width:calc(100% - 24px);margin:12px;padding:15px;background:#111827;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:600;cursor:pointer;letter-spacing:.01em;}}
.btn:active{{opacity:.85;transform:scale(.99);}}
.hidden{{display:none;}}
</style>
</head>
<body>
<form id="f">
<div class="card">

  <!-- Scope -->
  <div class="scope-bar">
    <button type="button" class="scope-btn{' active' if _scope=='Flight + Hotel' else ''}" onclick="setScope('Flight + Hotel')">Flight + Hotel</button>
    <button type="button" class="scope-btn{' active' if _scope=='Flight only' else ''}" onclick="setScope('Flight only')">Flight only</button>
    <button type="button" class="scope-btn{' active' if _scope=='Hotel only' else ''}" onclick="setScope('Hotel only')">Hotel only</button>
  </div>

  <!-- Trip type (flight only) -->
  <div class="tt-bar" id="tt-bar">
    <button type="button" class="tt-btn{' active' if _tt=='Round trip' else ''}" data-tt="Round trip" onclick="setTT('Round trip')">⇄ Round trip</button>
    <button type="button" class="tt-btn{' active' if _tt=='One way' else ''}" data-tt="One way" onclick="setTT('One way')">→ One way</button>
  </div>

  <!-- From -->
  <div class="field" id="flight-fields">
    <span class="field-icon">✈</span>
    <div class="field-body">
      <div class="field-label">From</div>
      <div class="field-value" id="orig-val">{_orig.split(' —')[0]}</div>
    </div>
    <span class="field-chev">›</span>
    <select id="orig-sel" onchange="updateOrig(this.value)">
      {''.join(f'<option value="{a}"{" selected" if a==_orig else ""}>{a}</option>' for a in AIRPORT_LABELS)}
    </select>
  </div>

  <!-- Swap -->
  <div class="swap-row" id="swap-row">
    <button type="button" class="swap-btn" onclick="swapAirports()">⇅ Swap</button>
  </div>

  <!-- To -->
  <div class="field" id="flight-fields2">
    <span class="field-icon">⬇</span>
    <div class="field-body">
      <div class="field-label">To</div>
      <div class="field-value" id="dest-val">{_dest.split(' —')[0]}</div>
    </div>
    <span class="field-chev">›</span>
    <select id="dest-sel" onchange="updateDest(this.value)">
      {''.join(f'<option value="{a}"{" selected" if a==_dest else ""}>{a}</option>' for a in AIRPORT_LABELS)}
    </select>
  </div>

  <!-- Depart date -->
  <div class="field" id="dep-field">
    <span class="field-icon">📅</span>
    <div class="field-body">
      <div class="field-label">Departure</div>
      <div class="field-value" id="dep-val">{_dep}</div>
    </div>
    <span class="field-chev">›</span>
    <input type="date" id="dep-date" value="{_dep}" onchange="document.getElementById('dep-val').textContent=fmtDate(this.value);updateNights();">
  </div>

  <!-- Return date -->
  <div class="field" id="ret-field">
    <span class="field-icon">📅</span>
    <div class="field-body">
      <div class="field-label">Return <span class="nights-badge" id="nights-badge">{(date(2026,6,20)-date(2026,6,10)).days} nights</span></div>
      <div class="field-value" id="ret-val">{_ret}</div>
    </div>
    <span class="field-chev">›</span>
    <input type="date" id="ret-date" value="{_ret}" onchange="document.getElementById('ret-val').textContent=fmtDate(this.value);updateNights();">
  </div>

  <!-- Hotel destination (hotel-only) -->
  <div class="field hidden" id="hotel-dest-field">
    <span class="field-icon">🏙</span>
    <div class="field-body">
      <div class="field-label">Destination</div>
      <div class="field-value" id="hdest-val">{_dest.split(' —')[0]}</div>
    </div>
    <span class="field-chev">›</span>
    <select id="hdest-sel" onchange="updateHDest(this.value)">
      {''.join(f'<option value="{a}"{" selected" if a==_dest else ""}>{a}</option>' for a in AIRPORT_LABELS)}
    </select>
  </div>

  <!-- Hotel check-in/out (hotel-only) -->
  <div class="field hidden" id="checkin-field">
    <span class="field-icon">📅</span>
    <div class="field-body">
      <div class="field-label">Check-in</div>
      <div class="field-value" id="ci-val">{_dep}</div>
    </div>
    <span class="field-chev">›</span>
    <input type="date" id="ci-date" value="{_dep}" onchange="document.getElementById('ci-val').textContent=fmtDate(this.value);updateNights();">
  </div>
  <div class="field hidden" id="checkout-field">
    <span class="field-icon">📅</span>
    <div class="field-body">
      <div class="field-label">Check-out <span class="nights-badge" id="hotel-nights-badge">{_nights} nights</span></div>
      <div class="field-value" id="co-val">{_ret}</div>
    </div>
    <span class="field-chev">›</span>
    <input type="date" id="co-date" value="{_ret}" onchange="document.getElementById('co-val').textContent=fmtDate(this.value);updateNights();">
  </div>

  <!-- Preferences row -->
  <div class="prefs-row">
    <div class="pref-cell" id="cabin-cell">
      <div class="pref-label">Cabin</div>
      <select class="pref-select" id="cabin-sel">
        {''.join(f'<option{" selected" if c==_cabin else ""}>{c}</option>' for c in ["Economy","Premium Economy","Business","First"])}
      </select>
    </div>
    <div class="pref-cell" id="hstyle-cell">
      <div class="pref-label">Hotel style</div>
      <select class="pref-select" id="hstyle-sel">
        {''.join(f'<option{" selected" if h==_hstyle else ""}>{h}</option>' for h in ["Budget","Standard","Luxury"])}
      </select>
    </div>
  </div>

  <!-- Value slider -->
  <div class="slider-wrap">
    <div class="slider-label"><span>Max value</span><span>Max experience</span></div>
    <input type="range" min="1" max="10" value="{_valexp}" id="val-slider">
  </div>

</div><!-- end card -->

<button type="submit" class="btn">Find My Best Trip</button>
</form>

<script>
var AIRPORTS = {airport_js};
var scope = "{_scope}";
var tt    = "{_tt}";

function fmtDate(s){{
  if(!s) return '';
  var d = new Date(s+'T12:00:00');
  return d.toLocaleDateString('en-US',{{month:'short',day:'numeric',year:'numeric'}});
}}

function updateNights(){{
  var d1 = document.getElementById('dep-date').value;
  var d2 = document.getElementById('ret-date').value;
  if(d1 && d2){{
    var n = Math.round((new Date(d2)-new Date(d1))/(86400000));
    if(n>0) document.getElementById('nights-badge').textContent = n+' nights';
  }}
  var ci = document.getElementById('ci-date').value;
  var co = document.getElementById('co-date').value;
  if(ci && co){{
    var hn = Math.round((new Date(co)-new Date(ci))/(86400000));
    if(hn>0) document.getElementById('hotel-nights-badge').textContent = hn+' nights';
  }}
}}

function updateOrig(v){{
  document.getElementById('orig-val').textContent = v.split(' —')[0];
}}
function updateDest(v){{
  document.getElementById('dest-val').textContent = v.split(' —')[0];
  document.getElementById('hdest-val').textContent = v.split(' —')[0];
  document.getElementById('hdest-sel').value = v;
}}
function updateHDest(v){{
  document.getElementById('hdest-val').textContent = v.split(' —')[0];
  document.getElementById('dest-sel').value = v;
  document.getElementById('dest-val').textContent = v.split(' —')[0];
}}

function swapAirports(){{
  var os = document.getElementById('orig-sel');
  var ds = document.getElementById('dest-sel');
  var tmp = os.value; os.value = ds.value; ds.value = tmp;
  updateOrig(os.value); updateDest(ds.value);
}}

function show(id){{ document.getElementById(id).classList.remove('hidden'); }}
function hide(id){{ document.getElementById(id).classList.add('hidden'); }}

function setScope(s){{
  scope = s;
  document.querySelectorAll('.scope-btn').forEach(function(b){{
    b.classList.toggle('active', b.textContent.trim()===s);
  }});
  applyScope();
}}

function setTT(t){{
  tt = t;
  document.querySelectorAll('.tt-btn').forEach(function(b){{
    b.classList.toggle('active', b.dataset.tt === t);
  }});
  applyScope();
}}

function applyScope(){{
  var isF = scope==='Flight + Hotel' || scope==='Flight only';
  var isH = scope==='Flight + Hotel' || scope==='Hotel only';
  var isHO = scope==='Hotel only';
  var isRT = tt==='Round trip';

  // flight fields
  ['tt-bar','flight-fields','swap-row','flight-fields2','dep-field','cabin-cell'].forEach(function(id){{
    document.getElementById(id).classList.toggle('hidden', !isF);
  }});
  document.getElementById('ret-field').classList.toggle('hidden', !isF || !isRT);

  // hotel-only fields
  ['hotel-dest-field','checkin-field','checkout-field'].forEach(function(id){{
    document.getElementById(id).classList.toggle('hidden', !isHO);
  }});

  // prefs
  document.getElementById('hstyle-cell').classList.toggle('hidden', !isH);
}}

applyScope();

document.getElementById('f').onsubmit = function(e){{
  e.preventDefault();
  var data = {{
    scope:   scope,
    tt:      tt,
    orig:    document.getElementById('orig-sel').value,
    dest:    document.getElementById('dest-sel').value,
    dep:     document.getElementById('dep-date').value,
    ret:     document.getElementById('ret-date').value,
    ci:      document.getElementById('ci-date') ? document.getElementById('ci-date').value : '',
    co:      document.getElementById('co-date') ? document.getElementById('co-date').value : '',
    cabin:   document.getElementById('cabin-sel').value,
    hstyle:  document.getElementById('hstyle-sel').value,
    valexp:  document.getElementById('val-slider').value,
  }};
  var qs = Object.entries(data).map(function(kv){{
    return encodeURIComponent(kv[0])+'='+encodeURIComponent(kv[1]);
  }}).join('&');
  // window.top is same-origin on Streamlit Cloud — reliable cross-iframe navigation
  try {{
    window.top.location.href = window.top.location.pathname + '?' + qs;
  }} catch(err) {{
    // Fallback for local dev where top may be cross-origin
    window.parent.postMessage({{type:'streamlit:setQueryParam', qs: qs}}, '*');
  }}
}};
</script>
</body>
</html>"""

    _result = components.html(card_html, height=640, scrolling=False)

    # ── Read component return value ──
    # components.html() doesn't return values — use session_state form pattern instead
    # The component uses postMessage to write a hidden Streamlit form, triggered by submit
    # We use a workaround: a hidden st.form that the component posts to via URL params
    qp = st.query_params
    run = "scope" in qp

    def _parse_qp(qp):
        _scope_val = qp.get("scope", "Flight + Hotel")
        include_flight = _scope_val in ["Flight + Hotel", "Flight only"]
        include_hotel  = _scope_val in ["Flight + Hotel", "Hotel only"]
        is_roundtrip   = qp.get("tt", "Round trip") == "Round trip"
        _orig = qp.get("orig", "San Francisco, CA — SFO (SFO)")
        _dst  = qp.get("dest", "Tokyo — Narita (NRT)")
        origin_city = _orig.split(" —")[0]
        origin_code = AIRPORTS.get(_orig, "SFO")
        dest_city   = _dst.split(" —")[0]
        dest_code   = AIRPORTS.get(_dst, "NRT")
        _dep_s = qp.get("dep", "2026-06-10")
        _ret_s = qp.get("ret", "2026-06-20")
        try:
            depart_date = date.fromisoformat(_dep_s)
            return_date = date.fromisoformat(_ret_s) if is_roundtrip else None
        except ValueError:
            depart_date = date(2026,6,10); return_date = date(2026,6,20)
        cabin       = qp.get("cabin",  "Business")
        hotel_style = qp.get("hstyle", "Standard")
        val_exp     = int(qp.get("valexp", 5))
        if include_flight and is_roundtrip and return_date:
            flight_nights = (return_date - depart_date).days
            hotel_nights  = flight_nights
            dates_str = f"{depart_date.strftime('%b %d')} – {return_date.strftime('%b %d, %Y')}"
        elif include_flight:
            flight_nights = None; hotel_nights = None
            dates_str = f"{depart_date.strftime('%b %d, %Y')} (one way)"
        else:
            try:
                checkin  = date.fromisoformat(qp.get("ci","2026-06-10"))
                checkout = date.fromisoformat(qp.get("co","2026-06-15"))
            except ValueError:
                checkin = date(2026,6,10); checkout = date(2026,6,15)
            hotel_nights = (checkout - checkin).days
            depart_date  = checkin; return_date = None
            flight_nights = None
            dates_str = f"{checkin.strftime('%b %d')} – {checkout.strftime('%b %d, %Y')}"
        nights = hotel_nights if hotel_nights else (flight_nights or 0)
        # Persist
        st.session_state.update({
            "trip_scope": _scope_val, "trip_type": qp.get("tt","Round trip"),
            "origin_label": _orig, "dest_label": _dst,
            "depart_str": _dep_s, "return_str": _ret_s,
            "cabin": cabin, "hotel_style": hotel_style,
            "hotel_nights_n": hotel_nights or 5, "val_exp": val_exp,
        })
        st.query_params.clear()
        return dict(
            include_flight=include_flight, include_hotel=include_hotel,
            is_roundtrip=is_roundtrip, origin_city=origin_city, origin_code=origin_code,
            dest_city=dest_city, dest_code=dest_code, depart_date=depart_date,
            return_date=return_date, cabin=cabin, hotel_style=hotel_style,
            val_exp=val_exp, dates_str=dates_str, nights=nights,
            flight_nights=flight_nights, hotel_nights=hotel_nights,
        )

    if run:
        _v = _parse_qp(qp)
    else:
        # Use last persisted values or defaults
        _v = _parse_qp({
            "scope":  st.session_state.get("trip_scope","Flight + Hotel"),
            "tt":     st.session_state.get("trip_type","Round trip"),
            "orig":   st.session_state.get("origin_label","San Francisco, CA — SFO (SFO)"),
            "dest":   st.session_state.get("dest_label","Tokyo — Narita (NRT)"),
            "dep":    st.session_state.get("depart_str","2026-06-10"),
            "ret":    st.session_state.get("return_str","2026-06-20"),
            "cabin":  st.session_state.get("cabin","Business"),
            "hstyle": st.session_state.get("hotel_style","Standard"),
            "valexp": str(st.session_state.get("val_exp",5)),
        })

    include_flight = _v["include_flight"]; include_hotel  = _v["include_hotel"]
    is_roundtrip   = _v["is_roundtrip"];   origin_city    = _v["origin_city"]
    origin_code    = _v["origin_code"];    dest_city      = _v["dest_city"]
    dest_code      = _v["dest_code"];      depart_date    = _v["depart_date"]
    return_date    = _v["return_date"];    cabin          = _v["cabin"]
    hotel_style    = _v["hotel_style"];    val_exp        = _v["val_exp"]
    dates_str      = _v["dates_str"];      nights         = _v["nights"]
    flight_nights  = _v["flight_nights"];  hotel_nights   = _v["hotel_nights"]
    st.markdown("---")

    if not run:
        st.caption("Configure your trip above and tap **Find My Best Trip**.")
        return


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

# Render compact header — title left, three nav buttons right
# On mobile the buttons stack under the title but stay readable
_logo_col, _nav_col = st.columns([2, 3])
with _logo_col:
    st.markdown(
        "<p style='font-size:1.1rem;font-weight:700;color:#111;margin:.4rem 0 0;'>"
        "AI Loyalty Optimizer</p>",
        unsafe_allow_html=True)
with _nav_col:
    nb1, nb2, nb3 = st.columns(3)
    with nb1:
        if st.button(
            "👤 Profile", key="nav_profile", use_container_width=True,
            type="primary" if cur_page == "profile" else "secondary"
        ):
            st.session_state.page = "profile"; st.rerun()
    with nb2:
        if st.button(
            "✈ Plan", key="nav_trip", use_container_width=True,
            type="primary" if cur_page == "trip" else "secondary"
        ):
            st.session_state.page = "trip"; st.rerun()
    with nb3:
        if st.button(
            "⚙ Admin", key="nav_admin", use_container_width=True,
            type="primary" if cur_page == "admin" else "secondary"
        ):
            st.session_state.page = "admin"; st.rerun()

st.markdown(
    "<hr style='margin:.35rem 0 1rem;border:none;border-top:1px solid #e8e8e8;'>",
    unsafe_allow_html=True)

if cur_page == "profile":
    page_profile()
elif cur_page == "admin":
    page_admin()
else:
    page_trip()
