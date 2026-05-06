"""Cohort-aware trader — picks 3 longs per day using cohort intelligence
+ a compounding lesson loop.

Mirrors the architecture running publicly at chartlibrary.io/agent-trader.
Offline backtest over 19 trading days: this strategy beat passive SPY
by +1.6 percentage points and beat the no-memory baseline by +7.5pp.

Full walkthrough: https://chartlibrary.io/guides/build-ai-trading-agent-claude

Usage:
    export ANTHROPIC_API_KEY=...
    export CHARTLIBRARY_API_KEY=cl_...   # optional; Sandbox tier works without
    python cohort_aware_trader.py

This is a paper-trading example — it picks but doesn't execute. Wire in
your own broker SDK if you want to take live positions. Educational use;
not financial advice.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import date

import anthropic
import requests

API = "https://chartlibrary.io/api/v1"
HAIKU_MODEL = "claude-haiku-4-5-20251001"
N_PICKS = 3
HOLD_DAYS = 5
LESSONS_WINDOW = 5


# --------------------------------------------------------------------------
# Local memory (SQLite — keep it simple)
# --------------------------------------------------------------------------

def init_db(path: str = "agent.db") -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY,
            trade_date TEXT, symbol TEXT, conviction TEXT,
            cohort_score REAL, win_rate_5d REAL, median_5d REAL,
            reason TEXT, status TEXT DEFAULT 'open'
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY,
            lesson_date TEXT UNIQUE, lesson_text TEXT,
            portfolio_5d REAL, spy_5d REAL
        );
    """)
    db.commit()
    return db


def read_recent_lessons(db: sqlite3.Connection, n: int = LESSONS_WINDOW) -> list[dict]:
    rows = db.execute(
        "SELECT lesson_date, lesson_text, portfolio_5d, spy_5d "
        "FROM lessons ORDER BY lesson_date DESC LIMIT ?",
        (n,),
    ).fetchall()
    return [
        {"date": d, "lesson": t, "portfolio_5d": p, "spy_5d": s}
        for d, t, p, s in reversed(rows)  # chronological
    ]


# --------------------------------------------------------------------------
# Pull today's enriched candidates from Chart Library
# --------------------------------------------------------------------------

def fetch_setups(top: int = 10) -> list[dict]:
    """Calls /api/v1/agent/setups — pre-enriched with full-cohort stats.
    No auth required for the Sandbox tier (200 calls/day)."""
    headers = {}
    key = os.getenv("CHARTLIBRARY_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    r = requests.get(
        f"{API}/agent/setups",
        params={"top": top, "timeframe": "1d"},
        headers=headers,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


# --------------------------------------------------------------------------
# Claude picks with conviction, conditioned on lessons
# --------------------------------------------------------------------------

def claude_picks(setups: list[dict], lessons: list[dict],
                  k: int = N_PICKS) -> list[dict]:
    client = anthropic.Anthropic()

    candidates = [
        {
            "symbol": s["symbol"],
            "cohort_score": round(s.get("cohort", {}).get("cohort_score", 0), 3),
            "win_rate_5d": round(s.get("cohort", {}).get("win_rate_5d", 0), 3),
            "median_5d": round(s.get("cohort", {}).get("median_5d", 0), 2),
            "interest_score": round(s.get("interest_score", 0), 2),
        }
        for s in setups
    ]

    lessons_block = ""
    if lessons:
        lessons_block = "\nLESSONS FROM RECENT DAYS:\n"
        for L in lessons:
            p = L["portfolio_5d"]
            sp = L["spy_5d"]
            p_str = f"{p:+.2f}%" if p is not None else "?"
            sp_str = f"{sp:+.2f}%" if sp is not None else "?"
            lessons_block += f"- {L['date']} (you {p_str}, SPY {sp_str}): {L['lesson']}\n"

    prompt = f"""You are a cohort-aware paper trader. Pick {k} long positions to hold 5 trading days, equal-weighted.

CANDIDATES (sorted by cohort_score descending):
{json.dumps(candidates, indent=2)}
{lessons_block}
Pick exactly {k} symbols. For each, output: conviction (low/medium/high) + ONE sentence reason (max 25 words).
Apply your accumulated lessons. High cohort_score is one signal — not the only one.

Output ONLY a JSON array:
[{{"symbol": "AAPL", "conviction": "medium", "reason": "60% win rate cohort, tight band"}}]"""

    resp = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    m = re.search(r"\[[\s\S]*\]", text)
    return json.loads(m.group()) if m else []


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    db = init_db()
    setups = fetch_setups(top=10)
    if len(setups) < N_PICKS:
        print(f"only {len(setups)} setups today — skipping.")
        return

    lessons = read_recent_lessons(db)
    print(f"Reading {len(lessons)} lessons from memory.")

    picks = claude_picks(setups, lessons)
    if not picks:
        print("LLM returned no picks.")
        return

    by_sym = {s["symbol"]: s for s in setups}
    for p in picks[:N_PICKS]:
        sym = p["symbol"].upper()
        if sym not in by_sym:
            print(f"  skip {sym} (not in candidates)")
            continue
        s = by_sym[sym]
        c = s.get("cohort", {})
        db.execute(
            "INSERT INTO trades (trade_date, symbol, conviction, cohort_score, "
            "win_rate_5d, median_5d, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                str(date.today()), sym, p["conviction"],
                c.get("cohort_score"), c.get("win_rate_5d"), c.get("median_5d"),
                p["reason"],
            ),
        )
        print(f"  BUY {sym} ({p['conviction']}) — {p['reason']}")
    db.commit()

    print()
    print("Trade decisions logged to agent.db.")
    print("Run a separate scoring loop after 5 trading days to:")
    print("  1. Mark trades closed against actual price data")
    print("  2. Generate a one-sentence lesson via Claude reflection")
    print("  3. Lesson conditions tomorrow's picks")
    print()
    print("See https://chartlibrary.io/guides/build-ai-trading-agent-claude")
    print("for the full scoring + lesson generation example.")


if __name__ == "__main__":
    main()
