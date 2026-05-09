"""
metadata_refresh.py
────────────────────────────────────────────────────────────────
Runs once daily (or on demand) to populate metadata.json.
All users share this file — it contains zero user-specific data.

Run manually:     python metadata_refresh.py
Run on schedule:  add to cron, GitHub Actions, or call from app

Cost: ~$0.002 per run (one Claude call, ~1500 tokens)
────────────────────────────────────────────────────────────────
"""

import anthropic
import json
import os
from datetime import datetime, timezone
from pathlib import Path

METADATA_PATH = Path(__file__).parent / "metadata.json"
MODEL         = "claude-sonnet-4-5"   # Sonnet is fine for structured data — no need for Opus

SYSTEM = (
    "You are a loyalty program data specialist. "
    "Return ONLY valid JSON, no markdown, no extra text."
)

PROMPT = """Generate current loyalty program metadata for a travel optimizer app.
Return EXACTLY this JSON structure with realistic, up-to-date values:

{
  "generated_at": "ISO-8601 UTC timestamp",
  "point_valuations": {
    "Chase Ultimate Rewards":  {"cpp": 2.0, "notes": "Best via Hyatt/Aeroplan transfers"},
    "Amex Membership Rewards": {"cpp": 2.0, "notes": "Best via Air Canada/ANA/Avianca"},
    "Capital One Miles":       {"cpp": 1.7, "notes": "Best via Air Canada/Turkish"},
    "Citi ThankYou Points":    {"cpp": 1.7, "notes": "Best via Air France/Turkish"},
    "Bilt Rewards":            {"cpp": 2.1, "notes": "Best via Hyatt/AA — no transfer fee"},
    "United MileagePlus":      {"cpp": 1.3, "notes": "Saver awards, avoid dynamic pricing"},
    "Delta SkyMiles":          {"cpp": 1.2, "notes": "Volatile — book during flash sales"},
    "American AAdvantage":     {"cpp": 1.5, "notes": "Partner awards, avoid peak"},
    "Alaska Mileage Plan":     {"cpp": 1.6, "notes": "Cathay/Emirates sweet spots"},
    "Air Canada Aeroplan":     {"cpp": 1.8, "notes": "No fuel surcharges on partners"},
    "British Airways Avios":   {"cpp": 1.4, "notes": "Short-haul + AA domestic sweet spots"},
    "Singapore KrisFlyer":     {"cpp": 1.7, "notes": "Singapore Suites, ANA partner awards"},
    "Marriott Bonvoy":         {"cpp": 0.7, "notes": "Category 1-4 hotels only"},
    "Hilton Honors":           {"cpp": 0.5, "notes": "5th night free saves value"},
    "World of Hyatt":          {"cpp": 1.7, "notes": "Best hotel program — high value"},
    "IHG One Rewards":         {"cpp": 0.5, "notes": "Best at Point Breaks promos"},
    "Wyndham Rewards":         {"cpp": 0.9, "notes": "Vacasa vacation rentals sweet spot"}
  },
  "transfer_partners": {
    "Chase Ultimate Rewards": [
      {"to": "United MileagePlus",  "ratio": "1:1", "time": "instant"},
      {"to": "Air Canada Aeroplan", "ratio": "1:1", "time": "instant"},
      {"to": "World of Hyatt",      "ratio": "1:1", "time": "instant"},
      {"to": "Marriott Bonvoy",     "ratio": "1:1", "time": "instant"},
      {"to": "British Airways Avios","ratio": "1:1", "time": "instant"},
      {"to": "Singapore KrisFlyer", "ratio": "1:1", "time": "instant"}
    ],
    "Amex Membership Rewards": [
      {"to": "Air Canada Aeroplan",  "ratio": "1:1",   "time": "instant"},
      {"to": "Delta SkyMiles",       "ratio": "1:1",   "time": "instant"},
      {"to": "British Airways Avios","ratio": "1:1",   "time": "instant"},
      {"to": "Singapore KrisFlyer",  "ratio": "1:1",   "time": "instant"},
      {"to": "Marriott Bonvoy",      "ratio": "1:1.2", "time": "instant"}
    ],
    "Capital One Miles": [
      {"to": "Air Canada Aeroplan",  "ratio": "1:1",   "time": "instant"},
      {"to": "Turkish Miles&Smiles", "ratio": "1:1",   "time": "instant"},
      {"to": "British Airways Avios","ratio": "1:1",   "time": "instant"}
    ],
    "Citi ThankYou Points": [
      {"to": "Air Canada Aeroplan",  "ratio": "1:1",   "time": "instant"},
      {"to": "Turkish Miles&Smiles", "ratio": "1:1",   "time": "instant"},
      {"to": "Singapore KrisFlyer",  "ratio": "1:1",   "time": "instant"}
    ],
    "Bilt Rewards": [
      {"to": "World of Hyatt",       "ratio": "1:1",   "time": "instant"},
      {"to": "Air Canada Aeroplan",  "ratio": "1:1",   "time": "instant"},
      {"to": "American AAdvantage",  "ratio": "1:1",   "time": "instant"},
      {"to": "United MileagePlus",   "ratio": "1:1",   "time": "instant"}
    ]
  },
  "promotions": [
    {
      "id": "promo_001",
      "title": "Transfer bonus or sale fare — example",
      "description": "Short description of what the promo is and why it matters for travelers.",
      "type": "transfer_bonus",
      "programs_affected": ["Program A", "Program B"],
      "benefit": "e.g. 30% bonus points on transfer",
      "expires": "YYYY-MM-DD or null",
      "cash_beats_points": false,
      "tags": ["active", "hotel points"]
    }
  ],
  "cash_rate_benchmarks": {
    "business_class": {
      "transatlantic_avg":  {"low": 2800, "mid": 4500, "high": 8000, "currency": "USD"},
      "transpacific_avg":   {"low": 2400, "mid": 4000, "high": 7000, "currency": "USD"},
      "domestic_us_avg":    {"low": 350,  "mid": 600,  "high": 1200,  "currency": "USD"},
      "intra_europe_avg":   {"low": 300,  "mid": 550,  "high": 900,   "currency": "USD"}
    },
    "economy_class": {
      "transatlantic_avg":  {"low": 400,  "mid": 800,  "high": 1600,  "currency": "USD"},
      "transpacific_avg":   {"low": 350,  "mid": 700,  "high": 1400,  "currency": "USD"},
      "domestic_us_avg":    {"low": 80,   "mid": 200,  "high": 500,   "currency": "USD"}
    },
    "hotel_nightly": {
      "budget":   {"low": 80,   "mid": 130,  "high": 200,  "currency": "USD"},
      "standard": {"low": 180,  "mid": 280,  "high": 450,  "currency": "USD"},
      "luxury":   {"low": 400,  "mid": 700,  "high": 1500, "currency": "USD"}
    }
  },
  "cpp_thresholds": {
    "burn_points_if_cpp_above": 1.5,
    "pay_cash_if_cpp_below":    1.2,
    "notes": "Between 1.2 and 1.5 is a gray zone — consider cash vs points based on context"
  }
}

Fill in ALL fields with realistic current values. Include 3-6 real active promotions
(transfer bonuses, flash sales, double-points offers) that loyalty travelers would
currently find useful. Set generated_at to the current UTC time."""


def refresh_metadata() -> dict:
    """Call Claude once to generate fresh metadata. Returns the parsed dict."""
    client = anthropic.Anthropic()

    print(f"[{datetime.now(timezone.utc).isoformat()}] Calling Claude for metadata refresh...")
    msg = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": PROMPT}]
    )

    raw = msg.content[0].text.strip()
    # Strip any accidental markdown fences
    import re
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    data = json.loads(raw)

    # Stamp with actual refresh time regardless of what Claude put
    data["generated_at"]     = datetime.now(timezone.utc).isoformat()
    data["refresh_cost_usd"] = round(
        (msg.usage.input_tokens * 0.000003 +
         msg.usage.output_tokens * 0.000015), 5
    )

    return data


def save_metadata(data: dict) -> None:
    """Write metadata to disk as pretty-printed JSON."""
    METADATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"[{datetime.now(timezone.utc).isoformat()}] metadata.json written "
          f"({METADATA_PATH.stat().st_size // 1024}KB) "
          f"— cost: ${data.get('refresh_cost_usd', '?')}")


def load_metadata() -> dict:
    """
    Load metadata from disk.  Called by the Streamlit app on every session.
    Uses st.cache_data with a 24h TTL so the file is only read once per day
    per Streamlit worker process — not on every user rerun.

    Falls back to a minimal stub if the file doesn't exist yet.
    """
    if not METADATA_PATH.exists():
        return _stub_metadata()

    try:
        return json.loads(METADATA_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return _stub_metadata()


def is_stale(max_age_hours: int = 25) -> bool:
    """Return True if metadata is missing or older than max_age_hours."""
    if not METADATA_PATH.exists():
        return True
    try:
        data = json.loads(METADATA_PATH.read_text())
        ts   = datetime.fromisoformat(data["generated_at"])
        age  = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        return age > max_age_hours
    except Exception:
        return True


def _stub_metadata() -> dict:
    """Minimal fallback so the app works before the first refresh runs."""
    return {
        "generated_at": "not-yet-refreshed",
        "point_valuations": {
            "Chase Ultimate Rewards":  {"cpp": 2.0, "notes": "Best via Hyatt/Aeroplan"},
            "Amex Membership Rewards": {"cpp": 2.0, "notes": "Best via Aeroplan/ANA"},
            "Marriott Bonvoy":         {"cpp": 0.7, "notes": "Category 1-4 hotels"},
            "World of Hyatt":          {"cpp": 1.7, "notes": "Best hotel program"},
        },
        "transfer_partners": {},
        "promotions": [],
        "cash_rate_benchmarks": {
            "business_class": {
                "transpacific_avg": {"low": 2400, "mid": 4000, "high": 7000, "currency": "USD"}
            },
            "hotel_nightly": {
                "luxury": {"low": 400, "mid": 700, "high": 1500, "currency": "USD"}
            }
        },
        "cpp_thresholds": {
            "burn_points_if_cpp_above": 1.5,
            "pay_cash_if_cpp_below":    1.2,
            "notes": "Stub — run metadata_refresh.py to populate"
        }
    }


if __name__ == "__main__":
    # Run manually or from a cron job / GitHub Action
    try:
        data = refresh_metadata()
        save_metadata(data)
        print("Refresh complete.")
    except anthropic.APIError as e:
        print(f"API error during refresh: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"Claude returned invalid JSON: {e}")
        raise
