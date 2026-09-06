"""
SQLite persistence layer. Local file, no external service.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
import datetime as dt

_LOCAL_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "nexus.db")
# Vercel functions only permit runtime writes under /tmp. The database remains
# local and persistent during development, while deployments remain functional.
DB_PATH = os.getenv("NEXUS_DB_PATH") or ("/tmp/nexus.db" if os.getenv("VERCEL") else _LOCAL_DB_PATH)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    started_at TEXT,
    user_profile TEXT
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TEXT,
    stock TEXT,
    agent TEXT,
    signal TEXT,
    confidence REAL,
    latency_ms REAL
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TEXT,
    stock TEXT,
    user_profile TEXT,
    final_decision TEXT,
    confidence REAL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TEXT,
    user_profile TEXT,
    portfolio_risk_score REAL,
    portfolio_value REAL
);
"""

# Columns added after the original schema shipped. Applied with ALTER TABLE
# ADD COLUMN, guarded by a PRAGMA check, so existing nexus.db files created
# before this change upgrade in place instead of breaking.
_RECOMMENDATIONS_MIGRATIONS = {
    "proposed_allocation_pct": "REAL",
    "risk_signal": "TEXT",
}


def _migrate(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(recommendations)").fetchall()}
    for column, col_type in _RECOMMENDATIONS_MIGRATIONS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE recommendations ADD COLUMN {column} {col_type}")


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def new_session(user_profile: str) -> str:
    session_id = str(uuid.uuid4())[:8]
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO sessions (session_id, started_at, user_profile) VALUES (?, ?, ?)",
            (session_id, dt.datetime.now().isoformat(), user_profile),
        )
        conn.commit()
    finally:
        conn.close()
    return session_id


def log_investigation(session_id: str, stock: str, user_profile: str, investigation,
                       proposed_allocation_pct: float | None = None) -> None:
    conn = _connect()
    try:
        ts = dt.datetime.now().isoformat()
        for agent_result in [investigation.technical, investigation.fundamental,
                              investigation.sentiment, investigation.risk, investigation.governance]:
            conn.execute(
                "INSERT INTO agent_runs (session_id, timestamp, stock, agent, signal, confidence, latency_ms) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session_id, ts, stock, agent_result.agent, agent_result.signal,
                 agent_result.confidence, agent_result.latency_ms),
            )
        conn.execute(
            "INSERT INTO recommendations "
            "(session_id, timestamp, stock, user_profile, final_decision, confidence, "
            " proposed_allocation_pct, risk_signal) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, ts, stock, user_profile, investigation.synthesis.final_signal,
             investigation.synthesis.confidence, proposed_allocation_pct, investigation.risk.signal),
        )
        conn.commit()
    finally:
        conn.close()


def log_portfolio_snapshot(session_id: str, user_profile: str, portfolio: dict) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO portfolio_snapshots (session_id, timestamp, user_profile, portfolio_risk_score, portfolio_value) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, dt.datetime.now().isoformat(), user_profile,
             portfolio.get("portfolio_risk_score", 0), portfolio.get("portfolio_value", 0)),
        )
        conn.commit()
    finally:
        conn.close()


def get_behavioral_history(user_profile: str, max_preferred_pct: float | None = None,
                            limit: int = 25) -> dict:
    """Summarizes this investor profile's past investigations across ALL
    sessions (not just the current one), for the Risk Agent to consult.

    Deliberately keyed by profile name (Conservative/Moderate/Aggressive),
    not by session — a session is one browser tab / one API process
    lifetime, but "this investor's demonstrated behavior" should span every
    time that profile has been used, in either the Streamlit or React app,
    since both write to the same recommendations table.

    Returns sample_size=0 with all other fields None/empty if there is no
    history yet — callers must treat that as "not enough data", never as
    "zero risk" or "zero override rate".
    """
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT stock, final_decision, confidence, proposed_allocation_pct, risk_signal, timestamp "
            "FROM recommendations WHERE user_profile=? ORDER BY timestamp DESC LIMIT ?",
            (user_profile, limit),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    sample_size = len(rows)
    if sample_size == 0:
        return {
            "sample_size": 0,
            "avg_confidence": None,
            "override_count": 0,
            "override_rate": None,
            "caution_count": 0,
            "caution_rate": None,
            "recent": [],
        }

    confidences = [r[2] for r in rows if r[2] is not None]
    avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else None

    override_count = 0
    checked_for_override = 0
    if max_preferred_pct is not None:
        for r in rows:
            proposed = r[3]
            if proposed is not None:
                checked_for_override += 1
                if proposed > max_preferred_pct:
                    override_count += 1
    override_rate = round(override_count / checked_for_override, 2) if checked_for_override else None

    caution_count = sum(1 for r in rows if r[4] == "CAUTION")
    caution_rate = round(caution_count / sample_size, 2)

    recent = [
        {
            "ticker": r[0], "decision": r[1], "confidence": r[2],
            "proposed_allocation_pct": r[3], "risk_signal": r[4], "timestamp": r[5],
        }
        for r in rows[:5]
    ]

    return {
        "sample_size": sample_size,
        "avg_confidence": avg_confidence,
        "override_count": override_count,
        "override_rate": override_rate,
        "caution_count": caution_count,
        "caution_rate": caution_rate,
        "recent": recent,
    }


def get_session_stats(session_id: str) -> dict:
    conn = _connect()
    try:
        cur = conn.execute("SELECT COUNT(*) FROM recommendations WHERE session_id=?", (session_id,))
        rec_count = cur.fetchone()[0]
        cur = conn.execute("SELECT AVG(latency_ms) FROM agent_runs WHERE session_id=?", (session_id,))
        avg_latency = cur.fetchone()[0] or 0.0
        return {"recommendation_count": rec_count, "avg_agent_latency_ms": round(avg_latency, 1)}
    finally:
        conn.close()
