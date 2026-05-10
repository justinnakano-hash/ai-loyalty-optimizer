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

    # ── Profile summary ──
    total_pts = sum(e["balance"] for e in profile.values())
    elite_ct  = sum(1 for e in profile.values() if e["status"] not in ["None","Standard"])
    m1, m2, m3 = st.columns(3)
    m1.metric("Programs", len(profile))
    m2.metric("Total points", f"{total_pts:,}")
    m3.metric("Elite statuses", elite_ct)
    st.markdown("---")

    # ════════════════════════════════════════
    #  SEARCH CARD — compact, Expedia-style
    # ════════════════════════════════════════

    # ── Scope toggle (pill row) ──
    search_scope = st.radio(
        "Planning",
        ["Flight + Hotel", "Flight only", "Hotel only"],
        horizontal=True, key="search_scope",
        label_visibility="collapsed")
    include_flight = search_scope in ["Flight + Hotel", "Flight only"]
    include_hotel  = search_scope in ["Flight + Hotel", "Hotel only"]

    # ── Default values ──
    origin_city = origin_code = dest_city = dest_code = ""
    cabin = "Economy"
    depart_date   = date(2026, 6, 10)
    return_date   = None
    flight_nights = None
    is_roundtrip  = True
    hotel_style   = "Standard"
    hotel_nights  = None

    # ── Search card ──
    st.markdown('<div class="search-card-inner">', unsafe_allow_html=True)

    if include_flight:
        # Trip type
        tt_cols = st.columns(2)
        with tt_cols[0]:
            trip_type = st.radio("Trip type", ["Round trip", "One way"],
                                 horizontal=False, key="trip_type",
                                 label_visibility="collapsed")
        is_roundtrip = trip_type == "Round trip"

        # Route — two compact selects side by side
        rc1, rc2 = st.columns(2)
        with rc1:
            origin_label = st.selectbox(
                "✈ From", AIRPORT_LABELS,
                index=AIRPORT_LABELS.index("San Francisco, CA — SFO (SFO)"),
                key="origin_sel")
            origin_code = AIRPORTS[origin_label]
            origin_city = origin_label.split(" —")[0]
        with rc2:
            dest_label = st.selectbox(
                "✈ To", AIRPORT_LABELS,
                index=AIRPORT_LABELS.index("Tokyo — Narita (NRT)"),
                key="dest_sel")
            dest_code = AIRPORTS[dest_label]
            dest_city = dest_label.split(" —")[0]

        # Dates — side by side calendar pickers
        if is_roundtrip:
            dc1, dc2 = st.columns(2)
            with dc1:
                depart_date = st.date_input(
                    "📅 Depart", value=date(2026, 6, 10),
                    min_value=date.today(), key="depart_date")
            with dc2:
                return_date = st.date_input(
                    "📅 Return",
                    value=date(2026, 6, 10) + timedelta(days=10),
                    min_value=depart_date + timedelta(days=1),
                    key="return_date")
            flight_nights = (return_date - depart_date).days
        else:
            depart_date = st.date_input(
                "📅 Departure date", value=date(2026, 6, 10),
                min_value=date.today(), key="depart_date_ow")

        cabin = st.selectbox(
            "💺 Cabin class",
            ["Economy", "Premium Economy", "Business", "First"],
            key="cabin_sel")

    if include_hotel:
        if not include_flight:
            dest_label = st.selectbox(
                "🏙 Destination", AIRPORT_LABELS,
                index=AIRPORT_LABELS.index("Tokyo — Narita (NRT)"),
                key="hotel_dest_sel")
            dest_city = dest_label.split(" —")[0]
            dest_code = AIRPORTS[dest_label]

            hc1, hc2 = st.columns(2)
            with hc1:
                checkin_date = st.date_input(
                    "📅 Check-in", value=date(2026, 6, 10),
                    min_value=date.today(), key="checkin_date")
            with hc2:
                checkout_date = st.date_input(
                    "📅 Check-out",
                    value=date(2026, 6, 10) + timedelta(days=5),
                    min_value=checkin_date + timedelta(days=1),
                    key="checkout_date")
            hotel_nights = (checkout_date - checkin_date).days
            depart_date  = checkin_date
        elif is_roundtrip and flight_nights:
            hotel_nights = flight_nights
            st.caption(f"🏨 {hotel_nights} hotel nights — matches your flight")
        else:
            hotel_nights = st.number_input(
                "🏨 Hotel nights", min_value=1, max_value=60, value=5,
                key="hotel_nights_input")

        hotel_style = st.selectbox(
            "⭐ Hotel style", ["Budget", "Standard", "Luxury"],
            key="hotel_style_sel")

    # Priority slider — compact
    val_exp = st.slider(
        "Value ←——→ Experience", 1, 10, 5,
        help="1 = max points value  ·  10 = max experience quality",
        key="val_exp_slider")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Big search button ──
    run = st.button("🔍  Find My Best Trip", type="primary",
                    use_container_width=True, key="run_btn")

    # ── Date summary string for prompt ──
    if include_flight and is_roundtrip and return_date:
        dates_str = f"{depart_date.strftime('%b %d')} – {return_date.strftime('%b %d, %Y')}"
    elif include_flight:
        dates_str = f"{depart_date.strftime('%b %d, %Y')} (one way)"
    elif include_hotel and hotel_nights:
        checkout = depart_date + timedelta(days=hotel_nights)
        dates_str = f"{depart_date.strftime('%b %d')} – {checkout.strftime('%b %d, %Y')}"
    else:
        dates_str = ""

    nights = hotel_nights if hotel_nights else (flight_nights or 0)

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

# Title sits on its own line — clean and full width
st.markdown("# AI Loyalty Optimizer")

# Nav — My Profile | Plan a Trip | (Admin, small, right-aligned)
nav_col1, nav_col2, nav_spacer, nav_admin = st.columns([1.4, 1.4, 3.5, 0.8])
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
with nav_admin:
    # Small lock icon — doesn't advertise "admin" to casual users
    admin_label = "Admin" if st.session_state.admin_authed else "Admin"
    if st.button(
        admin_label, key="nav_admin", use_container_width=True,
        type="primary" if st.session_state.page == "admin" else "secondary"
    ):
        st.session_state.page = "admin"
        st.rerun()

st.markdown(
    "<hr style='margin:.5rem 0 1.5rem;border:none;border-top:1px solid #e8e8e8;'>",
    unsafe_allow_html=True)

# Apply global mock override from admin if set
_mock_override = st.session_state.get("mock_override", None)

if st.session_state.page == "profile":
    page_profile()
elif st.session_state.page == "admin":
    page_admin()
else:
    page_trip()
