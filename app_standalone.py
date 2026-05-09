import streamlit as st
import anthropic
import json
import re

st.set_page_config(
    page_title="AI Loyalty Optimizer",
    page_icon="✈️",
    layout="centered",   # constrained width — no more full-stretch
)

# ── CSS ──
st.markdown("""
<style>
/* Cap the main content width and centre it */
.block-container {
    max-width: 860px !important;
    padding-top: 2rem !important;
}

.plain-english{background:#e6f4ea;border-radius:10px;padding:.9rem 1.1rem;font-size:14px;color:#1e5c2a;line-height:1.65;margin-bottom:1.1rem;}
.hero{border:1px solid #e8e8e8;border-radius:12px;overflow:hidden;margin-bottom:1rem;}
.hero-top{padding:1.1rem 1.25rem;}
.route{font-size:19px;font-weight:600;color:#111;display:flex;align-items:center;gap:10px;margin-bottom:4px;}
.route-line{flex:1;height:1px;background:#ddd;}
.tagline{font-size:13px;color:#666;}
.hero-bottom{display:grid;grid-template-columns:1fr 1fr 1fr;border-top:1px solid #e8e8e8;}
.hero-stat{padding:.9rem 1.1rem;border-right:1px solid #e8e8e8;}
.hero-stat:last-child{border-right:none;}
.hs-label{font-size:11px;color:#999;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px;}
.hs-val{font-size:18px;font-weight:600;color:#111;}
.hs-sub{font-size:12px;color:#888;margin-top:2px;}
.pts-wrap{background:#fff;border:1px solid #e8e8e8;border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;}
.pts-title{font-size:11px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px;}
.pts-row{display:flex;align-items:center;gap:10px;margin-bottom:8px;}
.pts-name{font-size:13px;color:#111;min-width:110px;}
.pts-track{flex:1;height:8px;background:#f0f0f0;border-radius:4px;overflow:hidden;}
.pts-fill{height:100%;border-radius:4px;}
.pts-amt{font-size:12px;color:#888;min-width:90px;text-align:right;}
.legend{display:flex;gap:16px;margin-top:10px;}
.legend-item{font-size:11px;color:#999;display:flex;align-items:center;gap:5px;}
.legend-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem;}
.card{background:#fff;border:1px solid #e8e8e8;border-radius:12px;padding:1rem 1.25rem;}
.card-head{font-size:11px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px;}
.dr{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f0f0f0;font-size:13px;}
.dr:last-child{border-bottom:none;}
.dr-l{color:#666;}
.dr-v{font-weight:500;color:#111;text-align:right;}
.perks-row{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:1rem;}
.chip{background:#f5f5f5;border:1px solid #e8e8e8;border-radius:20px;padding:5px 12px;font-size:12px;color:#555;}
.steps-card{background:#fff;border:1px solid #e8e8e8;border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;}
.step{display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #f5f5f5;align-items:flex-start;}
.step:last-child{border-bottom:none;}
.step-num{width:28px;height:28px;min-width:28px;border-radius:50%;background:#e8f0fe;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:#1a56cc;}
.step-title{font-size:13px;font-weight:600;color:#111;margin-bottom:3px;}
.step-desc{font-size:12px;color:#666;line-height:1.55;}
.alt-chip{background:#f7f7f7;border:1px solid #e8e8e8;border-radius:10px;padding:.75rem 1rem;margin-bottom:8px;}
.alt-name{font-size:13px;font-weight:600;color:#111;margin-bottom:3px;}
.alt-desc{font-size:12px;color:#555;margin-bottom:3px;}
.alt-trade{font-size:12px;color:#aaa;}
.cc-wrap{background:#f0f7ff;border:2px solid #a8d0f5;border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;}
.cc-eye{font-size:11px;color:#1a56cc;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;}
.cc-name{font-size:15px;font-weight:600;color:#111;margin-bottom:4px;}
.cc-bonus{font-size:13px;color:#2d7a3a;margin-bottom:6px;}
.cc-why{font-size:13px;color:#555;}
.mock-banner{background:#fff3e0;border:1px solid #ffcc80;border-radius:8px;padding:.6rem 1rem;font-size:13px;color:#e65100;margin-bottom:1rem;}
.section-title{font-size:11px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px;}
.profile-card{background:#fff;border:1px solid #e8e8e8;border-radius:12px;padding:.75rem 1rem;margin-bottom:.6rem;}
.profile-cat{font-size:11px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;}
</style>
""", unsafe_allow_html=True)

# ── Program catalogue ──
PROGRAMS = {
    "Credit Cards": {
        "Chase Ultimate Rewards":   {"color": "#1a56cc", "statuses": ["Standard"]},
        "Amex Membership Rewards":  {"color": "#007bc1", "statuses": ["Standard", "Gold Card", "Platinum Card", "Centurion"]},
        "Capital One Miles":        {"color": "#c8102e", "statuses": ["Standard", "Venture", "Venture X"]},
        "Citi ThankYou Points":     {"color": "#003b70", "statuses": ["Standard", "Preferred", "Premier", "Prestige"]},
        "Bilt Rewards":             {"color": "#111",    "statuses": ["Standard", "Silver", "Gold", "Platinum"]},
    },
    "Airlines": {
        "United MileagePlus":       {"color": "#005daa", "statuses": ["None", "Silver", "Gold", "Platinum", "1K"]},
        "Delta SkyMiles":           {"color": "#c8102e", "statuses": ["None", "Silver Medallion", "Gold Medallion", "Platinum Medallion", "Diamond Medallion"]},
        "American AAdvantage":      {"color": "#0078d2", "statuses": ["None", "Gold", "Platinum", "Platinum Pro", "Executive Platinum"]},
        "Alaska Mileage Plan":      {"color": "#01426a", "statuses": ["None", "MVP", "MVP Gold", "MVP Gold 75K"]},
        "Southwest Rapid Rewards":  {"color": "#304cb2", "statuses": ["None", "A-List", "A-List Preferred", "Companion Pass"]},
        "Air Canada Aeroplan":      {"color": "#c8102e", "statuses": ["None", "25K", "35K", "50K", "75K", "Super Elite"]},
        "British Airways Avios":    {"color": "#075aaa", "statuses": ["None", "Bronze", "Silver", "Gold"]},
        "Singapore KrisFlyer":      {"color": "#00338d", "statuses": ["None", "Elite Silver", "Elite Gold", "PPS Club"]},
    },
    "Hotels": {
        "Marriott Bonvoy":          {"color": "#c8a84b", "statuses": ["None", "Silver Elite", "Gold Elite", "Platinum Elite", "Titanium Elite", "Ambassador Elite"]},
        "Hilton Honors":            {"color": "#00205b", "statuses": ["None", "Silver", "Gold", "Diamond"]},
        "World of Hyatt":           {"color": "#8b1a1a", "statuses": ["None", "Discoverist", "Explorist", "Globalist"]},
        "IHG One Rewards":          {"color": "#006747", "statuses": ["None", "Silver Elite", "Gold Elite", "Platinum Elite", "Diamond Elite"]},
        "Wyndham Rewards":          {"color": "#0066b2", "statuses": ["None", "Blue", "Gold", "Platinum", "Diamond"]},
    }
}

ALL_PROGRAMS = {name: data for cat in PROGRAMS.values() for name, data in cat.items()}

def get_cat(prog_name):
    for cat, progs in PROGRAMS.items():
        if prog_name in progs:
            return cat
    return None

# ── Session state ──
if "profile" not in st.session_state:
    st.session_state.profile = {}
if "editing" not in st.session_state:
    st.session_state.editing = None   # name of program currently being edited

# ── Mock data ──
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


# ── Sidebar ──
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    api_key   = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
    mock_mode = st.toggle("🧪 Mock mode", value=True, help="Test UI without API calls")
    if mock_mode:
        st.caption("Sample data — no API key needed.")

    st.divider()
    st.markdown("### 🎯 My Loyalty Profile")
    st.caption("Set up once — reused for every query.")

    profile = st.session_state.profile

    # ── Display each added program with Edit / Delete ──
    for cat_name, cat_progs in PROGRAMS.items():
        cat_entries = {k: v for k, v in profile.items() if k in cat_progs}
        if not cat_entries:
            continue
        st.markdown(f"**{cat_name}**")
        for prog_name, entry in cat_entries.items():
            prog_data = ALL_PROGRAMS[prog_name]

            # ── Edit mode ──
            if st.session_state.editing == prog_name:
                with st.container():
                    st.markdown(f"*Editing: {prog_name}*")
                    new_bal = st.number_input(
                        "Balance", min_value=0, step=1000,
                        value=entry["balance"],
                        key=f"edit_bal_{prog_name}"
                    )
                    new_status = st.selectbox(
                        "Status",
                        prog_data["statuses"],
                        index=prog_data["statuses"].index(entry["status"])
                              if entry["status"] in prog_data["statuses"] else 0,
                        key=f"edit_status_{prog_name}"
                    )
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("💾 Save", key=f"save_{prog_name}", use_container_width=True):
                            st.session_state.profile[prog_name] = {
                                "balance": new_bal, "status": new_status
                            }
                            st.session_state.editing = None
                            st.rerun()
                    with col_cancel:
                        if st.button("✕ Cancel", key=f"cancel_{prog_name}", use_container_width=True):
                            st.session_state.editing = None
                            st.rerun()

            # ── View mode ──
            else:
                bal_fmt = f"{entry['balance']:,}"
                status  = entry["status"]
                col_info, col_edit, col_del = st.columns([5, 1, 1])
                with col_info:
                    color = prog_data["color"]
                    st.markdown(
                        f'<div style="font-size:13px;padding:4px 0;">'
                        f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
                        f'background:{color};margin-right:6px;vertical-align:middle;"></span>'
                        f'<b>{prog_name}</b><br>'
                        f'<span style="color:#666;font-size:12px;margin-left:14px;">'
                        f'{bal_fmt} pts · {status}</span></div>',
                        unsafe_allow_html=True
                    )
                with col_edit:
                    if st.button("✏️", key=f"edit_{prog_name}", help=f"Edit {prog_name}"):
                        st.session_state.editing = prog_name
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{prog_name}", help=f"Remove {prog_name}"):
                        del st.session_state.profile[prog_name]
                        if st.session_state.editing == prog_name:
                            st.session_state.editing = None
                        st.rerun()

    if not profile:
        st.info("No programs added yet.")

    st.markdown("---")

    # ── Add program ──
    st.markdown("**Add a program**")
    add_cat  = st.selectbox("Category", list(PROGRAMS.keys()), key="add_cat")
    available = [p for p in PROGRAMS[add_cat] if p not in profile]
    if available:
        add_prog   = st.selectbox("Program", available, key="add_prog")
        prog_data  = PROGRAMS[add_cat][add_prog]
        add_bal    = st.number_input("Points balance", min_value=0, step=1000, value=0, key="add_bal")
        add_status = st.selectbox("Your status", prog_data["statuses"], key="add_status")
        if st.button("➕ Add to profile", use_container_width=True):
            st.session_state.profile[add_prog] = {"balance": add_bal, "status": add_status}
            st.rerun()
    else:
        st.caption(f"All {add_cat} programs already added.")

    st.divider()

    # ── Trip ──
    st.markdown("### ✈️ Trip")
    origin      = st.text_input("From (city)",    value="San Francisco")
    origin_code = st.text_input("Airport code",   value="SFO", max_chars=4).upper()
    destination = st.text_input("To (city)",       value="Tokyo")
    dest_code   = st.text_input("Airport code ",  value="NRT", max_chars=4).upper()
    dates       = st.text_input("Travel dates",    value="June 10–20, 2026")
    nights      = st.number_input("Nights", min_value=1, max_value=30, value=5)
    cabin       = st.selectbox("Cabin",        ["economy", "premium economy", "business", "first"])
    hotel_style = st.selectbox("Hotel style",  ["budget", "standard", "luxury"])
    val_exp     = st.slider("Value ← → Experience", 1, 10, 5)

    st.divider()
    run = st.button("✈️ Find My Best Trip", type="primary", use_container_width=True)


# ── Build user data ──
def build_user_data():
    profile = st.session_state.profile
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
            if status != "None":
                airline_statuses[prog_name] = status
        elif cat == "Hotels":
            hotels[prog_name] = bal
            if status != "None":
                hotel_statuses[prog_name] = status
    return {
        "points":      {"credit_cards": credit_cards, "airline_miles": airlines, "hotel_points": hotels},
        "status":      {"airlines": airline_statuses, "hotels": hotel_statuses},
        "trip":        {"origin": f"{origin} ({origin_code})", "destination": f"{destination} ({dest_code})", "dates": dates, "nights": int(nights)},
        "preferences": {"cabin": cabin, "hotel_style": hotel_style, "value_vs_experience": val_exp},
    }


# ── Claude ──
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


# ── Profile summary (main panel) ──
def show_profile_summary():
    profile = st.session_state.profile
    if not profile:
        return
    st.markdown("#### Your loyalty profile")
    for cat_name, cat_progs in PROGRAMS.items():
        cat_entries = {k: v for k, v in profile.items() if k in cat_progs}
        if not cat_entries:
            continue
        st.markdown(f"**{cat_name}**")
        rows = ""
        for prog_name, entry in cat_entries.items():
            color  = ALL_PROGRAMS[prog_name]["color"]
            status = entry["status"]
            sc     = "#2d7a3a" if status not in ["None","Standard"] else "#999"
            rows  += f'<div style="display:flex;gap:10px;align-items:center;padding:6px 0;border-bottom:1px solid #f5f5f5;font-size:13px;"><span style="width:10px;height:10px;border-radius:50%;background:{color};flex-shrink:0;"></span><span style="min-width:160px;font-weight:500;color:#111;">{prog_name}</span><span style="min-width:80px;font-weight:600;color:#111;">{entry["balance"]:,}</span><span style="color:{sc};font-size:12px;">{status}</span></div>'
        st.markdown(f'<div style="background:#fff;border:1px solid #e8e8e8;border-radius:10px;padding:.75rem 1rem;margin-bottom:.75rem;">{rows}</div>', unsafe_allow_html=True)


# ── Result renderer ──
def render(r, is_mock=False):
    if is_mock:
        st.markdown('<div class="mock-banner">🧪 Mock mode — sample data. Turn off mock mode and add your API key for a real strategy.</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="plain-english">💡 <b>In plain English:</b> {r.get("plain_english","")}</div>', unsafe_allow_html=True)

    rd = r.get("route_display", {}); hero = r.get("hero", {})
    st.markdown(f"""
    <div class="hero">
      <div class="hero-top">
        <div class="route"><span>{rd.get("origin",origin)}</span><div class="route-line"></div>✈️<div class="route-line"></div><span>{rd.get("destination",destination)}</span></div>
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
        st.markdown(f'<div class="card"><p class="card-head">✈️ Your flight</p><div class="dr"><span class="dr-l">Airline</span><span class="dr-v">{f.get("airline","—")}</span></div><div class="dr"><span class="dr-l">Book through</span><span class="dr-v">{f.get("book_via","—")}</span></div><div class="dr"><span class="dr-l">Points used</span><span class="dr-v">{f.get("points","—")}</span></div><div class="dr"><span class="dr-l">Cash fees</span><span class="dr-v">{f.get("cash_fees","—")}</span></div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="card"><p class="card-head">🏨 Your hotel</p><div class="dr"><span class="dr-l">Property</span><span class="dr-v">{h.get("name","—")}</span></div><div class="dr"><span class="dr-l">Book through</span><span class="dr-v">{h.get("book_via","—")}</span></div><div class="dr"><span class="dr-l">Points used</span><span class="dr-v">{h.get("points","—")}</span></div><div class="dr"><span class="dr-l">5th night</span><span class="dr-v">{h.get("fifth_night","—")}</span></div></div>', unsafe_allow_html=True)

    perks = r.get("perks", [])
    if perks:
        st.markdown(f'<div class="perks-row">{"".join(f"<div class=chip>✓ {p}</div>" for p in perks)}</div>', unsafe_allow_html=True)

    steps = r.get("booking_steps", [])
    if steps:
        sh = "".join(f'<div class="step"><div class="step-num">{i+1}</div><div><p class="step-title">{s["title"]}</p><p class="step-desc">{s["desc"]}</p></div></div>' for i, s in enumerate(steps))
        st.markdown(f'<div class="steps-card"><p class="card-head">📋 How to book</p>{sh}</div>', unsafe_allow_html=True)

    si = r.get("status", {})
    if si.get("airline") or si.get("hotel"):
        sc1, sc2 = st.columns(2)
        if si.get("airline"): sc1.info(f"✈️ {si['airline']}")
        if si.get("hotel"):   sc2.info(f"🏨 {si['hotel']}")
        st.markdown("<br>", unsafe_allow_html=True)

    alts = r.get("alternatives", [])
    if alts:
        st.markdown('<p class="section-title">🔄 Other options</p>', unsafe_allow_html=True)
        for a in alts:
            trade = f'<p class="alt-trade">⚖️ {a["trade"]}</p>' if a.get("trade") else ""
            st.markdown(f'<div class="alt-chip"><p class="alt-name">{a.get("name","")}</p><p class="alt-desc">{a.get("desc","")}</p>{trade}</div>', unsafe_allow_html=True)

    cc = r.get("card", {})
    if cc.get("name"):
        bonus = f'<p class="cc-bonus">🎁 {cc["bonus"]}</p>' if cc.get("bonus") else ""
        st.markdown(f'<div class="cc-wrap"><p class="cc-eye">💳 Want to upgrade?</p><p class="cc-name">{cc["name"]}</p>{bonus}<p class="cc-why">{cc.get("why","")}</p></div>', unsafe_allow_html=True)

    st.caption(f"🎯 Confidence: {r.get('confidence','')}")


# ── Main ──
st.markdown("# ✈️ AI Loyalty Optimizer")
st.caption("Set up your loyalty profile once in the sidebar — then just enter your trip.")

if run:
    profile = st.session_state.profile
    if not profile:
        st.warning("Add at least one loyalty program to your profile in the sidebar first.")
    elif mock_mode:
        show_profile_summary()
        st.divider()
        render(MOCK, is_mock=True)
    else:
        if not api_key:
            st.error("Add your Anthropic API key in the sidebar, or turn on mock mode.")
        else:
            show_profile_summary()
            st.divider()
            with st.spinner("Finding your best trip…"):
                try:
                    result = call_claude(api_key, build_user_data())
                    render(result, is_mock=False)
                except json.JSONDecodeError as e:
                    st.error(f"Unexpected response from Claude: {e}")
                except anthropic.AuthenticationError:
                    st.error("Invalid API key — check console.anthropic.com")
                except anthropic.APIError as e:
                    st.error(f"API error: {e}")
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
else:
    profile = st.session_state.profile
    if profile:
        show_profile_summary()
        st.info("👈 Enter your trip details in the sidebar and click **Find My Best Trip**.")
    else:
        st.markdown("""
<div style="background:#fff;border:1px solid #e8e8e8;border-radius:12px;padding:1.25rem;max-width:480px;">
  <p style="font-size:11px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px;">Getting started</p>
  <div style="display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #f5f5f5;">
    <div style="width:28px;height:28px;min-width:28px;border-radius:50%;background:#e8f0fe;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:#1a56cc;">1</div>
    <div><p style="font-size:13px;font-weight:600;color:#111;margin-bottom:2px;">Set up your loyalty profile</p><p style="font-size:12px;color:#666;">Add your programs, balances, and status levels. You only do this once — they stay saved for every trip.</p></div>
  </div>
  <div style="display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #f5f5f5;">
    <div style="width:28px;height:28px;min-width:28px;border-radius:50%;background:#e8f0fe;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:#1a56cc;">2</div>
    <div><p style="font-size:13px;font-weight:600;color:#111;margin-bottom:2px;">Enter your trip</p><p style="font-size:12px;color:#666;">Where are you going, when, and what cabin and hotel style do you want?</p></div>
  </div>
  <div style="display:flex;gap:12px;padding:8px 0;">
    <div style="width:28px;height:28px;min-width:28px;border-radius:50%;background:#e8f0fe;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:#1a56cc;">3</div>
    <div><p style="font-size:13px;font-weight:600;color:#111;margin-bottom:2px;">Get your optimized strategy</p><p style="font-size:12px;color:#666;">Claude finds the best combination of your points for flights and hotels, in plain English.</p></div>
  </div>
</div>
""", unsafe_allow_html=True)
