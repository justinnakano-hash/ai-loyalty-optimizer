import streamlit as st
import anthropic
import json
import re

st.set_page_config(
    page_title="AI Loyalty Optimizer",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ AI Loyalty Optimizer")
st.caption("Enter your points, status, and trip details — get an AI-optimized travel strategy.")

# ──────────────────────────────────────────────
# SIDEBAR: Inputs
# ──────────────────────────────────────────────
with st.sidebar:
    st.header("🔑 API Key")
    api_key = st.text_input("Anthropic API Key", type="password",
                            placeholder="sk-ant-...",
                            help="Get yours at console.anthropic.com")

    st.divider()
    st.header("🎯 Your Profile")

    # --- Points ---
    st.subheader("Points Balances")
    amex = st.number_input("Amex Membership Rewards", min_value=0, step=1000, value=80000)
    chase = st.number_input("Chase Ultimate Rewards", min_value=0, step=1000, value=60000)
    capital_one = st.number_input("Capital One Miles", min_value=0, step=1000, value=0)

    st.markdown("**Airline Miles** (optional)")
    airline_programs = ["United MileagePlus", "Delta SkyMiles", "AA AAdvantage",
                        "Alaska Mileage Plan", "Southwest Rapid Rewards",
                        "Air Canada Aeroplan", "British Airways Avios",
                        "Singapore KrisFlyer", "Other"]
    airline_program = st.selectbox("Airline program", ["(none)"] + airline_programs)
    airline_miles = 0
    if airline_program != "(none)":
        airline_miles = st.number_input(f"{airline_program} balance", min_value=0, step=1000, value=0)

    st.markdown("**Hotel Points** (optional)")
    hotel_programs = ["Marriott Bonvoy", "Hilton Honors", "World of Hyatt",
                      "IHG One Rewards", "Wyndham Rewards"]
    hotel_program = st.selectbox("Hotel program", ["(none)"] + hotel_programs)
    hotel_pts = 0
    if hotel_program != "(none)":
        hotel_pts = st.number_input(f"{hotel_program} balance", min_value=0, step=5000, value=0)

    st.divider()

    # --- Status ---
    st.subheader("Elite Status")
    airline_statuses = ["None", "Silver / Basic", "Gold / Mid-tier",
                        "Platinum / Top-tier", "Executive Platinum / 1K / Diamond"]
    airline_status = st.selectbox("Airline status", airline_statuses)

    hotel_statuses = ["None", "Silver", "Gold", "Platinum",
                      "Titanium / Diamond / Globalist"]
    hotel_status = st.selectbox("Hotel status", hotel_statuses)

    st.divider()

    # --- Trip ---
    st.subheader("Trip Details")
    origin = st.text_input("Origin airport", value="SFO", max_chars=4).upper()
    destination = st.text_input("Destination airport", value="NRT", max_chars=4).upper()
    dates = st.text_input("Travel dates", value="June 10–20, 2026")
    nights = st.number_input("Nights", min_value=1, max_value=30, value=5)

    st.divider()

    # --- Preferences ---
    st.subheader("Preferences")
    cabin = st.selectbox("Cabin class",
                         ["economy", "premium economy", "business", "first"])
    hotel_style = st.selectbox("Hotel style", ["budget", "standard", "luxury"])
    val_exp = st.slider("Value ← → Experience", min_value=1, max_value=10, value=5,
                        help="1 = maximize points value, 10 = maximize experience")

    st.divider()
    run = st.button("🚀 Optimize My Trip", type="primary", use_container_width=True)


# ──────────────────────────────────────────────
# BUILD USER DATA
# ──────────────────────────────────────────────
def build_user_data() -> dict:
    airline_miles_dict = {}
    if airline_program != "(none)" and airline_miles > 0:
        airline_miles_dict[airline_program] = airline_miles

    hotel_pts_dict = {}
    if hotel_program != "(none)" and hotel_pts > 0:
        hotel_pts_dict[hotel_program] = hotel_pts

    return {
        "points": {
            "amex": amex,
            "chase": chase,
            "capital_one": capital_one,
            "airline_miles": airline_miles_dict,
            "hotel_points": hotel_pts_dict,
        },
        "status": {
            "airline": airline_status,
            "hotel": hotel_status,
        },
        "trip": {
            "origin": origin,
            "destination": destination,
            "dates": dates,
            "nights": nights,
        },
        "preferences": {
            "cabin": cabin,
            "hotel_style": hotel_style,
            "value_vs_experience": val_exp,
        },
    }


# ──────────────────────────────────────────────
# CLAUDE CALL
# ──────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert travel strategist and loyalty optimization engine.
Given user data, generate the most optimal travel strategy.
Optimize for: points efficiency, experience quality, status perks, and simplicity.
Always return ONLY valid JSON, no markdown, no extra text."""

def build_prompt(user_data: dict) -> str:
    return f"""Given the user data below, generate the most optimal travel strategy.

USER DATA:
{json.dumps(user_data, indent=2)}

Return a JSON response with EXACTLY this structure:
{{
  "best_strategy": {{
    "summary": "",
    "flight": {{
      "route": "",
      "program": "",
      "points_required": "",
      "transfer": ""
    }},
    "hotel": {{
      "name": "",
      "program": "",
      "points_per_night": "",
      "total_points": ""
    }},
    "perks": [],
    "booking_steps": [],
    "reasoning": ""
  }},
  "alternatives": [
    {{"name": "", "description": "", "tradeoff": ""}}
  ],
  "status_impact": {{
    "airline": "",
    "hotel": ""
  }},
  "credit_card_recommendation": {{
    "card": "",
    "bonus": "",
    "reason": ""
  }},
  "confidence": ""
}}

Do NOT assume real-time availability. Be realistic and concise."""


def call_claude(api_key: str, user_data: dict) -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": build_prompt(user_data)}
        ]
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ──────────────────────────────────────────────
# DISPLAY RESULTS
# ──────────────────────────────────────────────
def show_result(data: dict):
    best = data.get("best_strategy", {})
    alts = data.get("alternatives", [])
    status_impact = data.get("status_impact", {})
    cc = data.get("credit_card_recommendation", {})
    confidence = data.get("confidence", "")

    st.subheader("🏆 Best Strategy")
    st.markdown(f"> {best.get('summary', '')}")

    col_flight, col_hotel = st.columns(2)

    with col_flight:
        st.markdown("#### ✈️ Flight")
        flight = best.get("flight", {})
        st.metric("Route", flight.get("route", "—"))
        st.metric("Program", flight.get("program", "—"))
        st.metric("Points Required", flight.get("points_required", "—"))
        if flight.get("transfer"):
            st.info(f"🔄 {flight['transfer']}")

    with col_hotel:
        st.markdown("#### 🏨 Hotel")
        hotel = best.get("hotel", {})
        st.metric("Hotel", hotel.get("name", "—"))
        st.metric("Program", hotel.get("program", "—"))
        st.metric("Points / Night", hotel.get("points_per_night", "—"))
        st.metric(f"Total ({nights} nights)", hotel.get("total_points", "—"))

    perks = best.get("perks", [])
    if perks:
        st.markdown("#### 🎁 Perks Unlocked")
        for p in perks:
            st.markdown(f"- ✅ {p}")

    steps = best.get("booking_steps", [])
    if steps:
        st.markdown("#### 📋 Booking Steps")
        for i, step in enumerate(steps, 1):
            st.markdown(f"**{i}.** {step}")

    if best.get("reasoning"):
        with st.expander("💡 Reasoning"):
            st.write(best["reasoning"])

    st.divider()

    if status_impact.get("airline") or status_impact.get("hotel"):
        st.subheader("📊 Status Impact")
        c1, c2 = st.columns(2)
        if status_impact.get("airline"):
            c1.info(f"✈️ **Airline:** {status_impact['airline']}")
        if status_impact.get("hotel"):
            c2.info(f"🏨 **Hotel:** {status_impact['hotel']}")
        st.divider()

    if alts:
        st.subheader("🔄 Alternatives")
        for alt in alts:
            with st.expander(f"**{alt.get('name', 'Option')}**"):
                st.write(alt.get("description", ""))
                if alt.get("tradeoff"):
                    st.caption(f"⚖️ Tradeoff: {alt['tradeoff']}")
        st.divider()

    if cc.get("card"):
        st.subheader("💳 Credit Card Recommendation")
        st.markdown(f"**{cc['card']}**")
        if cc.get("bonus"):
            st.success(f"🎁 {cc['bonus']}")
        if cc.get("reason"):
            st.write(cc["reason"])
        st.divider()

    if confidence:
        st.caption(f"🎯 Confidence: {confidence}")

    with st.expander("🔍 Raw JSON response"):
        st.json(data)


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
if run:
    if not api_key:
        st.error("Please enter your Anthropic API key in the sidebar.")
    elif not origin or not destination:
        st.error("Please enter origin and destination airports.")
    else:
        user_data = build_user_data()
        with st.spinner("Calling Claude… crunching your points across programs"):
            try:
                result = call_claude(api_key, user_data)
                st.success("Strategy generated!")
                show_result(result)
            except json.JSONDecodeError as e:
                st.error(f"Claude returned invalid JSON: {e}")
            except anthropic.AuthenticationError:
                st.error("Invalid API key. Check your key at console.anthropic.com")
            except anthropic.APIError as e:
                st.error(f"Anthropic API error: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
else:
    st.info("👈 Enter your API key and travel details in the sidebar, then click **Optimize My Trip**.")
    st.markdown("""
**What this app does:**
- Analyzes your points across Amex, Chase, Capital One, airlines, and hotels
- Factors in your elite status for perks and upgrades
- Calls Claude directly — no backend server needed
- Recommends the most efficient use of your points for flights + hotel
- Suggests credit cards if you're short on points
- Provides step-by-step booking instructions
    """)
