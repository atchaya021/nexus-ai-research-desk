"""
Small display-formatting helpers shared across the Streamlit UI.
"""
from __future__ import annotations

SIGNAL_COLORS = {
    "BULLISH": "#2ecc71", "BEARISH": "#e74c3c", "NEUTRAL": "#95a5a6",
    "CAUTION": "#f39c12", "MONITOR": "#f1c40f", "ACCEPTABLE": "#2ecc71",
    "ACCUMULATE": "#2ecc71", "HOLD": "#3498db", "WATCH": "#f39c12",
    "REDUCE": "#e67e22", "AVOID": "#e74c3c",
    "CONFLICT_DETECTED": "#e74c3c", "REVIEW_RECOMMENDED": "#f39c12", "CONSISTENT": "#2ecc71",
    "UNAVAILABLE": "#7f8c8d",
}


def signal_color(signal: str) -> str:
    return SIGNAL_COLORS.get(signal, "#bdc3c7")


def pct(value: float) -> str:
    return f"{value*100:.0f}%"
