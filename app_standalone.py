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
)

# ─────────────────────────────────────────────
#  VIEWPORT DETECTION
# ─────────────────────────────────────────────
# Uses a URL query param (?mobile=1) set by a tiny inline <script>.
# The script runs on page load, checks window.innerWidth, and if ≤768
# appends ?mobile=1 to the URL — triggering one Streamlit rerun.
# After that rerun IS_MOBILE is True and stays True for the session.
# No external library, no visible widget, no loading flash on desktop.

def _detect_viewport():
    # Already detected this session
    if "viewport_width" in st.session_state:
        return st.session_state.viewport_width

    # Check if the JS probe set ?mobile=1
    mobile_param = st.query_params.get("mobile", None)
    if mobile_param is not None:
        w = 390 if mobile_param == "1" else 1200
        st.session_state.viewport_width = w
        st.query_params.clear()   # clean URL
        return w

    # First render — inject the probe script, default to desktop
    st.markdown("""
<script>
(function() {
    if (window.innerWidth <= 768) {
        var url = new URL(window.location.href);
        if (!url.searchParams.has('mobile')) {
            url.searchParams.set('mobile', '1');
            window.location.replace(url.toString());
        }
    }
})();
</script>
""", unsafe_allow_html=True)
    st.session_state.viewport_width = 1200
    return 1200

VIEWPORT_W = _detect_viewport()
IS_MOBILE  = VIEWPORT_W <= 768

# ─────────────────────────────────────────────
#  STYLES
# ─────────────────────────────────────────────
# Desktop CSS (unchanged from original) is always loaded.
# Mobile CSS is appended ONLY on mobile and overrides where needed.

st.html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script>
(function(){
    function _checkMobile(){
        if(window.innerWidth<=768) document.body.classList.add('is-mobile');
        else document.body.classList.remove('is-mobile');
    }
    _checkMobile();
    window.addEventListener('resize',_checkMobile);
})();
</script>
<style>
/* ════════════════════════════════════════════════════════════════
   AI LOYALTY OPTIMIZER — DESIGN SYSTEM
   ════════════════════════════════════════════════════════════════ */
:root {
    /* — Type — */
    --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;

    /* — Neutrals — */
    --ink:      #0A0A0B;   /* primary text, headings, CTAs */
    --ink-2:    #27272A;   /* button hover */
    --ink-3:    #52525B;   /* body secondary */
    --ink-4:    #71717A;   /* muted text */
    --ink-5:    #A1A1AA;   /* placeholder, captions */
    --ink-6:    #D4D4D8;   /* disabled */

    /* — Surfaces — */
    --paper:     #FFFFFF;
    --canvas:    #FAFAF7;  /* page background — warm off-white */
    --surface-1: #F4F4F1;  /* subtle bg (section pills) */
    --surface-2: #ECECE8;  /* hover surfaces */

    /* — Borders — */
    --line:      #E5E5E0;
    --line-soft: #F0F0EC;

    /* — Brand & semantic — */
    --brand:        var(--ink);         /* primary actions = near-black */
    --brand-hover:  var(--ink-2);
    --accent:       #E11D48;            /* used only for "Find Trip" CTA */
    --accent-hover: #BE123C;
    --success:      #047857;
    --success-soft: #ECFDF5;
    --warning:      #B45309;
    --warning-soft: #FFFBEB;
    --info:         #1E40AF;
    --info-soft:    #EFF6FF;

    /* — Radii — */
    --r-sm: 8px;
    --r-md: 12px;
    --r-lg: 16px;
    --r-xl: 20px;
    --r-full: 9999px;

    /* — Shadows — */
    --shadow-1: 0 1px 2px rgba(15,23,42,.04);
    --shadow-2: 0 1px 3px rgba(15,23,42,.06), 0 1px 2px rgba(15,23,42,.03);
    --shadow-3: 0 4px 12px rgba(15,23,42,.06), 0 2px 4px rgba(15,23,42,.03);

    /* — Motion — */
    --t-fast: 120ms cubic-bezier(.4, 0, .2, 1);
    --t-base: 180ms cubic-bezier(.4, 0, .2, 1);
}

/* ── Base ───────────────────────────────────────────────────────── */
html, body, .stApp, [class*="st-emotion-cache"] {
    font-family: var(--font) !important;
    color: var(--ink);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}
.stApp { background: var(--canvas) !important; }

.block-container {
    max-width: 880px !important;
    padding: 2.25rem 1.5rem 4rem !important;
}

/* Sidebar — hide entirely; everything's in the main flow */
section[data-testid="stSidebar"],
[data-testid="collapsedControl"],
button[data-testid="stSidebarCollapsedControl"] { display: none !important; }

/* Headings */
h1, .stMarkdown h1 {
    font-size: 30px !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em !important;
    color: var(--ink) !important;
    line-height: 1.2 !important;
    margin: 0 0 .35rem !important;
}
h2, .stMarkdown h2 {
    font-size: 22px !important;
    font-weight: 600 !important;
    letter-spacing: -0.015em !important;
    color: var(--ink) !important;
    line-height: 1.3 !important;
}
h3, .stMarkdown h3 {
    font-size: 17px !important;
    font-weight: 600 !important;
    color: var(--ink) !important;
}
p, .stMarkdown p { color: var(--ink-3); line-height: 1.6; }

/* Horizontal rules — softer */
hr {
    margin: 1.5rem 0 !important;
    border: none !important;
    border-top: 1px solid var(--line) !important;
}

/* ── Buttons (Streamlit defaults reset) ───────────────────────── */
button[kind="primary"], .stButton button[kind="primary"] {
    background: var(--brand) !important;
    color: #fff !important;
    border: 1px solid var(--brand) !important;
    border-radius: var(--r-sm) !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: .55rem 1rem !important;
    min-height: 40px !important;
    white-space: nowrap !important;
    box-shadow: none !important;
    transition: background var(--t-fast), border-color var(--t-fast) !important;
}
/* Force white text on all inner elements Streamlit wraps button labels in */
button[kind="primary"] *, .stButton button[kind="primary"] * {
    color: #fff !important;
    white-space: nowrap !important;
}
button[kind="primary"]:hover, .stButton button[kind="primary"]:hover {
    background: var(--brand-hover) !important;
    border-color: var(--brand-hover) !important;
    color: #fff !important;
}
button[kind="secondary"], .stButton button[kind="secondary"] {
    background: var(--paper) !important;
    color: var(--ink) !important;
    border: 1px solid var(--line) !important;
    border-radius: var(--r-sm) !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: .55rem .75rem !important;
    min-height: 40px !important;
    white-space: nowrap !important;
    box-shadow: none !important;
    transition: background var(--t-fast), border-color var(--t-fast) !important;
}
button[kind="secondary"] p, .stButton button[kind="secondary"] p {
    white-space: nowrap !important;
    overflow: hidden !important;
    margin: 0 !important;
}
button[kind="secondary"]:hover, .stButton button[kind="secondary"]:hover {
    background: var(--surface-1) !important;
    border-color: var(--ink-5) !important;
}
button:focus, .stButton button:focus {
    box-shadow: 0 0 0 3px rgba(10,10,11,.08) !important;
    outline: none !important;
}

/* ── Inputs (Streamlit reset) ─────────────────────────────────── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stTextInput"] > div > div,
[data-testid="stNumberInput"] > div > div,
[data-testid="stDateInput"] > div > div {
    background: var(--paper) !important;
    border: 1px solid var(--line) !important;
    border-radius: var(--r-sm) !important;
    min-height: 40px !important;
    transition: border-color var(--t-fast) !important;
}
[data-testid="stSelectbox"] > div > div:hover,
[data-testid="stTextInput"] > div > div:hover,
[data-testid="stNumberInput"] > div > div:hover,
[data-testid="stDateInput"] > div > div:hover {
    border-color: var(--ink-5) !important;
}
[data-testid="stSelectbox"] > div > div:focus-within,
[data-testid="stTextInput"] > div > div:focus-within,
[data-testid="stNumberInput"] > div > div:focus-within,
[data-testid="stDateInput"] > div > div:focus-within {
    border-color: var(--ink) !important;
    box-shadow: 0 0 0 3px rgba(10,10,11,.06) !important;
}
[data-testid="stWidgetLabel"], label[data-testid="stWidgetLabel"] {
    font-size: 12px !important;
    font-weight: 500 !important;
    color: var(--ink-4) !important;
    margin-bottom: .35rem !important;
}

/* ── Slider — recolor from default red ────────────────────────── */
[data-testid="stSlider"] [role="slider"] {
    background: var(--ink) !important;
    border: 2px solid #fff !important;
    box-shadow: 0 0 0 1px var(--ink), 0 1px 3px rgba(0,0,0,.12) !important;
}
[data-testid="stSlider"] > div > div > div > div { background: var(--ink) !important; }
[data-testid="stSlider"] > div > div > div { background: var(--surface-2) !important; }
[data-testid="stSlider"] [data-testid="stTickBar"] { background: transparent !important; }
[data-testid="stTickBarMin"], [data-testid="stTickBarMax"] {
    color: var(--ink-5) !important; font-size: 11px !important;
}
/* Slider thumb tooltip pip */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] + div {
    background: var(--ink) !important;
    color: #fff !important;
}

/* ── Plain-English callout ────────────────────────────────────── */
.plain-english {
    background: var(--info-soft);
    border: 1px solid #DBEAFE;
    border-radius: var(--r-md);
    padding: 1rem 1.25rem;
    font-size: 14px;
    color: #1E3A8A;
    line-height: 1.65;
    margin-bottom: 1.25rem;
}

/* ── Hero result card ─────────────────────────────────────────── */
.hero {
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    overflow: hidden;
    margin-bottom: 1.25rem;
    box-shadow: var(--shadow-1);
}
.hero-top { padding: 1.25rem 1.5rem; }
.route {
    font-size: 19px;
    font-weight: 600;
    color: var(--ink);
    letter-spacing: -0.01em;
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 4px;
}
.route-line { flex: 1; height: 1px; background: var(--line); }
.tagline { font-size: 13px; color: var(--ink-4); }
.hero-bottom {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    border-top: 1px solid var(--line);
}
.hero-stat {
    padding: 1rem 1.25rem;
    border-right: 1px solid var(--line);
}
.hero-stat:last-child { border-right: none; }
.hs-label {
    font-size: 10.5px;
    color: var(--ink-5);
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 600;
    margin-bottom: 4px;
}
.hs-val {
    font-size: 17px;
    font-weight: 600;
    color: var(--ink);
    letter-spacing: -0.01em;
    line-height: 1.3;
}
.hs-sub { font-size: 12px; color: var(--ink-4); margin-top: 2px; }

/* ── Points bars ──────────────────────────────────────────────── */
.pts-wrap {
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
}
.pts-title, .card-head {
    font-size: 10.5px;
    font-weight: 600;
    color: var(--ink-5);
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 14px;
}
.pts-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.pts-name { font-size: 13px; color: var(--ink); min-width: 130px; font-weight: 500; }
.pts-track { flex: 1; height: 6px; background: var(--surface-1); border-radius: var(--r-full); overflow: hidden; }
.pts-fill { height: 100%; border-radius: var(--r-full); }
.pts-amt { font-size: 12px; color: var(--ink-4); min-width: 100px; text-align: right; }
.legend { display: flex; gap: 16px; margin-top: 12px; flex-wrap: wrap; }
.legend-item { font-size: 11px; color: var(--ink-4); display: flex; align-items: center; gap: 6px; }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

/* ── Generic result cards ─────────────────────────────────────── */
.res-card, .steps-card {
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
}
.dr {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid var(--line-soft);
    font-size: 14px;
}
.dr:last-child { border-bottom: none; }
.dr-l { color: var(--ink-3); }
.dr-v { font-weight: 500; color: var(--ink); text-align: right; }

/* Perks chips */
.perks-row { display: flex; flex-wrap: wrap; gap: 6px; margin: .5rem 0 1.25rem; }
.chip {
    background: var(--surface-1);
    border: 1px solid var(--line);
    border-radius: var(--r-full);
    padding: 5px 12px;
    font-size: 12px;
    color: var(--ink-3);
}

/* Steps */
.step {
    display: flex;
    gap: 14px;
    padding: 12px 0;
    border-bottom: 1px solid var(--line-soft);
    align-items: flex-start;
}
.step:last-child { border-bottom: none; }
.step-num {
    width: 26px; height: 26px; min-width: 26px;
    border-radius: 50%;
    background: var(--ink);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
}
.step-title { font-size: 14px; font-weight: 600; color: var(--ink); margin-bottom: 4px; }
.step-desc { font-size: 13px; color: var(--ink-3); line-height: 1.55; }

/* Alternatives */
.alt-chip {
    background: var(--surface-1);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    padding: .9rem 1.1rem;
    margin-bottom: 8px;
}
.alt-name { font-size: 14px; font-weight: 600; color: var(--ink); margin-bottom: 4px; }
.alt-desc { font-size: 13px; color: var(--ink-2); margin-bottom: 4px; }
.alt-trade { font-size: 12px; color: var(--ink-5); }

/* Credit card recommendation */
.cc-wrap {
    background: linear-gradient(135deg, #FFFBF0 0%, #FFFFFF 100%);
    border: 1px solid #FDE68A;
    border-radius: var(--r-lg);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
}
.cc-eye {
    font-size: 10.5px;
    color: var(--warning);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 8px;
}
.cc-name { font-size: 16px; font-weight: 600; color: var(--ink); margin-bottom: 4px; letter-spacing: -0.01em; }
.cc-bonus { font-size: 13px; color: var(--success); margin-bottom: 8px; font-weight: 500; }
.cc-why { font-size: 13px; color: var(--ink-3); line-height: 1.55; }

/* Mock-mode banner */
.mock-banner {
    background: var(--warning-soft);
    border: 1px solid #FDE68A;
    border-radius: var(--r-sm);
    padding: .65rem 1rem;
    font-size: 13px;
    color: var(--warning);
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ════════════════════════════════════════════════════════════════
   SECTION-CARD PATTERN (used on trip form for "Optimize for",
   "Route", "Dates", "Preferences")
   ════════════════════════════════════════════════════════════════ */
.mf-section, .m-section {
    background: var(--surface-1);
    border-radius: var(--r-md);
    margin-bottom: .75rem;
    overflow: hidden;
}
.mf-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: .9rem 1.1rem;
    font-size: 14px;
}
.mf-header-label {
    font-weight: 600;
    color: var(--ink);
}
.mf-header-value {
    color: var(--ink-4);
    font-size: 13px;
    font-weight: 400;
    text-align: right;
    max-width: 55%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.mf-body {
    padding: 0 .9rem .9rem;
}
.mf-route-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: .5rem 0;
    border-top: 1px solid var(--line-soft);
}
.mf-route-lbl {
    font-size: 12.5px;
    color: var(--ink-4);
    width: 40px;
    flex-shrink: 0;
    padding-top: 11px;
    font-weight: 500;
}
.mf-route-val { flex: 1; min-width: 0; }

/* Make inputs inside section-cards seamless */
.mf-body div[data-testid="stSelectbox"] label,
.mf-body div[data-testid="stDateInput"] label,
.mf-body div[data-testid="stNumberInput"] label,
.mf-body div[data-testid="stSlider"] label { display: none !important; }
.mf-body div[data-testid="stSelectbox"] > div > div,
.mf-body div[data-testid="stDateInput"] > div > div {
    background: var(--paper) !important;
    border-color: var(--line) !important;
    border-radius: var(--r-sm) !important;
}

/* ── Segmented controls (Round trip / One way, etc.) ──────────── */
.m-seg button, .mf-seg button {
    background: var(--paper) !important;
    color: var(--ink-2) !important;
    border: 1px solid var(--line) !important;
    border-radius: var(--r-sm) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    min-height: 40px !important;
    box-shadow: none !important;
    transition: all var(--t-fast) !important;
}
.m-seg button:hover, .mf-seg button:hover {
    border-color: var(--ink-5) !important;
    color: var(--ink) !important;
}
.m-seg button[kind="primary"], .mf-seg button[kind="primary"] {
    background: var(--ink) !important;
    color: #fff !important;
    border-color: var(--ink) !important;
    font-weight: 600 !important;
}

/* Force seg button columns to stay side-by-side */
.m-seg > div, .mf-seg > div {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 6px !important;
    width: 100% !important;
}
.m-seg > div > div, .mf-seg > div > div {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    width: 0 !important;
    padding: 0 !important;
}

/* ════════════════════════════════════════════════════════════════
   PROFILE PAGE (My Programs / Cards)
   ════════════════════════════════════════════════════════════════ */
.m-profile-cat {
    font-size: 10.5px;
    font-weight: 600;
    color: var(--ink-5);
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin: 1.25rem 0 .35rem;
}
.m-profile-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 11px 0;
    border-bottom: 1px solid var(--line-soft);
}
.m-profile-row:last-child { border-bottom: none; }
.m-profile-row .m-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}
.m-profile-row .m-name {
    flex: 1;
    font-size: 14px;
    font-weight: 600;
    color: var(--ink);
}
.m-profile-row .m-bal {
    font-size: 13px;
    color: var(--ink-3);
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}
.m-profile-row .m-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: var(--r-full);
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
    margin-left: 4px;
}

/* Summary bar */
.m-summary-bar {
    background: var(--surface-1);
    border-radius: var(--r-md);
    padding: .85rem 1.1rem;
    font-size: 13px;
    color: var(--ink-3);
    margin-top: 1rem;
}

/* Dashed "+ Add" button (used on profile + add card forms) */
.m-add-prog button {
    border: 1px dashed var(--line) !important;
    background: var(--canvas) !important;
    color: var(--ink-4) !important;
    border-radius: var(--r-sm) !important;
    height: 42px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: all var(--t-fast) !important;
}
.m-add-prog button:hover {
    background: var(--surface-1) !important;
    border-color: var(--ink-5) !important;
    color: var(--ink-2) !important;
}

/* ════════════════════════════════════════════════════════════════
   MOBILE RESULTS — score cards, pills, CPP chips
   ════════════════════════════════════════════════════════════════ */
.m-res-card {
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: var(--shadow-1);
}
.m-res-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
    gap: 12px;
}
.m-res-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--ink);
    letter-spacing: -0.01em;
    line-height: 1.3;
}
.m-pill-covered, .m-pill-shortfall {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: var(--r-full);
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
    letter-spacing: 0.01em;
}
.m-pill-covered { background: var(--success-soft); color: var(--success); }
.m-pill-shortfall { background: var(--warning-soft); color: var(--warning); }

.m-bar-row { margin-bottom: .5rem; }
.m-bar-labels {
    display: flex;
    justify-content: space-between;
    font-size: 12.5px;
    margin-bottom: 6px;
}
.m-bar-labels .m-bar-name { font-weight: 500; color: var(--ink); }
.m-bar-labels .m-bar-need { color: var(--ink-4); }
.m-bar-track {
    height: 7px;
    background: var(--surface-1);
    border-radius: var(--r-full);
    position: relative;
    overflow: hidden;
}
.m-bar-fill { height: 100%; border-radius: var(--r-full); }
.m-bar-foot {
    text-align: right;
    font-size: 11px;
    margin-top: 4px;
    font-weight: 500;
}

.m-cpp-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 8px;
    margin-top: 1rem;
}
.m-cpp-chip {
    border-radius: var(--r-md);
    padding: .65rem .5rem;
    text-align: center;
    line-height: 1.25;
}
.m-cpp-chip.best { background: var(--success-soft); color: var(--success); }
.m-cpp-chip.normal { background: var(--surface-1); color: var(--ink-3); }
.m-cpp-val { font-size: 16px; font-weight: 600; display: block; letter-spacing: -0.01em; }
.m-cpp-lbl { font-size: 11px; display: block; margin-top: 2px; }

.m-plain {
    background: var(--info-soft);
    border: 1px solid #DBEAFE;
    border-radius: var(--r-md);
    padding: .9rem 1.1rem;
    font-size: 13.5px;
    color: #1E3A8A;
    line-height: 1.55;
    margin-bottom: 1rem;
}

/* ════════════════════════════════════════════════════════════════
   MOBILE-SPECIFIC OVERRIDES (body.is-mobile)
   ════════════════════════════════════════════════════════════════ */
body.is-mobile .block-container {
    padding: 1rem 1rem 2.5rem !important;
    max-width: 100% !important;
}
body.is-mobile .mobile-hide-title h1 { display: none !important; }

/* Mobile card shell (wraps each "page" on mobile) */
.m-card {
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: var(--r-lg);
    padding: 1.25rem 1.25rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: var(--shadow-1);
}
.m-card-title {
    font-size: 20px;
    font-weight: 700;
    color: var(--ink);
    letter-spacing: -0.02em;
    margin: 0 0 1rem;
}

/* Tab nav inside mobile card */
.m-tabs {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--line);
    margin-bottom: 1.25rem;
}
.m-tabs > div[data-testid="column"] { padding: 0 !important; }
.m-tabs button[kind] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    color: var(--ink-4) !important;
    font-weight: 500 !important;
    padding: .6rem .25rem !important;
    box-shadow: none !important;
    height: auto !important;
    min-height: 0 !important;
    font-size: 14px !important;
}
.m-tabs button[kind="primary"] {
    color: var(--ink) !important;
    border-bottom: 2px solid var(--ink) !important;
    font-weight: 600 !important;
}
.m-tabs button:focus { box-shadow: none !important; }

/* The big "Find my best trip" CTA — only place we use accent */
div.m-cta button {
    background: var(--ink) !important;
    color: #fff !important;
    border: none !important;
    border-radius: var(--r-md) !important;
    height: 52px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    width: 100% !important;
    letter-spacing: -0.005em !important;
    box-shadow: var(--shadow-2) !important;
    transition: background var(--t-fast), transform var(--t-fast) !important;
}
div.m-cta button:hover { background: var(--ink-2) !important; }
div.m-cta button:active { transform: scale(.99); }

/* ════════════════════════════════════════════════════════════════
   DESKTOP HEADER (when not in m-card layout)
   ════════════════════════════════════════════════════════════════ */
.app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 1.25rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid var(--line);
}
.app-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 17px;
    font-weight: 700;
    color: var(--ink);
    letter-spacing: -0.015em;
}
.app-brand-mark {
    width: 28px; height: 28px;
    border-radius: 8px;
    background: var(--ink);
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: -0.02em;
}

/* Hide all default styling helpers on smaller widths */
@media (max-width: 768px) {
    .app-header { display: none; }
}

/* Hide the m-hide-on-mobile elements on mobile */
.m-hide-on-mobile { display: none; }
@media (min-width: 769px) {
    .m-hide-on-mobile { display: block; }
}

/* ════════════════════════════════════════════════════════════════
   COMPONENT IFRAMES — clickable_images, etc.
   Streamlit 1.29+ injects a forced white iframe body background we can't
   reach via CSS. Workaround: set iframe to the canvas color so it blends.
   ════════════════════════════════════════════════════════════════ */
iframe {
    background: var(--canvas) !important;
    color-scheme: normal !important;
}
[data-testid="stIFrame"],
[data-testid="stCustomComponentV1"] {
    background: var(--canvas) !important;
    color-scheme: normal !important;
}
[data-testid="element-container"]:has(iframe),
[data-testid="stElementContainer"]:has(iframe),
.element-container:has(iframe) {
    background: transparent !important;
}
/* Allow Edit/Remove buttons to shrink their padding when columns are narrow */
.stButton button {
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
</style>
""")

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
#  PERSISTENT ADMIN SETTINGS
# ─────────────────────────────────────────────
# st.cache_resource is shared across ALL sessions in the same process.
# Backed by admin_settings.json so it survives redeploys/restarts.

from pathlib import Path as _Path
_ADMIN_SETTINGS_PATH = _Path(__file__).parent / "admin_settings.json"

@st.cache_resource
def _admin_settings_store():
    """One shared dict across all sessions. Loaded from disk on first call."""
    if _ADMIN_SETTINGS_PATH.exists():
        try:
            return json.loads(_ADMIN_SETTINGS_PATH.read_text())
        except Exception:
            pass
    return {"mock_override": False}

def get_admin_setting(key, default=None):
    return _admin_settings_store().get(key, default)

def set_admin_setting(key, value):
    store = _admin_settings_store()
    store[key] = value
    try:
        _ADMIN_SETTINGS_PATH.write_text(json.dumps(store, indent=2))
    except Exception:
        pass  # disk write failure is non-fatal; in-memory store still works

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────
if "profile"      not in st.session_state: st.session_state.profile      = {}
if "page"         not in st.session_state: st.session_state.page         = "profile"
if "editing"      not in st.session_state: st.session_state.editing      = None
if "admin_authed" not in st.session_state: st.session_state.admin_authed = False
# mock_override reads from persistent store, not session state
if "mock_override" not in st.session_state:
    st.session_state.mock_override = get_admin_setting("mock_override", False)

# Mobile widget state
if "m_search_scope" not in st.session_state: st.session_state.m_search_scope = "Flight + Hotel"
if "m_trip_type"    not in st.session_state: st.session_state.m_trip_type    = "Round trip"

# ─────────────────────────────────────────────
#  PER-USER PROFILE PERSISTENCE
#  Uses streamlit-cookies-manager with the proven ready() + save() pattern.
#  A small UUID cookie identifies the browser; the actual profile data lives
#  in a per-user JSON file on the server keyed by that UUID.
# ─────────────────────────────────────────────
import json as _json
import uuid as _uuid

_USER_COOKIE_NAME = "loyalty_app_uid"
_COOKIES_OK = True
_cookies = None

try:
    from streamlit_cookies_manager import CookieManager
    _cookies = CookieManager()
    # ready() returns False on the very first render (iframe is still loading).
    # st.stop() halts the script; Streamlit reruns when the iframe reports back,
    # and on that next run ready() returns True.
    if not _cookies.ready():
        st.markdown(
            '<div style="padding:1rem;color:#888;font-size:14px;">Loading…</div>',
            unsafe_allow_html=True,
        )
        st.stop()
except Exception:
    _COOKIES_OK = False

def _get_user_id():
    """Return the persistent per-browser ID. Set the cookie if it's missing."""
    if not _COOKIES_OK or _cookies is None:
        # Cookies unavailable — fall back to a per-process default so the app
        # still works (data persists within this server process but not across
        # browsers). Better than crashing.
        if not st.session_state.get("_uid"):
            st.session_state["_uid"] = _uuid.uuid4().hex
        return st.session_state["_uid"]

    existing = _cookies.get(_USER_COOKIE_NAME)
    if existing:
        return existing

    # No cookie yet — mint a UUID and persist it
    new_id = _uuid.uuid4().hex
    _cookies[_USER_COOKIE_NAME] = new_id
    _cookies.save()  # IMPORTANT: must call save() or the cookie isn't written
    return new_id

USER_ID = _get_user_id()

# Per-user JSON file on disk
def _profile_path_for(user_id):
    return _Path(__file__).parent / f"profile_{user_id}.json"

@st.cache_resource
def _profile_store_for(user_id):
    """Per-user shared dict, loaded from disk on first call per process."""
    path = _profile_path_for(user_id)
    if path.exists():
        try:
            data = _json.loads(path.read_text())
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}

def save_profile_to_cookie():
    """
    Persist the current profile to the per-user file.
    Function name kept for API compatibility with existing call sites.
    """
    try:
        path = _profile_path_for(USER_ID)
        store = _profile_store_for(USER_ID)
        store.clear()
        store.update(st.session_state.profile)
        path.write_text(_json.dumps(store, indent=2))
    except Exception:
        pass

# Hydrate this session's profile from the per-user store on first run
if not st.session_state.get("_profile_loaded"):
    saved = _profile_store_for(USER_ID)
    if saved and not st.session_state.profile:
        st.session_state.profile = dict(saved)
    st.session_state["_profile_loaded"] = True

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

    # Points-gap analysis — drives the "Covered" pill, progress bars, and CPP chips
    # in both desktop and mobile renderers.
    "points_analysis": {
        "flight": {
            "status": "covered",
            "required_pts": 60000,
            "program_recommended": "Aeroplan (via Chase transfer)",
            "cpp_achieved": 2.1,
            "cpp_alternatives": [
                {"label": "via Aeroplan", "cpp": 2.1},
                {"label": "via ANA",      "cpp": 1.8},
                {"label": "via United",   "cpp": 1.4},
            ],
            "bars": [
                {"name": "Chase UR", "have": 80000, "need": 60000, "pct": 100,
                 "color": "#378ADD", "surplus_or_gap": "+20k leftover"},
            ],
            "transfer_options": [
                {"from_program": "Chase UR", "to_program": "Aeroplan",
                 "ratio": "1:1", "have": 80000, "need": 60000, "feasible": True},
            ],
        },
        "hotel": {
            "status": "covered",
            "required_pts": 80000,
            "program_recommended": "Marriott Bonvoy (via Amex transfer)",
            "cpp_achieved": 1.1,
            "cpp_alternatives": [
                {"label": "Courtyard", "cpp": 1.1},
                {"label": "St. Regis", "cpp": 0.8},
                {"label": "cash/nt",   "cpp": 0.0},
            ],
            "bars": [
                {"name": "Bonvoy + Amex", "have": 96000, "need": 80000, "pct": 100,
                 "color": "#1D9E75", "surplus_or_gap": "5th night free"},
            ],
            "transfer_options": [
                {"from_program": "Amex MR", "to_program": "Marriott Bonvoy",
                 "ratio": "1:1.2", "have": 60000, "need": 80000, "feasible": True},
            ],
            "tip": "Book 5 consecutive nights — Bonvoy gives you the 5th free.",
        },
    },

    # Cash vs points comparison
    "cash_vs_points": {
        "recommendation": "points",
        "points_option": {
            "out_of_pocket": "~$150",
            "pts_used": 156000,
            "pts_value_usd": "~$3,200",
            "cpp": 2.1,
        },
        "cash_option": {
            "total_cost": "$5,200",
            "pts_saved": 156000,
            "pts_saved_value": "~$3,200",
            "net_vs_points": "+$1,850 worse than points",
        },
        "verdict": "Points crush cash here — you're getting 2.1¢/pt on the flight, well above the 1.5¢ threshold. Cash would cost ~$5,200 vs ~$150 plus points worth $3,200.",
    },

    # Active promotions (sample)
    "promotions": [
        {
            "title": "Amex → Marriott 20% transfer bonus",
            "description": "Transfer Membership Rewards to Bonvoy and get a 20% bonus through the end of the month. Turns 80k MR into 96k Bonvoy.",
            "type": "transfer_bonus",
            "tags": ["transfer bonus", "hotel"],
            "expires": "2026-06-30",
            "relevant_to_this_trip": True,
        },
        {
            "title": "ANA Business class fare sale (SFO–NRT)",
            "description": "Cash fares reduced ~25% for travel May–July. Doesn't affect award space, but useful as a cash benchmark.",
            "type": "sale_fare",
            "tags": ["sale fare", "flight"],
            "expires": "2026-07-31",
            "relevant_to_this_trip": True,
        },
    ],
}

# ─────────────────────────────────────────────
#  PAGE: MY PROFILE — DESKTOP (unchanged)
# ─────────────────────────────────────────────
def page_profile():
    profile = st.session_state.profile
    editing = st.session_state.get("editing", None)

    st.markdown(
        '<p style="font-size:11px;font-weight:700;color:#999;text-transform:uppercase;'
        'letter-spacing:.05em;margin:0 0 .75rem;">MY LOYALTY PROFILE</p>',
        unsafe_allow_html=True)

    if not profile:
        st.info("No programs added yet. Use the form below to get started.")
    else:
        for cat_name, cat_progs in PROGRAMS.items():
            cat_entries = {k: v for k, v in profile.items() if k in cat_progs}
            if not cat_entries:
                continue
            st.markdown(
                f'<p style="font-size:11px;font-weight:700;color:#999;'
                f'text-transform:uppercase;letter-spacing:.06em;margin:1rem 0 4px;">{cat_name}</p>',
                unsafe_allow_html=True)
            st.markdown('<div style="border-top:1px solid #e8e8e8;margin-bottom:2px;"></div>',
                        unsafe_allow_html=True)

            for prog_name, entry in cat_entries.items():
                pdata  = ALL_PROGRAMS[prog_name]
                color  = pdata["color"]
                status = entry["status"]
                bal    = entry["balance"]

                if editing == prog_name:
                    st.markdown(
                        f'<div style="background:#f0f6ff;border:1px solid #c5d8f7;'
                        f'border-radius:8px;padding:6px 10px;margin:4px 0;">'
                        f'<span style="font-size:12px;color:#1a56cc;font-weight:500;">'
                        f'Editing — {prog_name}</span></div>',
                        unsafe_allow_html=True)
                    e1, e2, e3, e4 = st.columns([2, 2, 1, 1])
                    with e1:
                        new_bal = st.number_input("Balance", min_value=0, step=1000,
                            value=bal, key=f"ebal_{prog_name}", label_visibility="collapsed")
                    with e2:
                        idx = pdata["statuses"].index(status) if status in pdata["statuses"] else 0
                        new_status = st.selectbox("Status", pdata["statuses"], index=idx,
                            key=f"estat_{prog_name}", label_visibility="collapsed")
                    with e3:
                        if st.button("Save", key=f"save_{prog_name}",
                                     use_container_width=True, type="primary"):
                            st.session_state.profile[prog_name] = {
                                "balance": new_bal, "status": new_status}
                            st.session_state.editing = None
                            save_profile_to_cookie()
                            st.rerun()
                    with e4:
                        if st.button("Cancel", key=f"cancel_{prog_name}",
                                     use_container_width=True):
                            st.session_state.editing = None
                            st.rerun()
                else:
                    is_active = status not in ["None", "Standard"]
                    pill_bg   = "#e6f4ea" if is_active else "#f0f0f0"
                    pill_col  = "#1e5c2a" if is_active else "#666"
                    r_info, r_edit, r_del = st.columns([7, 1, 1])
                    with r_info:
                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:10px;'
                            f'padding:8px 0;border-bottom:1px solid #f5f5f5;">'
                            f'<span style="width:9px;height:9px;border-radius:50%;'
                            f'background:{color};flex-shrink:0;display:inline-block;"></span>'
                            f'<span style="font-size:13px;font-weight:600;color:#111;flex:1;">'
                            f'{prog_name}</span>'
                            f'<span style="font-size:13px;color:#555;white-space:nowrap;">'
                            f'{bal:,} pts</span>'
                            f'<span style="display:inline-block;padding:2px 10px;'
                            f'border-radius:20px;font-size:11px;font-weight:500;'
                            f'background:{pill_bg};color:{pill_col};white-space:nowrap;'
                            f'margin-left:4px;">{status}</span></div>',
                            unsafe_allow_html=True)
                    with r_edit:
                        if st.button("Edit", key=f"edit_{prog_name}", use_container_width=True):
                            st.session_state.editing = prog_name
                            st.rerun()
                    with r_del:
                        if st.button("Remove", key=f"del_{prog_name}", use_container_width=True):
                            del st.session_state.profile[prog_name]
                            if st.session_state.editing == prog_name:
                                st.session_state.editing = None
                            save_profile_to_cookie()
                            st.rerun()

        total = sum(e["balance"] for e in profile.values())
        elite = sum(1 for e in profile.values() if e["status"] not in ["None", "Standard"])
        st.markdown(
            f'<div style="margin-top:1rem;padding:.75rem 1rem;background:#f7f7f7;'
            f'border-radius:8px;font-size:13px;color:#555;">'
            f'<b>{len(profile)}</b> programs &nbsp;&middot;&nbsp; '
            f'<b>{total:,}</b> total points &nbsp;&middot;&nbsp; '
            f'<b>{elite}</b> elite status(es)</div>',
            unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Add a program**")
    ac1, ac2, ac3, ac4, ac5 = st.columns([1.4, 1.8, 1.4, 1.8, 0.8])
    with ac1:
        add_cat = st.selectbox("Category", list(PROGRAMS.keys()), key="add_cat")
    already_added = set(profile.keys())
    available = [p for p in PROGRAMS[add_cat] if p not in already_added]
    with ac2:
        if available:
            add_prog = st.selectbox("Program", available, key="add_prog")
        else:
            st.selectbox("Program", ["— all added —"], disabled=True, key="add_prog_dis")
            add_prog = None
    with ac3:
        add_bal = st.number_input("Balance (pts)", min_value=0, step=1000,
                                  value=0, key="add_bal")
    with ac4:
        if add_prog:
            add_status = st.selectbox("Status", PROGRAMS[add_cat][add_prog]["statuses"],
                                      key="add_status")
        else:
            st.selectbox("Status", ["—"], disabled=True, key="add_status_dis")
            add_status = None
    with ac5:
        st.markdown("<div style='margin-top:1.75rem;'>", unsafe_allow_html=True)
        if st.button("+ Add", use_container_width=True, type="primary",
                     disabled=not add_prog, key="add_btn"):
            st.session_state.profile[add_prog] = {"balance": add_bal, "status": add_status}
            save_profile_to_cookie()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def _render_mobile_tabs():
    """Render Profile / Plan / Admin tabs inside a card. Active tab = primary."""
    st.markdown('<div class="m-tabs">', unsafe_allow_html=True)
    t1, t2, t3 = st.columns(3)
    with t1:
        if st.button("Profile", key="m_tab_profile", use_container_width=True,
                     type="primary" if st.session_state.page == "profile" else "secondary"):
            st.session_state.page = "profile"
            st.rerun()
    with t2:
        if st.button("Plan", key="m_tab_plan", use_container_width=True,
                     type="primary" if st.session_state.page == "trip" else "secondary"):
            st.session_state.page = "trip"
            st.rerun()
    with t3:
        if st.button("Admin", key="m_tab_admin", use_container_width=True,
                     type="primary" if st.session_state.page == "admin" else "secondary"):
            st.session_state.page = "admin"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def _seg_buttons(options, state_key, key_prefix, n_cols=None):
    """Render a segmented button group. Reads/writes st.session_state[state_key]."""
    current = st.session_state.get(state_key, options[0])
    n = n_cols or len(options)
    st.markdown('<div class="m-seg">', unsafe_allow_html=True)
    cols = st.columns(n)
    for i, opt in enumerate(options):
        with cols[i % n]:
            if st.button(opt, key=f"{key_prefix}_{i}", use_container_width=True,
                         type="primary" if opt == current else "secondary"):
                st.session_state[state_key] = opt
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    return st.session_state.get(state_key, options[0])

# ─────────────────────────────────────────────
#  TRIP — SHARED HELPERS (used by both mobile + desktop)
# ─────────────────────────────────────────────
def _get_api_key():
    try:
        return st.secrets["admin"]["api_key"]
    except (KeyError, FileNotFoundError):
        return None


def _resolve_mock_mode(api_key):
    if not api_key:
        return True
    return get_admin_setting("mock_override", False)


def _build_trip_data(profile, params):
    """params: dict with origin_city, origin_code, dest_city, dest_code, cabin,
       hotel_style, val_exp, dates_str, nights, is_roundtrip,
       include_flight, include_hotel."""
    cc, al, ht, ast_, hst = {}, {}, {}, {}, {}
    for pn, entry in profile.items():
        bal = entry["balance"]; s = entry["status"]; cat = get_cat(pn)
        if cat == "Credit Cards": cc[pn] = bal
        elif cat == "Airlines":
            al[pn] = bal
            if s != "None": ast_[pn] = s
        elif cat == "Hotels":
            ht[pn] = bal
            if s != "None": hst[pn] = s
    return {
        "points":      {"credit_cards": cc, "airline_miles": al, "hotel_points": ht},
        "status":      {"airlines": ast_, "hotels": hst},
        "trip":        {
            "origin":         f"{params['origin_city']} ({params['origin_code']})" if params['origin_city'] else "",
            "destination":    f"{params['dest_city']} ({params['dest_code']})" if params['dest_city'] else "",
            "dates":          params['dates_str'],
            "nights":         int(params['nights']) if params['nights'] else 0,
            "trip_type":      "Round trip" if params['is_roundtrip'] else "One way",
            "include_flight": params['include_flight'],
            "include_hotel":  params['include_hotel'],
        },
        "preferences": {
            "cabin":               params['cabin'] if params['include_flight'] else "N/A",
            "hotel_style":         params['hotel_style'] if params['include_hotel'] else "N/A",
            "value_vs_experience": params['val_exp'],
        },
    }


_SYSTEM_PROMPT = ("You are an expert travel strategist. "
                  "Return ONLY valid JSON, no markdown, no extra text.")


def _build_prompt(d, params):
    scope = []
    if params['include_flight']: scope.append("flight")
    if params['include_hotel']:  scope.append("hotel")
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
  "route_display": {{"origin": "{params['origin_city']}", "destination": "{params['dest_city']}"}},
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


def _call_claude(key, data, params):
    client = anthropic.Anthropic(api_key=key)
    msg = client.messages.create(
        model="claude-opus-4-5", max_tokens=2000, system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_prompt(data, params)}])
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)

# ─────────────────────────────────────────────
#  RESULTS RENDERER — DESKTOP (unchanged from original)
# ─────────────────────────────────────────────
def _render_results_desktop(r, params, is_mock=False):
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
    if params['include_flight']:
        tagline_parts.append(f"{params['cabin']} class")
        tagline_parts.append("round trip" if params['is_roundtrip'] else "one way")
    if params['nights']:
        tagline_parts.append(f"{int(params['nights'])} nights")
    tagline_parts.append(params['dates_str'])
    tagline = " &middot; ".join(tagline_parts)

    if params['include_flight']:
        route_html = (
            f'<span>{rd.get("origin", params["origin_city"])}</span>'
            f'<div class="route-line"></div>&rarr;'
            + ('<div class="route-line"></div>&larr;' if params['is_roundtrip'] else '')
            + ('<div class="route-line"></div>' if not params['is_roundtrip'] else '')
            + f'<span>{rd.get("destination", params["dest_city"])}</span>'
        )
    else:
        route_html = f'<span>Hotel in {rd.get("destination", params["dest_city"])}</span>'

    stats_html = ""
    if params['include_flight']:
        stats_html += (
            f'<div class="hero-stat">'
            f'<p class="hs-label">Flight</p>'
            f'<p class="hs-val">{hero.get("flight_pts","—")}</p>'
            f'<p class="hs-sub">points used</p></div>'
        )
    if params['include_hotel']:
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
    if params['include_flight']:
        cards.append(
            f'<div class="res-card"><p class="card-head">Flight</p>'
            f'<div class="dr"><span class="dr-l">Airline</span><span class="dr-v">{f.get("airline","—")}</span></div>'
            f'<div class="dr"><span class="dr-l">Book through</span><span class="dr-v">{f.get("book_via","—")}</span></div>'
            f'<div class="dr"><span class="dr-l">Points used</span><span class="dr-v">{f.get("points","—")}</span></div>'
            f'<div class="dr"><span class="dr-l">Cash fees</span><span class="dr-v">{f.get("cash_fees","—")}</span></div>'
            f'</div>'
        )
    if params['include_hotel']:
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

    gen_at = get_metadata().get("generated_at","unknown")
    st.caption(f"Market data refreshed: {gen_at[:10] if len(gen_at) > 9 else gen_at}")

# ─────────────────────────────────────────────
#  RESULTS RENDERER — MOBILE (mockup-style)
# ─────────────────────────────────────────────
def _render_results_mobile(r, params, is_mock=False):
    rd = r.get("route_display", {})

    # Build header line: "SFO → Tokyo · Business"
    o = rd.get("origin", params.get("origin_city", "")) or ""
    d = rd.get("destination", params.get("dest_city", "")) or ""
    arrow = " → " if params['include_flight'] else " · "
    suffix = ""
    if params['include_flight']:
        suffix = f" · {params['cabin']}"
    elif params['include_hotel']:
        suffix = " · Hotel"
    header = f"{o}{arrow}{d}{suffix}" if (o or d) else "Your trip"

    st.markdown('<div class="m-card">', unsafe_allow_html=True)
    st.markdown(f'<p class="m-card-title">{header}</p>', unsafe_allow_html=True)

    if is_mock:
        st.markdown(
            '<div class="mock-banner">Preview mode — showing sample data.</div>',
            unsafe_allow_html=True)

    # Plain-english callout
    st.markdown(
        f'<div class="m-plain">{r.get("plain_english","")}</div>',
        unsafe_allow_html=True)

    # ── Mockup-style Flight/Hotel cards with progress bar + pill ──
    pa = r.get("points_analysis", {})
    f  = r.get("flight", {})
    h  = r.get("hotel", {})

    if params['include_flight']:
        sec = pa.get("flight", {}) if pa else {}
        _render_mobile_section_card(
            title=f"Flight — {f.get('airline','—')} via {f.get('book_via','—').replace('Air Canada Aeroplan','Aeroplan')}",
            sec=sec,
        )

    if params['include_hotel']:
        sec = pa.get("hotel", {}) if pa else {}
        _render_mobile_section_card(
            title=f"Hotel — {h.get('name','—')}",
            sec=sec,
        )

    # If there's no points_analysis (e.g. mock without it), show fallback hero stats
    if not pa:
        hero = r.get("hero", {})
        _render_mobile_fallback_hero(hero, params)

    st.markdown('</div>', unsafe_allow_html=True)  # /m-card

    # ── Secondary sections — keep them, in their own cards for legibility ──
    perks = r.get("perks", [])
    steps = r.get("booking_steps", [])
    alts  = r.get("alternatives", [])
    cc    = r.get("card", {})
    si    = r.get("status", {})
    cvp   = r.get("cash_vs_points", {})
    promos = [p for p in r.get("promotions", []) if p.get("relevant_to_this_trip", True)]

    if perks:
        st.markdown('<div class="m-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-head">What you get</p>', unsafe_allow_html=True)
        chips = "".join(f'<div class="chip">&#10003; {p}</div>' for p in perks)
        st.markdown(f'<div class="perks-row">{chips}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if steps:
        st.markdown('<div class="m-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-head">How to book</p>', unsafe_allow_html=True)
        sh = "".join(
            f'<div class="step"><div class="step-num">{i+1}</div>'
            f'<div><p class="step-title">{s["title"]}</p>'
            f'<p class="step-desc">{s["desc"]}</p></div></div>'
            for i, s in enumerate(steps))
        st.markdown(sh, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if cvp:
        _render_mobile_cash_vs_points(cvp)

    if alts:
        st.markdown('<div class="m-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-head">Other options</p>', unsafe_allow_html=True)
        for a in alts:
            trade = (f'<p class="alt-trade">Tradeoff: {a["trade"]}</p>'
                     if a.get("trade") else "")
            st.markdown(
                f'<div class="alt-chip">'
                f'<p class="alt-name">{a.get("name","")}</p>'
                f'<p class="alt-desc">{a.get("desc","")}</p>{trade}</div>',
                unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if cc.get("name"):
        bonus = f'<p class="cc-bonus">{cc["bonus"]}</p>' if cc.get("bonus") else ""
        st.markdown(
            f'<div class="cc-wrap"><p class="cc-eye">Worth considering</p>'
            f'<p class="cc-name">{cc["name"]}</p>{bonus}'
            f'<p class="cc-why">{cc.get("why","")}</p></div>',
            unsafe_allow_html=True)

    if si.get("airline") or si.get("hotel"):
        if si.get("airline"): st.info(f"Airline: {si['airline']}")
        if si.get("hotel"):   st.info(f"Hotel: {si['hotel']}")

    if promos:
        st.markdown('<div class="m-card">', unsafe_allow_html=True)
        st.markdown('<p class="card-head">Active promotions</p>', unsafe_allow_html=True)
        for p in promos:
            tags_html = "".join(
                f'<span style="font-size:11px;padding:2px 8px;border-radius:20px;'
                f'background:#e8f0fe;color:#1a56cc;margin-right:4px;">{t}</span>'
                for t in p.get("tags",[]))
            expires = f'<p style="font-size:11px;color:#bbb;margin:5px 0 0;">Expires: {p["expires"]}</p>' if p.get("expires") else ""
            st.markdown(
                f'<div style="border:1px solid #e8e8e8;border-radius:12px;'
                f'padding:.85rem 1rem;margin-bottom:.5rem;">'
                f'<p style="font-size:13px;font-weight:600;color:#111;margin:0 0 4px;">{p.get("title","")}</p>'
                f'<p style="font-size:12px;color:#666;margin:0 0 6px;line-height:1.5;">{p.get("description","")}</p>'
                f'{tags_html}{expires}</div>',
                unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.caption(f"Confidence: {r.get('confidence','')}")
    gen_at = get_metadata().get("generated_at","unknown")
    st.caption(f"Market data: {gen_at[:10] if len(gen_at) > 9 else gen_at}")


def _render_mobile_section_card(title, sec):
    """Renders a single Flight or Hotel results card matching the mockup."""
    status = sec.get("status", "")
    if status == "covered":
        pill = '<span class="m-pill-covered">&#10003; Covered</span>'
    elif status == "shortfall":
        pill = '<span class="m-pill-shortfall">&#9650; Shortfall</span>'
    else:
        pill = ""

    # Bars — show the first one prominently (the recommended program)
    bars = sec.get("bars", [])
    bars_html = ""
    for b in bars[:2]:  # limit on mobile to keep it tight
        pct  = min(int(b.get("pct", 0)), 100)
        sg   = b.get("surplus_or_gap", "")
        sg_c = "#1e5c2a" if "+" in sg else "#cc3333"
        have = b.get("have", 0); need = b.get("need", 0)
        # Format "80k / 60k needed" — point values rounded to nearest thousand.
        # Only apply k-suffix shortening once values are >= 1000 to avoid "0k" noise.
        def _fmt_pts(n):
            if n >= 1000: return f"{int(round(n/1000))}k"
            return f"{n:,}"
        have_s = _fmt_pts(have)
        need_s = _fmt_pts(need)
        bars_html += (
            f'<div class="m-bar-row" style="margin-bottom:.85rem;">'
            f'<div class="m-bar-labels">'
            f'<span class="m-bar-name">{b.get("name","")}</span>'
            f'<span class="m-bar-need">{have_s} / {need_s} needed</span>'
            f'</div>'
            f'<div class="m-bar-track">'
            f'<div class="m-bar-fill" style="width:{pct}%;background:{b.get("color","#378ADD")};"></div>'
            f'</div>'
            + (f'<div class="m-bar-foot" style="color:{sg_c};">{sg}</div>' if sg else "")
            + '</div>'
        )

    # CPP chips (3 across)
    cpp_alts = sec.get("cpp_alternatives", [])
    cpp_html = ""
    if cpp_alts:
        best = max((c.get("cpp", 0) for c in cpp_alts), default=0)
        cpp_html = '<div class="m-cpp-row">'
        for c in cpp_alts[:3]:
            cls = "best" if c.get("cpp", 0) == best else "normal"
            cpp_html += (
                f'<div class="m-cpp-chip {cls}">'
                f'<span class="m-cpp-val">{c.get("cpp",0):.1f}¢</span>'
                f'<span class="m-cpp-lbl">{c.get("label","")}</span>'
                f'</div>'
            )
        cpp_html += '</div>'

    st.markdown(
        f'<div class="m-res-card">'
        f'<div class="m-res-head">'
        f'<span class="m-res-title">{title}</span>'
        f'{pill}'
        f'</div>'
        f'{bars_html}'
        f'{cpp_html}'
        f'</div>',
        unsafe_allow_html=True)


def _render_mobile_fallback_hero(hero, params):
    """When points_analysis is empty (e.g. some mock data), show simpler hero stats."""
    rows = []
    if params['include_flight']:
        rows.append(("Flight", hero.get("flight_pts", "—")))
    if params['include_hotel']:
        rows.append(("Hotel",  hero.get("hotel_nights", "—")))
    rows.append(("Cash needed", hero.get("cash", "—")))
    body = "".join(
        f'<div class="dr"><span class="dr-l">{k}</span><span class="dr-v">{v}</span></div>'
        for k, v in rows)
    st.markdown(
        f'<div class="m-res-card">{body}</div>',
        unsafe_allow_html=True)


def _render_mobile_cash_vs_points(cvp):
    rec = cvp.get("recommendation", "")
    po  = cvp.get("points_option", {})
    co  = cvp.get("cash_option", {})
    pts_winner  = rec == "points"
    cash_winner = rec == "cash"

    def card(winner, label, main_val, main_sub, details):
        bdr = "2px solid #3B6D11" if winner else "1px solid #e8e8e8"
        badge = ('<span style="font-size:10px;font-weight:700;padding:2px 8px;'
                 'border-radius:20px;background:#e6f4ea;color:#1e5c2a;">Better</span>'
                 if winner else "")
        rows = "".join(
            f'<div style="display:flex;justify-content:space-between;font-size:11px;'
            f'color:#888;margin-bottom:2px;">'
            f'<span>{k}</span><span style="font-weight:500;color:#111;">{v}</span></div>'
            for k, v in details.items())
        return (
            f'<div style="border:{bdr};border-radius:12px;padding:.85rem 1rem;'
            f'margin-bottom:.6rem;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'margin-bottom:6px;">'
            f'<span style="font-size:11px;font-weight:600;color:#888;'
            f'text-transform:uppercase;letter-spacing:.04em;">{label}</span>{badge}</div>'
            f'<p style="font-size:20px;font-weight:600;color:#111;margin:0 0 2px;">{main_val}</p>'
            f'<p style="font-size:12px;color:#888;margin:0 0 8px;">{main_sub}</p>'
            f'<div style="border-top:1px solid #f0f0f0;padding-top:6px;">{rows}</div>'
            f'</div>'
        )

    st.markdown('<div class="m-card">', unsafe_allow_html=True)
    st.markdown('<p class="card-head">Cash vs points</p>', unsafe_allow_html=True)
    st.markdown(
        card(pts_winner, "Burn points",
             po.get("out_of_pocket", "—"), "out of pocket",
             {"Points used":     f'{po.get("pts_used",0):,}',
              "Points value":    po.get("pts_value_usd", "—"),
              "Effective CPP":   f'{po.get("cpp",0):.1f}¢'}),
        unsafe_allow_html=True)
    st.markdown(
        card(cash_winner, "Pay cash",
             co.get("total_cost", "—"), "total cost",
             {"Points saved":     f'{co.get("pts_saved",0):,}',
              "Points kept value": co.get("pts_saved_value", "—"),
              "Net vs points":     co.get("net_vs_points", "—")}),
        unsafe_allow_html=True)
    if cvp.get("verdict"):
        st.markdown(
            f'<div style="background:#f7f7f7;border-radius:8px;padding:.75rem 1rem;'
            f'font-size:12.5px;color:#555;line-height:1.55;">{cvp["verdict"]}</div>',
            unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  PAGE: PLAN A TRIP — DESKTOP (sidebar form preserved from original)
# ─────────────────────────────────────────────
def page_trip():
    profile   = st.session_state.profile
    api_key   = _get_api_key()
    mock_mode = _resolve_mock_mode(api_key)

    if not profile:
        st.warning("Your loyalty profile is empty. Go to **My Profile** and add your programs first.")
        return

    if mock_mode:
        st.markdown('<div class="mock-banner">Preview mode — sample data.</div>',
                    unsafe_allow_html=True)

    def seg(options, state_key, key_prefix, n_cols=None):
        current = st.session_state.get(state_key, options[0])
        radio_key = f"{key_prefix}_radio"
        idx = options.index(current) if current in options else 0
        st.markdown('<div class="mf-seg">', unsafe_allow_html=True)
        cols = st.columns(len(options) if n_cols is None else n_cols)
        for i, opt in enumerate(options):
            with cols[i % len(cols)]:
                if st.button(opt, key=f"{key_prefix}_{i}", use_container_width=True,
                             type="primary" if opt == current else "secondary"):
                    st.session_state[state_key] = opt
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return st.session_state.get(state_key, options[0])

    def scope_tiles():
        """
        Three icon tiles using st-clickable-images. The images ARE the buttons —
        no hidden Streamlit buttons, no CSS overlay tricks. Click returns the
        clicked image index, which we map back to the scope value.
        """
        from st_clickable_images import clickable_images

        current = st.session_state.get("t_scope", "Flight + Hotel")
        OPTIONS = ["Flight + Hotel", "Flight", "Hotel"]

        # Build inline SVG data-URIs for each tile state (active vs inactive)
        # Each SVG is a 220x110 tile with the icon and label baked in
        def make_tile_svg(label, is_active):
            bg     = "#111111" if is_active else "#ffffff"
            border = "#111111" if is_active else "#e0e0e0"
            fg     = "#ffffff" if is_active else "#333333"
            ic_fg  = "#ffffff" if is_active else "#555555"

            # Tabler-style icon paths (24x24 viewBox)
            PLANE_PATH = ('M16 10h4a2 2 0 0 1 0 4h-4l-4 7h-3l2-7h-4l-2 2H3l1-4'
                          ' l-1-4h2l2 2h4l-2-7h3z')
            BUILDING_PATH = ('M5 21V7l8-4v18M19 21V11l-6-4M9 9v.01M9 12v.01'
                             'M9 15v.01M9 18v.01')

            # ViewBox 180x140 — near-square so icons stay proportionally large at any size
            if label == "Flight + Hotel":
                # Two icons side by side, scaled up
                icons = (
                    f'<g transform="translate(40 30) scale(1.8)">'
                    f'<path d="{PLANE_PATH}" fill="none" stroke="{ic_fg}" '
                    f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
                    f'</g>'
                    f'<g transform="translate(100 30) scale(1.8)">'
                    f'<path d="{BUILDING_PATH}" fill="none" stroke="{ic_fg}" '
                    f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
                    f'</g>'
                )
            elif label == "Flight":
                icons = (
                    f'<g transform="translate(60 22) scale(2.6)">'
                    f'<path d="{PLANE_PATH}" fill="none" stroke="{ic_fg}" '
                    f'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>'
                    f'</g>'
                )
            else:  # Hotel
                icons = (
                    f'<g transform="translate(60 22) scale(2.6)">'
                    f'<path d="{BUILDING_PATH}" fill="none" stroke="{ic_fg}" '
                    f'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>'
                    f'</g>'
                )

            svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 140" '
                f'width="180" height="140">'
                f'<rect x="2" y="2" width="176" height="136" rx="14" '
                f'fill="{bg}" stroke="{border}" stroke-width="2"/>'
                f'{icons}'
                f'<text x="90" y="120" text-anchor="middle" '
                f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" '
                f'font-size="14" font-weight="600" fill="{fg}">{label}</text>'
                f'</svg>'
            )
            import base64
            b64 = base64.b64encode(svg.encode()).decode()
            return f"data:image/svg+xml;base64,{b64}"

        images = [make_tile_svg(label, label == current) for label in OPTIONS]
        titles = OPTIONS

        # Detect mobile via User-Agent so we can size tiles appropriately
        try:
            ua = st.context.headers.get("User-Agent", "").lower()
            tile_is_mobile = any(s in ua for s in ["mobile", "android", "iphone", "ipad", "ipod"])
        except Exception:
            tile_is_mobile = False

        if tile_is_mobile:
            # Mobile: full-width grid, taller square-ish tiles
            div_style = {
                "display": "grid",
                "grid-template-columns": "1fr 1fr 1fr",
                "gap": "8px",
                "justify-content": "center",
            }
            img_style = {
                "cursor": "pointer",
                "width": "100%",
                "height": "auto",
                "border-radius": "14px",
                "transition": "transform .12s",
            }
        else:
            # Desktop: shorter tiles with a max-height cap so they don't dominate the form
            div_style = {
                "display": "grid",
                "grid-template-columns": "1fr 1fr 1fr",
                "gap": "10px",
                "justify-content": "center",
                "max-width": "600px",
                "margin": "0 auto",
            }
            img_style = {
                "cursor": "pointer",
                "width": "100%",
                "max-height": "90px",
                "height": "auto",
                "object-fit": "contain",
                "border-radius": "14px",
                "transition": "transform .12s",
            }

        clicked = clickable_images(
            images,
            titles=titles,
            div_style=div_style,
            img_style=img_style,
            key="scope_tiles_clickable",
        )

        if clicked > -1 and OPTIONS[clicked] != current:
            st.session_state["t_scope"] = OPTIONS[clicked]
            st.rerun()

        return st.session_state.get("t_scope", "Flight + Hotel")

    def mf_open(label, value=""):
        val_html = f'<span class="mf-header-value">{value}</span>' if value else ""
        st.markdown(
            f'<div class="mf-section"><div class="mf-header">'
            f'<span class="mf-header-label">{label}</span>{val_html}'
            f'</div><div class="mf-body">', unsafe_allow_html=True)

    def mf_close():
        st.markdown('</div></div>', unsafe_allow_html=True)

    # ── Optimize for ──
    cur_scope = st.session_state.get("t_scope", "Flight + Hotel")
    mf_open("Optimize for", cur_scope)
    raw_scope = scope_tiles()
    mf_close()
    scope_map    = {"Flight": "Flight only", "Hotel": "Hotel only"}
    search_scope = scope_map.get(raw_scope, raw_scope)
    include_flight = search_scope in ["Flight + Hotel", "Flight only"]
    include_hotel  = search_scope in ["Flight + Hotel", "Hotel only"]

    # ── Route ──
    if include_flight:
        cur_orig  = st.session_state.get("t_origin", "San Francisco, CA — SFO (SFO)")
        cur_dest  = st.session_state.get("t_dest",   "Tokyo — Narita (NRT)")
        mf_open("Route", f"{AIRPORTS.get(cur_orig,'—')} → {AIRPORTS.get(cur_dest,'—')}")
        st.markdown('<div class="mf-route-row"><span class="mf-route-lbl">From</span><div class="mf-route-val">', unsafe_allow_html=True)
        origin_label = st.selectbox("From", AIRPORT_LABELS, key="t_origin",
            index=AIRPORT_LABELS.index(cur_orig), label_visibility="collapsed")
        st.markdown('</div></div>', unsafe_allow_html=True)
        origin_code = AIRPORTS[origin_label]; origin_city = origin_label.split(" —")[0]
        st.markdown('<div class="mf-route-row"><span class="mf-route-lbl">To</span><div class="mf-route-val">', unsafe_allow_html=True)
        dest_label = st.selectbox("To", AIRPORT_LABELS, key="t_dest",
            index=AIRPORT_LABELS.index(cur_dest), label_visibility="collapsed")
        st.markdown('</div></div>', unsafe_allow_html=True)
        dest_code = AIRPORTS[dest_label]; dest_city = dest_label.split(" —")[0]
        st.markdown('<div class="mf-route-row"><span class="mf-route-lbl">Type</span><div class="mf-route-val">', unsafe_allow_html=True)
        trip_type = seg(["Round trip", "One way"], "t_trip_type", "ttt", n_cols=2)
        st.markdown('</div></div>', unsafe_allow_html=True)
        is_roundtrip = trip_type == "Round trip"
        mf_close()
    else:
        cur_dest = st.session_state.get("t_dest", "Tokyo — Narita (NRT)")
        mf_open("Destination", AIRPORTS.get(cur_dest, "—"))
        dest_label = st.selectbox("Destination", AIRPORT_LABELS, key="t_dest",
            index=AIRPORT_LABELS.index(cur_dest), label_visibility="collapsed")
        mf_close()
        dest_city = dest_label.split(" —")[0]; dest_code = AIRPORTS[dest_label]
        origin_city = ""; origin_code = ""; is_roundtrip = False

    # ── Dates ──
    dep_val = st.session_state.get("t_dep_val", date(2026, 6, 10))
    ret_val = st.session_state.get("t_ret_val", date(2026, 6, 20))
    ci_val  = st.session_state.get("t_ci_val",  date(2026, 6, 10))
    co_val  = st.session_state.get("t_co_val",  date(2026, 6, 15))
    if include_flight:
        dates_prev = (f"{dep_val.strftime('%b %d')} – {ret_val.strftime('%b %d')}"
                      if is_roundtrip else dep_val.strftime('%b %d, %Y'))
    else:
        dates_prev = f"{ci_val.strftime('%b %d')} – {co_val.strftime('%b %d')}"
    mf_open("Dates", dates_prev)
    if include_flight:
        if is_roundtrip:
            ca, cb = st.columns(2)
            with ca:
                depart_date = st.date_input("Depart", value=dep_val,
                    min_value=date.today(), key="t_depart")
                st.session_state.t_dep_val = depart_date
            with cb:
                return_date = st.date_input("Return",
                    value=max(ret_val, depart_date + timedelta(days=1)),
                    min_value=depart_date + timedelta(days=1), key="t_return")
                st.session_state.t_ret_val = return_date
            flight_nights = (return_date - depart_date).days
        else:
            depart_date = st.date_input("Departure", value=dep_val,
                min_value=date.today(), key="t_depart")
            st.session_state.t_dep_val = depart_date
            return_date = None; flight_nights = None
    else:
        ca, cb = st.columns(2)
        with ca:
            checkin_date = st.date_input("Check-in", value=ci_val,
                min_value=date.today(), key="t_checkin")
            st.session_state.t_ci_val = checkin_date
        with cb:
            checkout_date = st.date_input("Check-out",
                value=max(co_val, checkin_date + timedelta(days=1)),
                min_value=checkin_date + timedelta(days=1), key="t_checkout")
            st.session_state.t_co_val = checkout_date
        depart_date = checkin_date; return_date = None
        flight_nights = (checkout_date - checkin_date).days
    mf_close()

    # ── Preferences ──
    cur_cabin = st.session_state.get("t_cabin", "Economy")
    cur_hs    = st.session_state.get("t_hotel_style", "Standard")
    cabin_disp = {"Prem. Eco": "Premium Economy"}.get(cur_cabin, cur_cabin)
    if include_flight and include_hotel: pref_prev = f"{cabin_disp} · {cur_hs}"
    elif include_flight: pref_prev = cabin_disp
    else: pref_prev = cur_hs
    # Detect mobile via User-Agent header — works at Python time, no JS, no CSS hide
    def _is_mobile():
        try:
            ua = st.context.headers.get("User-Agent", "").lower()
            return any(s in ua for s in ["mobile", "android", "iphone", "ipad", "ipod"])
        except Exception:
            return False
    is_mobile = _is_mobile()

    mf_open("Preferences", pref_prev)
    if include_flight:
        st.markdown('<p style="font-size:12px;color:#888;margin:0 0 .35rem;">Cabin</p>', unsafe_allow_html=True)
        cabin_options = ["Economy", "Prem. Eco", "Business", "First"]
        if is_mobile:
            current_cabin = st.session_state.get("t_cabin", "Economy")
            cabin_idx = cabin_options.index(current_cabin) if current_cabin in cabin_options else 0
            cabin_raw = st.selectbox("Cabin", cabin_options,
                                     index=cabin_idx, key="t_cabin_mobile_dd",
                                     label_visibility="collapsed")
            st.session_state["t_cabin"] = cabin_raw
        else:
            cabin_raw = seg(cabin_options, "t_cabin", "tcab", n_cols=4)
        cabin = {"Prem. Eco": "Premium Economy"}.get(cabin_raw, cabin_raw)
        st.markdown('<div style="height:.4rem"></div>', unsafe_allow_html=True)
    else:
        cabin = "Economy"
    if include_hotel:
        st.markdown('<p style="font-size:12px;color:#888;margin:0 0 .35rem;">Hotel style</p>', unsafe_allow_html=True)
        hs_options = ["Budget", "Standard", "Luxury"]
        if is_mobile:
            current_hs = st.session_state.get("t_hotel_style", "Standard")
            hs_idx = hs_options.index(current_hs) if current_hs in hs_options else 1
            hotel_style = st.selectbox("Hotel style", hs_options,
                                       index=hs_idx, key="t_hotel_style_mobile_dd",
                                       label_visibility="collapsed")
            st.session_state["t_hotel_style"] = hotel_style
        else:
            hotel_style = seg(hs_options, "t_hotel_style", "ths", n_cols=3)
        st.markdown('<div style="height:.4rem"></div>', unsafe_allow_html=True)
        if include_flight and is_roundtrip: hotel_nights = flight_nights
        elif include_flight: hotel_nights = st.number_input("Nights", min_value=1, max_value=60, value=5, key="t_hotel_nights")
        else: hotel_nights = flight_nights
    else:
        hotel_style = "Standard"; hotel_nights = None
    pref_map = {1:"Max value",3:"Mostly value",5:"Balanced",7:"Mostly comfort",10:"Max comfort"}
    st.markdown('<p style="font-size:12px;color:#888;margin:0 0 .1rem;">Priority</p>', unsafe_allow_html=True)
    val_exp = st.slider("Priority", 1, 10, st.session_state.get("t_val_exp", 5),
                        key="t_val_exp_sl", label_visibility="collapsed")
    st.session_state.t_val_exp = val_exp
    nearest = min(pref_map, key=lambda x: abs(x - val_exp))
    st.markdown(f'<p style="font-size:11px;color:#888;text-align:center;margin:-.1rem 0 0;">{pref_map[nearest]}</p>', unsafe_allow_html=True)
    mf_close()

    # ── CTA ──
    st.markdown('<div style="height:.35rem"></div>', unsafe_allow_html=True)
    run = st.button("Find My Best Trip", type="primary", use_container_width=True, key="t_run")

    # ── Build params & render ──
    if include_flight and is_roundtrip and return_date:
        dates_str = f"{depart_date.strftime('%b %d')} – {return_date.strftime('%b %d, %Y')}"
    elif include_flight:
        dates_str = depart_date.strftime('%b %d, %Y') + " (one way)"
    elif include_hotel:
        dates_str = (f"{depart_date.strftime('%b %d')} – "
                     f"{(depart_date + timedelta(days=hotel_nights)).strftime('%b %d, %Y')}")
    else:
        dates_str = ""
    nights = hotel_nights if hotel_nights else (flight_nights or 0)

    if not run:
        return

    params = {
        'origin_city': origin_city, 'origin_code': origin_code,
        'dest_city':   dest_city,   'dest_code':   dest_code,
        'cabin':       cabin,       'hotel_style': hotel_style,
        'val_exp':     val_exp,     'dates_str':   dates_str,
        'nights':      nights,      'is_roundtrip': is_roundtrip,
        'include_flight': include_flight, 'include_hotel': include_hotel,
    }

    if mock_mode:
        _render_results_desktop(MOCK, params, is_mock=True)
    elif not api_key:
        st.warning("This app is not yet configured. Please ask the administrator to set up the API key.")
    else:
        with st.spinner("Finding your best trip…"):
            try:
                data = _build_trip_data(profile, params)
                result = _call_claude(api_key, data, params)
                _render_results_desktop(result, params)
            except json.JSONDecodeError as e: st.error(f"Unexpected response: {e}")
            except anthropic.AuthenticationError: st.error("API key issue — please contact the administrator.")
            except anthropic.APIError as e: st.error(f"Service error: {e}")
            except Exception as e: st.error(f"Something went wrong: {e}")

def page_admin():
    """
    Admin panel — access controlled by a password stored in st.secrets.

    Required Streamlit secrets:
        [admin]
        password   = "your-secret-password"
        api_key    = "sk-ant-..."
    """

    def get_secret(section, key, fallback=None):
        try:
            return st.secrets[section][key]
        except (KeyError, FileNotFoundError):
            return fallback

    admin_pw   = get_secret("admin", "password")
    master_key = get_secret("admin", "api_key")
    secrets_configured = bool(admin_pw and master_key)

    # On mobile, wrap everything in the card shell
    if IS_MOBILE:
        st.markdown('<div class="m-card">', unsafe_allow_html=True)
        st.markdown('<p class="m-card-title">Admin</p>', unsafe_allow_html=True)
        _render_mobile_tabs()

    # ── Login wall ──
    if not st.session_state.admin_authed:
        if not IS_MOBILE:
            st.markdown("## Admin")
            st.markdown('<div style="max-width:360px;">', unsafe_allow_html=True)

        if not secrets_configured:
            st.error(
                "Admin secrets not configured. Add these to your Streamlit Cloud secrets:\n\n"
                "```toml\n[admin]\npassword = \"your-password\"\n"
                "api_key  = \"sk-ant-...\"\n```\n\n"
                "Go to: Streamlit Cloud → your app → Settings → Secrets"
            )
            if IS_MOBILE: st.markdown('</div>', unsafe_allow_html=True)
            return

        pw_input = st.text_input("Admin password", type="password",
                                 placeholder="Enter password", key="admin_pw_input")
        if st.button("Log in", type="primary", key="admin_login_btn",
                     use_container_width=IS_MOBILE):
            if pw_input == admin_pw:
                st.session_state.admin_authed = True
                st.rerun()
            else:
                st.error("Incorrect password.")

        if not IS_MOBILE:
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('</div>', unsafe_allow_html=True)
        return

    # ── Authenticated ──
    if not IS_MOBILE:
        col_title, col_logout = st.columns([4, 1])
        with col_title:
            st.markdown("## Admin Panel")
        with col_logout:
            if st.button("Log out", key="admin_logout"):
                st.session_state.admin_authed = False
                st.session_state.page = "profile"
                st.rerun()
    else:
        if st.button("Log out", key="admin_logout", use_container_width=True):
            st.session_state.admin_authed = False
            st.session_state.page = "profile"
            st.rerun()

    st.caption(f"Logged in as admin · API key: {master_key[:12]}..." if master_key else "")
    st.markdown("---")

    # ── Section 1: Mock mode ──
    st.markdown("### Mock mode")
    st.caption("When ON, all users see sample data instead of live API results. Persists across sessions.")

    current = get_admin_setting("mock_override", False)
    st.session_state.mock_override = current
    status_label = "🟢 ON — showing sample data" if current else "⚪ OFF — using live API"
    st.info(f"Mock mode is currently: **{status_label}**")

    def _set_mock(value):
        set_admin_setting("mock_override", value)
        st.session_state.mock_override = value
        st.rerun()

    mc1, mc2 = st.columns(2)
    with mc1:
        if st.button("Mock ON", use_container_width=True,
                     type="primary" if current is True else "secondary",
                     key="mock_on"):
            _set_mock(True)
    with mc2:
        if st.button("Mock OFF", use_container_width=True,
                     type="primary" if current is False else "secondary",
                     key="mock_off"):
            _set_mock(False)

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

    if IS_MOBILE:
        st.metric("Last refreshed", gen_at[:10] if len(gen_at) > 9 else gen_at)
        st.metric("Status",         freshness)
        st.metric("Last cost",      f"${cost}" if cost != "unknown" else "—")
    else:
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
        if st.button("Run metadata refresh now", type="primary",
                     use_container_width=True, key="admin_refresh_btn"):
            with st.spinner("Calling Claude to refresh market data… (~30 seconds)"):
                try:
                    import os
                    original_key = os.environ.get("ANTHROPIC_API_KEY")
                    os.environ["ANTHROPIC_API_KEY"] = master_key
                    data = refresh_metadata()
                    save_metadata(data)
                    if original_key:
                        os.environ["ANTHROPIC_API_KEY"] = original_key
                    elif "ANTHROPIC_API_KEY" in os.environ:
                        del os.environ["ANTHROPIC_API_KEY"]
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
                    st.rerun()
                except Exception as e:
                    st.error(f"Refresh failed: {e}")

    st.markdown("---")

    with st.expander("View current metadata.json"):
        st.json(get_metadata())

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

**4. Security model**

- Password and API key live only in Streamlit secrets (encrypted, server-side)
- Nothing sensitive is stored in the repo or in `metadata.json`
- Admin session is per-browser (session state) — closing the tab logs you out
- The admin route is not hidden by URL — it's protected by password only
""")

    if IS_MOBILE:
        st.markdown('</div>', unsafe_allow_html=True)  # /m-card

# ─────────────────────────────────────────────
#  NAV + ROUTER
# ─────────────────────────────────────────────

if IS_MOBILE:
    # Hide the title on mobile (the card titles take over) — wrap so CSS rule applies
    st.markdown('<div class="mobile-hide-title">', unsafe_allow_html=True)
    st.markdown("# AI Loyalty Optimizer")
    st.markdown('</div>', unsafe_allow_html=True)
else:
    # Desktop: modern header with brand mark + tab nav
    st.markdown(
        '<div class="app-header">'
        '<div class="app-brand">'
        '<span class="app-brand-mark">AL</span>'
        '<span>AI Loyalty Optimizer</span>'
        '</div>'
        '<div style="flex:0 0 auto;"></div>'
        '</div>',
        unsafe_allow_html=True
    )

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
        if st.button("Admin", key="nav_admin", use_container_width=True,
                     type="primary" if st.session_state.page == "admin" else "secondary"):
            st.session_state.page = "admin"
            st.rerun()

    st.markdown(
        "<div style='height:1.5rem;'></div>",
        unsafe_allow_html=True)

# Route to the active page
if st.session_state.page == "profile":
    page_profile()
elif st.session_state.page == "admin":
    page_admin()
else:
    page_trip()
