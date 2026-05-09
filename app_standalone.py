import streamlit as st
import anthropic
import json
import re

st.set_page_config(
    page_title="AI Loyalty Optimizer",
    page_icon="✈️",
    layout="wide",
)

# ── CSS ──
st.markdown("""
<style>
.plain-english {
    background:#e6f4ea; border-radius:10px; padding:.9rem 1.1rem;
    font-size:14px; color:#1e5c2a; line-height:1.65; margin-bottom:1.1rem;
}
.hero {
    border:1px solid #e8e8e8; border-radius:12px; overflow:hidden; margin-bottom:1rem;
}
.hero-top { padding:1.1rem 1.25rem; }
.route {
    font-size:19px; font-weight:600; color:#111;
    display:flex; align-items:center; gap:10px; margin-bottom:4px;
}
.route-line { flex:1; height:1px; background:#ddd; }
.tagline { font-size:13px; color:#666; }
.hero-bottom {
    display:grid; grid-template-columns:1fr 1fr 1fr;
    border-top:1px solid #e8e8e8;
}
.hero-stat { padding:.9rem 1.1rem; border-right:1px solid #e8e8e8; }
.hero-stat:last-child { border-right:none; }
.hs-label { font-size:11px; color:#999; text-transform:uppercase; letter-spacing:.05em; margin-bottom:3px; }
.hs-val   { font-size:18px; font-weight:600; color:#111; }
.hs-sub   { font-size:12px; color:#888; margin-top:2px; }
.pts-wrap {
    background:#fff; border:1px solid #e8e8e8; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem;
}
.pts-title { font-size:11px; font-weight:600; color:#999; text-transform:uppercase; letter-spacing:.05em; margin-bottom:10px; }
.pts-row   { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
.pts-row:last-of-type { margin-bottom:0; }
.pts-name  { font-size:13px; color:#111; min-width:110px; }
.pts-track { flex:1; height:8px; background:#f0f0f0; border-radius:4px; overflow:hidden; }
.pts-fill  { height:100%; border-radius:4px; }
.pts-amt   { font-size:12px; color:#888; min-width:90px; text-align:right; }
.legend    { display:flex; gap:16px; margin-top:10px; }
.legend-item { font-size:11px; color:#999; display:flex; align-items:center; gap:5px; }
.legend-dot  { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.two-col { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1rem; }
.card {
    background:#fff; border:1px solid #e8e8e8; border-radius:12px; padding:1rem 1.25rem;
}
.card-head {
    font-size:11px; font-weight:600; color:#999; text-transform:uppercase;
    letter-spacing:.05em; margin-bottom:10px; display:flex; align-items:center; gap:6px;
}
.dr { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #f0f0f0; font-size:13px; }
.dr:last-child { border-bottom:none; }
.dr-l { color:#666; }
.dr-v { font-weight:500; color:#111; text-align:right; }
.perks-row { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:1rem; }
.chip {
    background:#f5f5f5; border:1px solid #e8e8e8; border-radius:20px;
    padding:5px 12px; font-size:12px; color:#555; display:flex; align-items:center; gap:5px;
}
.steps-card {
    background:#fff; border:1px solid #e8e8e8; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem;
}
.step { display:flex; gap:12px; padding:10px 0; border-bottom:1px solid #f5f5f5; align-items:flex-start; }
.step:last-child { border-bottom:none; }
.step-num {
    width:28px; height:28px; min-width:28px; border-radius:50%;
    background:#e8f0fe; display:flex; align-items:center; justify-content:center;
    font-size:12px; font-weight:600; color:#1a56cc;
}
.step-title { font-size:13px; font-weight:600; color:#111; margin-bottom:3px; }
.step-desc  { font-size:12px; color:#666; line-height:1.55; }
.alt-chip {
    background:#f7f7f7; border:1px solid #e8e8e8; border-radius:10px;
    padding:.75rem 1rem; margin-bottom:8px;
}
.alt-name  { font-size:13px; font-weight:600; color:#111; margin-bottom:3px; }
.alt-desc  { font-size:12px; color:#555; margin-bottom:3px; }
.alt-trade { font-size:12px; color:#aaa; }
.cc-wrap {
    background:#f0f7ff; border:2px solid #a8d0f5; border-radius:12px;
    padding:1rem 1.25rem; margin-bottom:1rem;
}
.cc-eye    { font-size:11px; color:#1a56cc; font-weight:600; text-transform:uppercase; letter-spacing:.05em; margin-bottom:6px; }
.cc-name   { font-size:15px; font-weight:600; color:#111; margin-bottom:4px; }
.cc-bonus  { font-size:13px; color:#2d7a3a; margin-bottom:6px; }
.cc-why    { font-size:13px; color:#555; }
.mock-banner {
    background:#fff3e0; border:1px solid #ffcc80; border-radius:8px;
    padding:.6rem 1rem; font-size:13px; color:#e65100; margin-bottom:1rem;
}
.section-title {
    font-size:11px; font-weight:600; color:#999; text-transform:uppercase;
    letter-spacing:.05em; margin-bottom:10px;
}
</style>
""", unsafe_allow_html=True)

# ── Mock data ──
MOCK = {
    "plain_english": "Use your Chase points for a lie-flat business class seat on ANA — one of the best flights in the world on this route. Transfer your Amex points to cover 4 hotel nights in central Tokyo, and the 5th night is free. Total out of pocket: about $150 in taxes.",
    "route_display": {"origin": "San Francisco", "destination": "Tokyo"},
    "hero": {"flight_pts": "60,000 Chase pts", "hotel_nights": "4 nights paid, 5th free", "cash": "~$150"},
    "points_bars": [
        {"name": "Chase UR",     "pct": 100, "color": "#378ADD", "label": "60k → flight"},
        {"name": "Amex MR",      "pct": 100, "color": "#1D9E75", "label": "80k → hotel"},
        {"name": "Left over",    "pct": 20,  "color": "#1D9E75", "label": "~16k saved"},
    ],
    "flight": {"airline": "ANA (direct)", "book_via": "Air Canada Aeroplan", "points": "60,000 Chase UR", "cash_fees": "~$150"},
    "hotel":  {"name": "Courtyard Tokyo Ginza", "book_via": "Marriott Bonvoy", "points": "~96,000 Bonvoy", "fifth_night": "Free"},
    "perks": ["Lie-flat bed", "Premium dining", "Airport lounge", "5th night free", "No fuel surcharges"],
    "booking_steps": [
        {"title": "Create a free Aeroplan account",
         "desc": "Go to aeroplan.com and sign up — takes 2 minutes. This is where you'll book your ANA flight."},
        {"title": "Move your Chase points to Aeroplan",
         "desc": "In your Chase account, transfer 60,000 points to Aeroplan (instant). Then search ANA Business SFO → NRT on June 10."},
        {"title": "Move your Amex points to Marriott",
         "desc": "Transfer 80,000 Amex points to Marriott Bonvoy — you'll receive ~96,000 pts thanks to Amex's 20% bonus. Search Bonvoy for Tokyo Ginza."},
        {"title": "Book 5 nights to unlock the free night",
         "desc": "Book 5 consecutive award nights and Bonvoy automatically makes the 5th free. Pay ~$150 in flight taxes and you're done."},
    ],
    "alternatives": [
        {"name": "United MileagePlus (simpler)",
         "desc": "Transfer Chase UR directly to United and book ANA or Polaris Business. Easier to search but costs ~80,000 miles.",
         "trade": "Burns 20,000 more points for the same seat"},
        {"name": "Amex → ANA Mileage Club (best round-trip value)",
         "desc": "Transfer Amex MR directly to ANA at 1:1. Round-trip Business is ~88,000 miles — exceptional value.",
         "trade": "Requires ANA account; own-metal award space can be limited"},
    ],
    "card": {
        "name": "Marriott Bonvoy Brilliant (Amex)",
        "bonus": "185,000 bonus points — enough for 2–3 nights at the St. Regis Tokyo",
        "why": "This one card closes the gap to a luxury hotel. Also gets you Gold status, a $300 dining credit, and lounge access at SFO.",
    },
    "confidence": "High for flight · Medium for hotel (book early)",
    "status": {"airline": "No elite status — but ANA Business includes lounge access at Tokyo on arrival.", "hotel": "Standard room assignment without status. The Bonvoy Brilliant card grants automatic Gold."},
}

# ── Sidebar ──
with st.sidebar:
    st.markdown("### 🔑 API Key")
    api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...",
                            help="Get yours at console.anthropic.com")
    st.divider()
    mock_mode = st.toggle("🧪 Mock mode (no API calls)", value=True,
                          help="Test the UI instantly without using any API tokens")
    if mock_mode:
        st.caption("Sample data shown — no API key needed.")
    st.divider()

    st.markdown("### 🎯 Points & Miles")
    amex  = st.number_input("Amex Membership Rewards", min_value=0, step=1000, value=80000)
    chase = st.number_input("Chase Ultimate Rewards",  min_value=0, step=1000, value=60000)
    cap1  = st.number_input("Capital One Miles",       min_value=0, step=1000, value=0)

    airline_program = st.selectbox("Airline program",
        ["(none)", "United MileagePlus", "Delta SkyMiles", "AA AAdvantage",
         "Alaska Mileage Plan", "Southwest Rapid Rewards", "Air Canada Aeroplan",
         "British Airways Avios", "Singapore KrisFlyer", "Other"])
    airline_miles = 0
    if airline_program != "(none)":
        airline_miles = st.number_input(f"{airline_program} balance", min_value=0, step=1000, value=0)

    hotel_program = st.selectbox("Hotel program",
        ["(none)", "Marriott Bonvoy", "Hilton Honors", "World of Hyatt",
         "IHG One Rewards", "Wyndham Rewards"])
    hotel_pts = 0
    if hotel_program != "(none)":
        hotel_pts = st.number_input(f"{hotel_program} balance", min_value=0, step=5000, value=0)

    st.divider()
    st.markdown("### ⭐ Elite Status")
    airline_status = st.selectbox("Airline status",
        ["None", "Silver / Basic", "Gold / Mid-tier",
         "Platinum / Top-tier", "Executive Platinum / 1K / Diamond"])
    hotel_status = st.selectbox("Hotel status",
        ["None", "Silver", "Gold", "Platinum", "Titanium / Diamond / Globalist"])

    st.divider()
    st.markdown("### ✈️ Trip Details")
    origin      = st.text_input("Origin city or airport", value="San Francisco").strip()
    destination = st.text_input("Destination city",       value="Tokyo").strip()
    origin_code = st.text_input("Origin airport code",    value="SFO", max_chars=4).upper()
    dest_code   = st.text_input("Destination code",       value="NRT", max_chars=4).upper()
    dates       = st.text_input("Travel dates",           value="June 10–20, 2026")
    nights      = st.number_input("Nights", min_value=1, max_value=30, value=5)

    st.divider()
    st.markdown("### 🎛️ Preferences")
    cabin       = st.selectbox("Cabin class",  ["economy", "premium economy", "business", "first"])
    hotel_style = st.selectbox("Hotel style",  ["budget", "standard", "luxury"])
    val_exp     = st.slider("Value ← → Experience", 1, 10, 5)

    st.divider()
    run = st.button("✈️ Find My Best Trip", type="primary", use_container_width=True)


# ── Data builder ──
def build_user_data():
    am, hp = {}, {}
    if airline_program != "(none)" and airline_miles > 0: am[airline_program] = airline_miles
    if hotel_program   != "(none)" and hotel_pts    > 0: hp[hotel_program]   = hotel_pts
    return {
        "points":      {"amex": amex, "chase": chase, "capital_one": cap1,
                        "airline_miles": am, "hotel_points": hp},
        "status":      {"airline": airline_status, "hotel": hotel_status},
        "trip":        {"origin": f"{origin} ({origin_code})", "destination": f"{destination} ({dest_code})",
                        "dates": dates, "nights": int(nights)},
        "preferences": {"cabin": cabin, "hotel_style": hotel_style, "value_vs_experience": val_exp},
    }

# ── Claude call ──
SYSTEM = ("You are an expert travel strategist. Return ONLY valid JSON, no markdown, no extra text.")

def build_prompt(d):
    return f"""Given the user data below, generate the most optimal travel strategy in plain, friendly English.

USER DATA:
{json.dumps(d, indent=2)}

Return EXACTLY this JSON (fill every field, keep language simple and jargon-free):
{{
  "plain_english": "One friendly sentence summarising the strategy — no jargon",
  "route_display": {{"origin": "{origin}", "destination": "{destination}"}},
  "hero": {{
    "flight_pts": "e.g. 60,000 Chase pts",
    "hotel_nights": "e.g. 4 nights paid, 5th free",
    "cash": "e.g. ~$150"
  }},
  "points_bars": [
    {{"name": "Program name", "pct": 80, "color": "#378ADD", "label": "60k → flight"}},
    {{"name": "Program name", "pct": 60, "color": "#1D9E75", "label": "80k → hotel"}},
    {{"name": "Left over",    "pct": 20, "color": "#1D9E75", "label": "~16k saved"}}
  ],
  "flight": {{"airline": "", "book_via": "", "points": "", "cash_fees": ""}},
  "hotel":  {{"name": "", "book_via": "", "points": "", "fifth_night": "Free or N/A"}},
  "perks": ["short plain-English perk", "..."],
  "booking_steps": [
    {{"title": "Short action title", "desc": "Plain English explanation of exactly what to do"}},
    ...
  ],
  "alternatives": [
    {{"name": "", "desc": "", "trade": ""}},
    ...
  ],
  "card": {{"name": "", "bonus": "", "why": ""}},
  "status": {{"airline": "", "hotel": ""}},
  "confidence": ""
}}
Use city names not airport codes. Keep every description friendly and simple. Do NOT assume real-time availability."""

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


# ── Render ──
def render(r, is_mock=False):

    if is_mock:
        st.markdown('<div class="mock-banner">🧪 Mock mode — sample data only. Turn off mock mode and add your API key for a real strategy.</div>', unsafe_allow_html=True)

    # Plain English summary
    st.markdown(f'<div class="plain-english">💡 <strong>In plain English:</strong> {r.get("plain_english","")}</div>', unsafe_allow_html=True)

    # Hero card
    rd   = r.get("route_display", {})
    hero = r.get("hero", {})
    st.markdown(f"""
    <div class="hero">
      <div class="hero-top">
        <div class="route">
          <span>{rd.get("origin", origin)}</span>
          <div class="route-line"></div>
          ✈️
          <div class="route-line"></div>
          <span>{rd.get("destination", destination)}</span>
        </div>
        <p class="tagline">{dates} · {cabin.title()} class · {int(nights)} nights</p>
      </div>
      <div class="hero-bottom">
        <div class="hero-stat"><p class="hs-label">Flight</p><p class="hs-val">{hero.get("flight_pts","—")}</p><p class="hs-sub">points used</p></div>
        <div class="hero-stat"><p class="hs-label">Hotel</p><p class="hs-val">{hero.get("hotel_nights","—")}</p><p class="hs-sub">award nights</p></div>
        <div class="hero-stat"><p class="hs-label">Cash needed</p><p class="hs-val">{hero.get("cash","—")}</p><p class="hs-sub">taxes &amp; fees</p></div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Points bars
    bars = r.get("points_bars", [])
    if bars:
        bars_html = "".join(f"""
        <div class="pts-row">
          <span class="pts-name">{b["name"]}</span>
          <div class="pts-track"><div class="pts-fill" style="width:{b["pct"]}%;background:{b["color"]};"></div></div>
          <span class="pts-amt">{b["label"]}</span>
        </div>""" for b in bars)
        st.markdown(f"""
        <div class="pts-wrap">
          <p class="pts-title">Your points at a glance</p>
          {bars_html}
          <div class="legend">
            <span class="legend-item"><span class="legend-dot" style="background:#378ADD;"></span>Flight</span>
            <span class="legend-item"><span class="legend-dot" style="background:#1D9E75;"></span>Hotel</span>
            <span class="legend-item"><span class="legend-dot" style="background:#E24B4A;"></span>Shortfall</span>
          </div>
        </div>""", unsafe_allow_html=True)

    # Flight + Hotel columns
    f = r.get("flight", {}); h = r.get("hotel", {})
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="card">
          <p class="card-head">✈️ Your flight</p>
          <div class="dr"><span class="dr-l">Airline</span><span class="dr-v">{f.get("airline","—")}</span></div>
          <div class="dr"><span class="dr-l">Book through</span><span class="dr-v">{f.get("book_via","—")}</span></div>
          <div class="dr"><span class="dr-l">Points used</span><span class="dr-v">{f.get("points","—")}</span></div>
          <div class="dr"><span class="dr-l">Cash fees</span><span class="dr-v">{f.get("cash_fees","—")}</span></div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="card">
          <p class="card-head">🏨 Your hotel</p>
          <div class="dr"><span class="dr-l">Property</span><span class="dr-v">{h.get("name","—")}</span></div>
          <div class="dr"><span class="dr-l">Book through</span><span class="dr-v">{h.get("book_via","—")}</span></div>
          <div class="dr"><span class="dr-l">Points used</span><span class="dr-v">{h.get("points","—")}</span></div>
          <div class="dr"><span class="dr-l">5th night</span><span class="dr-v">{h.get("fifth_night","—")}</span></div>
        </div>""", unsafe_allow_html=True)

    # Perk chips
    perks = r.get("perks", [])
    if perks:
        chips = "".join(f'<div class="chip">✓ {p}</div>' for p in perks)
        st.markdown(f'<div class="perks-row">{chips}</div>', unsafe_allow_html=True)

    # Booking steps
    steps = r.get("booking_steps", [])
    if steps:
        steps_html = "".join(f"""
        <div class="step">
          <div class="step-num">{i+1}</div>
          <div>
            <p class="step-title">{s["title"]}</p>
            <p class="step-desc">{s["desc"]}</p>
          </div>
        </div>""" for i, s in enumerate(steps))
        st.markdown(f'<div class="steps-card"><p class="card-head">📋 How to book</p>{steps_html}</div>', unsafe_allow_html=True)

    # Status impact
    si = r.get("status", {})
    if si.get("airline") or si.get("hotel"):
        c1, c2 = st.columns(2)
        if si.get("airline"): c1.info(f"✈️ {si['airline']}")
        if si.get("hotel"):   c2.info(f"🏨 {si['hotel']}")
        st.markdown("<br>", unsafe_allow_html=True)

    # Alternatives
    alts = r.get("alternatives", [])
    if alts:
        st.markdown('<p class="section-title">🔄 Other options</p>', unsafe_allow_html=True)
        for a in alts:
            trade = f'<p class="alt-trade">⚖️ {a["trade"]}</p>' if a.get("trade") else ""
            st.markdown(f"""
            <div class="alt-chip">
              <p class="alt-name">{a.get("name","")}</p>
              <p class="alt-desc">{a.get("desc","")}</p>
              {trade}
            </div>""", unsafe_allow_html=True)

    # Credit card
    cc = r.get("card", {})
    if cc.get("name"):
        st.markdown(f"""
        <div class="cc-wrap">
          <p class="cc-eye">💳 Want to upgrade your hotel?</p>
          <p class="cc-name">{cc["name"]}</p>
          <p class="cc-bonus">🎁 {cc.get("bonus","")}</p>
          <p class="cc-why">{cc.get("why","")}</p>
        </div>""", unsafe_allow_html=True)

    # Confidence
    st.caption(f"🎯 Confidence: {r.get('confidence','')}")


# ── Main ──
st.markdown("# ✈️ AI Loyalty Optimizer")
st.caption("Fill in your details in the sidebar and click **Find My Best Trip**.")

if run:
    if mock_mode:
        render(MOCK, is_mock=True)
    else:
        if not api_key:
            st.error("Add your Anthropic API key in the sidebar, or turn on mock mode to test the UI.")
        elif not origin or not destination:
            st.error("Please enter your origin and destination.")
        else:
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
    st.markdown("""
<div style="background:#fff;border:1px solid #e8e8e8;border-radius:12px;padding:1.25rem;max-width:540px;">
  <p style="font-size:11px;font-weight:600;color:#999;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px;">What this app does</p>
  <div style="display:flex;gap:8px;padding:5px 0;font-size:14px;color:#444;">✓ <span>Finds the best use of your points for flights and hotels</span></div>
  <div style="display:flex;gap:8px;padding:5px 0;font-size:14px;color:#444;">✓ <span>Explains everything in plain English — no jargon</span></div>
  <div style="display:flex;gap:8px;padding:5px 0;font-size:14px;color:#444;">✓ <span>Shows you exactly how to book, step by step</span></div>
  <div style="display:flex;gap:8px;padding:5px 0;font-size:14px;color:#444;">✓ <span>Suggests a credit card if you need more points</span></div>
  <div style="display:flex;gap:8px;padding:5px 0;font-size:14px;color:#444;">✓ <span>Visual points bar so you can see exactly what gets used</span></div>
  <p style="font-size:13px;color:#e65100;margin-top:10px;">🧪 Mock mode is on — click <strong>Find My Best Trip</strong> to preview the UI instantly.</p>
</div>
""", unsafe_allow_html=True)
