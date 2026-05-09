import streamlit as st
import anthropic
import json
import re

st.set_page_config(
    page_title="AI Loyalty Optimizer",
    page_icon="✈️",
    layout="wide",
)

# ── Custom CSS ──
st.markdown("""
<style>
.card {
    background: #ffffff;
    border: 1px solid #e8e8e8;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}
.card-dark {
    background: #f7f7f7;
    border: 1px solid #e8e8e8;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}
.card-highlight {
    background: #f0f7ff;
    border: 2px solid #a8d0f5;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}
.metric-box {
    background: #f7f7f7;
    border-radius: 8px;
    padding: 0.75rem 1rem;
}
.metric-label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 4px; }
.metric-value { font-size: 18px; font-weight: 600; color: #111; margin: 0; }
.metric-sub   { font-size: 12px; color: #888; margin: 2px 0 0; }
.row-item {
    display: flex;
    justify-content: space-between;
    padding: 7px 0;
    border-bottom: 1px solid #f0f0f0;
    font-size: 14px;
}
.row-item:last-child { border-bottom: none; }
.row-label { color: #666; }
.row-value  { font-weight: 500; color: #111; text-align: right; max-width: 60%; }
.perk-item  { display: flex; align-items: flex-start; gap: 8px; padding: 5px 0; font-size: 14px; color: #444; }
.step-item  { display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px solid #f0f0f0; font-size: 14px; color: #444; align-items: flex-start; }
.step-item:last-child { border-bottom: none; }
.step-num   { background: #f0f0f0; border-radius: 50%; width: 24px; height: 24px; min-width: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: #333; }
.badge-best { display: inline-block; background: #e6f4ea; color: #2d7a3a; font-size: 12px; font-weight: 500; padding: 3px 12px; border-radius: 20px; margin-bottom: 10px; }
.badge-rec  { display: inline-block; background: #e8f0fe; color: #1a56cc; font-size: 12px; font-weight: 500; padding: 3px 12px; border-radius: 20px; margin-bottom: 10px; }
.badge-mock { display: inline-block; background: #fff3e0; color: #e65100; font-size: 12px; font-weight: 500; padding: 3px 12px; border-radius: 20px; margin-bottom: 10px; }
.section-title { font-size: 13px; font-weight: 600; color: #333; text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 12px; }
.alt-card   { background: #f7f7f7; border-radius: 8px; padding: 0.85rem 1rem; margin-bottom: 8px; }
.alt-name   { font-size: 14px; font-weight: 600; color: #111; margin: 0 0 4px; }
.alt-desc   { font-size: 13px; color: #555; margin: 0 0 4px; }
.alt-trade  { font-size: 12px; color: #999; margin: 0; }
.confidence { font-size: 12px; color: #aaa; text-align: right; margin-top: 0.5rem; }
.mock-banner {
    background: #fff3e0;
    border: 1px solid #ffcc80;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    font-size: 13px;
    color: #e65100;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)


# ── Mock response (realistic fake data — no API call) ──
MOCK_RESPONSE = {
    "best_strategy": {
        "summary": "Transfer Chase UR to Aeroplan and fly ANA Business direct. Use Amex MR for a Marriott mid-tier hotel with the 5th night free.",
        "flight": {
            "route": "SFO → NRT (ANA direct, ~11 hrs)",
            "program": "Air Canada Aeroplan",
            "points_required": "60,000 pts",
            "transfer": "Transfer Chase UR → Aeroplan at 1:1 (instant). No fuel surcharges on ANA via Aeroplan."
        },
        "hotel": {
            "name": "Courtyard Tokyo Ginza",
            "program": "Marriott Bonvoy",
            "points_per_night": "30,000 pts",
            "total_points": "96,000 pts (5th night free)"
        },
        "perks": [
            "Lie-flat business class seat on ANA — one of the best products on this route",
            "No fuel surcharges when booking ANA via Aeroplan",
            "ANA lounge access at NRT on arrival",
            "5th hotel night free with Bonvoy consecutive award stay",
            "80,000 Amex MR points left over for a future trip"
        ],
        "booking_steps": [
            "Create a free Aeroplan account at aeroplan.com",
            "Transfer 60,000 Chase UR → Aeroplan (1:1, usually instant)",
            "Search ANA Business award SFO–NRT on aeroplan.com for June 10",
            "Book and pay ~$150 in taxes and fees",
            "Transfer 80,000 Amex MR → Marriott Bonvoy (becomes ~96,000 pts at 1:1.2)",
            "Search Marriott award stays in Tokyo Ginza for June 10–15",
            "Book 5 consecutive nights to trigger the free 5th night benefit"
        ],
        "reasoning": "Aeroplan is the best-value program for ANA Business on this route — it prices at 60k one-way versus 80k+ on other programs, with no fuel surcharges. Your Amex transfer to Bonvoy at 1:1.2 gives you 96k points which exactly covers 4 paid nights + 1 free at the Courtyard Ginza."
    },
    "alternatives": [
        {
            "name": "United MileagePlus (simpler)",
            "description": "Transfer Chase UR directly to United and book ANA or United Polaris. Easier to search but costs 80,000 miles one-way.",
            "tradeoff": "Burns 20,000 more points for the same seat"
        },
        {
            "name": "Amex → ANA Mileage Club (best round-trip value)",
            "description": "Transfer Amex MR to ANA directly at 1:1. ANA prices round-trip Business at ~88,000 miles — exceptional value if you want both directions covered.",
            "tradeoff": "Requires ANA account; award space on own metal can be limited"
        },
        {
            "name": "Cash hotel + save all points",
            "description": "Book a great Tokyo hotel on cash (~$250–350/night) and save all 80k Amex for a future trip or second business class seat.",
            "tradeoff": "Higher out-of-pocket but more flexibility with your Amex balance"
        }
    ],
    "status_impact": {
        "airline": "No elite status means no complimentary upgrades on the ground. ANA Business class itself includes ANA lounge access at NRT on arrival.",
        "hotel": "Without Bonvoy status, standard room assignment applies. Consider the Bonvoy Brilliant card for automatic Gold status."
    },
    "credit_card_recommendation": {
        "card": "Marriott Bonvoy Brilliant (Amex)",
        "bonus": "185,000 bonus points after meeting spend — covers 2–3 luxury nights in Tokyo",
        "reason": "Closes your hotel points gap entirely. Also includes automatic Marriott Gold status, a $300 annual dining credit, and Priority Pass lounge access for SFO departure."
    },
    "confidence": "High for flight · Medium for hotel availability (book early)"
}


# ── Sidebar ──
with st.sidebar:
    st.markdown("### 🔑 API Key")
    api_key = st.text_input("Anthropic API Key", type="password",
                            placeholder="sk-ant-...",
                            help="Get yours at console.anthropic.com")

    st.divider()

    # Mock mode toggle — prominent placement
    mock_mode = st.toggle("🧪 Mock mode (no API calls)", value=True,
                          help="Use fake data to test the UI without burning API tokens")
    if mock_mode:
        st.caption("Mock mode on — results use sample data, no API key needed.")

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
    origin      = st.text_input("Origin airport",      value="SFO", max_chars=4).upper()
    destination = st.text_input("Destination airport", value="NRT", max_chars=4).upper()
    dates       = st.text_input("Travel dates",        value="June 10–20, 2026")
    nights      = st.number_input("Nights", min_value=1, max_value=30, value=5)

    st.divider()
    st.markdown("### 🎛️ Preferences")
    cabin       = st.selectbox("Cabin class",  ["economy", "premium economy", "business", "first"])
    hotel_style = st.selectbox("Hotel style",  ["budget", "standard", "luxury"])
    val_exp     = st.slider("Value ← → Experience", 1, 10, 5)

    st.divider()
    run = st.button("🚀 Optimize My Trip", type="primary", use_container_width=True)


# ── Data builder ──
def build_user_data():
    am, hp = {}, {}
    if airline_program != "(none)" and airline_miles > 0:
        am[airline_program] = airline_miles
    if hotel_program != "(none)" and hotel_pts > 0:
        hp[hotel_program] = hotel_pts
    return {
        "points":      {"amex": amex, "chase": chase, "capital_one": cap1,
                        "airline_miles": am, "hotel_points": hp},
        "status":      {"airline": airline_status, "hotel": hotel_status},
        "trip":        {"origin": origin, "destination": destination,
                        "dates": dates, "nights": int(nights)},
        "preferences": {"cabin": cabin, "hotel_style": hotel_style,
                        "value_vs_experience": val_exp},
    }


# ── Claude call ──
SYSTEM = ("You are an expert travel strategist and loyalty optimization engine. "
          "Return ONLY valid JSON, no markdown, no extra text.")

def build_prompt(d):
    return f"""Given the user data below, generate the most optimal travel strategy.
Optimize for: points efficiency, experience quality, status perks, and simplicity.

USER DATA:
{json.dumps(d, indent=2)}

Return EXACTLY this JSON structure:
{{
  "best_strategy": {{
    "summary": "",
    "flight":  {{"route":"","program":"","points_required":"","transfer":""}},
    "hotel":   {{"name":"","program":"","points_per_night":"","total_points":""}},
    "perks": [], "booking_steps": [], "reasoning": ""
  }},
  "alternatives": [{{"name":"","description":"","tradeoff":""}}],
  "status_impact": {{"airline":"","hotel":""}},
  "credit_card_recommendation": {{"card":"","bonus":"","reason":""}},
  "confidence": ""
}}
Do NOT assume real-time availability. Be realistic and concise."""

def call_claude(key, data):
    client = anthropic.Anthropic(api_key=key)
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1500,
        system=SYSTEM,
        messages=[{"role": "user", "content": build_prompt(data)}]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ── Render helpers ──
def row(label, value):
    st.markdown(f'<div class="row-item"><span class="row-label">{label}</span>'
                f'<span class="row-value">{value}</span></div>', unsafe_allow_html=True)

def metric_box(label, value, sub=""):
    sub_html = f'<p class="metric-sub">{sub}</p>' if sub else ""
    st.markdown(f'<div class="metric-box"><p class="metric-label">{label}</p>'
                f'<p class="metric-value">{value}</p>{sub_html}</div>', unsafe_allow_html=True)


# ── Result renderer ──
def show_result(data, is_mock=False):
    s    = data.get("best_strategy", {})
    f    = s.get("flight", {})
    h    = s.get("hotel",  {})
    alts = data.get("alternatives", [])
    si   = data.get("status_impact", {})
    cc   = data.get("credit_card_recommendation", {})

    # Mock banner
    if is_mock:
        st.markdown('<div class="mock-banner">🧪 Mock mode — this is sample data. Switch off mock mode and add your API key to get a real strategy.</div>',
                    unsafe_allow_html=True)

    # Hero
    badge = '<span class="badge-mock">🧪 Mock result</span>' if is_mock else '<span class="badge-best">✓ Best strategy</span>'
    st.markdown(f"""
    <div class="card">
        {badge}
        <h2 style="margin:0 0 4px;font-size:22px;">{origin} → {destination}</h2>
        <p style="color:#666;margin:0;font-size:14px;">{cabin.title()} class · {dates} · {int(nights)} nights</p>
        <p style="color:#444;margin:1rem 0 0;font-size:14px;font-style:italic;">{s.get("summary","")}</p>
    </div>""", unsafe_allow_html=True)

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1: metric_box("Points used (flight)", f.get("points_required","—"), f.get("program",""))
    with m2: metric_box("Points used (hotel)",  h.get("total_points","—"),    h.get("program",""))
    with m3: metric_box("Out of pocket", "~$150", "Taxes & fees")
    with m4: metric_box("Confidence", data.get("confidence","—"))

    st.markdown("<br>", unsafe_allow_html=True)

    # Flight + Hotel
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="card"><p class="section-title">✈️ Flight</p>', unsafe_allow_html=True)
        row("Airline",       f.get("route",           "—"))
        row("Book via",      f.get("program",         "—"))
        row("Transfer",      f.get("transfer",        "—"))
        row("Points needed", f.get("points_required", "—"))
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card"><p class="section-title">🏨 Hotel</p>', unsafe_allow_html=True)
        row("Property",     h.get("name",            "—"))
        row("Book via",     h.get("program",         "—"))
        row("Points/night", h.get("points_per_night","—"))
        row("Total points", h.get("total_points",    "—"))
        st.markdown('</div>', unsafe_allow_html=True)

    # Perks
    perks = s.get("perks", [])
    if perks:
        st.markdown('<div class="card"><p class="section-title">🎁 What\'s included</p>', unsafe_allow_html=True)
        for p in perks:
            st.markdown(f'<div class="perk-item"><span style="color:#2d7a3a;">✓</span><span>{p}</span></div>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Booking steps
    steps = s.get("booking_steps", [])
    if steps:
        st.markdown('<div class="card"><p class="section-title">📋 How to book</p>', unsafe_allow_html=True)
        for i, step in enumerate(steps, 1):
            st.markdown(f'<div class="step-item"><div class="step-num">{i}</div><span>{step}</span></div>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Reasoning
    if s.get("reasoning"):
        with st.expander("💡 Show reasoning"):
            st.write(s["reasoning"])

    # Status impact
    if si.get("airline") or si.get("hotel"):
        st.markdown('<div class="card-dark"><p class="section-title">📊 Status impact</p>', unsafe_allow_html=True)
        sc1, sc2 = st.columns(2)
        if si.get("airline"): sc1.info(f"✈️ {si['airline']}")
        if si.get("hotel"):   sc2.info(f"🏨 {si['hotel']}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Alternatives
    if alts:
        st.markdown('<div class="card-dark"><p class="section-title">🔄 Alternatives</p>', unsafe_allow_html=True)
        for a in alts:
            trade = f'<p class="alt-trade">⚖️ {a["tradeoff"]}</p>' if a.get("tradeoff") else ""
            st.markdown(f'<div class="alt-card"><p class="alt-name">{a.get("name","")}</p>'
                        f'<p class="alt-desc">{a.get("description","")}</p>{trade}</div>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Credit card
    if cc.get("card"):
        bonus = f'<p style="font-size:13px;color:#2d7a3a;margin:0 0 6px;">🎁 {cc["bonus"]}</p>' if cc.get("bonus") else ""
        st.markdown(f"""
        <div class="card-highlight">
            <span class="badge-rec">💳 Recommended card</span>
            <p style="font-size:16px;font-weight:600;margin:0 0 4px;">{cc["card"]}</p>
            {bonus}
            <p style="font-size:13px;color:#555;margin:0;">{cc.get("reason","")}</p>
        </div>""", unsafe_allow_html=True)

    # Confidence
    st.markdown(f'<p class="confidence">🎯 Confidence: {data.get("confidence","")}</p>',
                unsafe_allow_html=True)


# ── Main ──
st.markdown("# ✈️ AI Loyalty Optimizer")
st.caption("Fill in your details in the sidebar and click **Optimize My Trip**.")

if run:
    if mock_mode:
        # Return fake data instantly — zero API calls
        show_result(MOCK_RESPONSE, is_mock=True)

    else:
        if not api_key:
            st.error("Please enter your Anthropic API key in the sidebar, or switch on mock mode to test the UI.")
        elif not origin or not destination:
            st.error("Please enter origin and destination airports.")
        else:
            with st.spinner("Optimizing your trip…"):
                try:
                    result = call_claude(api_key, build_user_data())
                    show_result(result, is_mock=False)
                except json.JSONDecodeError as e:
                    st.error(f"Claude returned invalid JSON: {e}")
                except anthropic.AuthenticationError:
                    st.error("Invalid API key — check console.anthropic.com")
                except anthropic.APIError as e:
                    st.error(f"Anthropic API error: {e}")
                except Exception as e:
                    st.error(f"Unexpected error: {e}")
else:
    st.markdown("""
<div class="card" style="max-width:540px;">
    <p class="section-title">What this app does</p>
    <div class="perk-item"><span style="color:#2d7a3a;">✓</span><span>Analyzes your points across Amex, Chase, Capital One, airlines, and hotels</span></div>
    <div class="perk-item"><span style="color:#2d7a3a;">✓</span><span>Factors in your elite status for perks and upgrades</span></div>
    <div class="perk-item"><span style="color:#2d7a3a;">✓</span><span>Recommends the most efficient use of your points for flights and hotel</span></div>
    <div class="perk-item"><span style="color:#2d7a3a;">✓</span><span>Suggests credit cards if you are short on points</span></div>
    <div class="perk-item"><span style="color:#2d7a3a;">✓</span><span>Provides step-by-step booking instructions</span></div>
    <br>
    <p style="font-size:13px;color:#e65100;margin:0;">🧪 Mock mode is on by default — test the full UI instantly with no API key needed.</p>
</div>
""", unsafe_allow_html=True)
