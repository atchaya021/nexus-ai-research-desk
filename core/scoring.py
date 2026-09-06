"""
Shared deterministic scoring helpers for the Synthesis Agent.

Kept separate from agents/synthesis.py so the decision matrix is easy to
audit and unit-test in isolation.
"""
from __future__ import annotations

SIGNAL_LADDER = ["AVOID", "REDUCE", "WATCH", "HOLD", "ACCUMULATE"]


def market_score(technical_score: int, fundamental_score: int, sentiment_score: int) -> float:
    """Weighted blend of the three directional agents.
    Technical and fundamental carry slightly more weight than sentiment,
    reflecting that sentiment is the noisiest, most short-lived signal."""
    return round(0.35 * technical_score + 0.35 * fundamental_score + 0.30 * sentiment_score, 1)


def base_signal_from_market_score(score: float) -> str:
    if score >= 65:
        return "ACCUMULATE"
    if score >= 52:
        return "HOLD"
    if score >= 40:
        return "WATCH"
    if score >= 28:
        return "REDUCE"
    return "AVOID"


def downgrade(signal: str, steps: int) -> str:
    idx = SIGNAL_LADDER.index(signal)
    idx = max(0, idx - steps)
    return SIGNAL_LADDER[idx]


def apply_risk_adjustment(base: str, risk_signal: str, risk_score: int) -> tuple[str, int]:
    """Returns (adjusted_signal, steps_downgraded)."""
    steps = 0
    if risk_signal == "CAUTION":
        steps = 2 if risk_score >= 80 else 1
    elif risk_signal == "MONITOR":
        steps = 1 if risk_score >= 55 else 0
    adjusted = downgrade(base, steps)
    return adjusted, steps


def apply_governance_adjustment(signal: str, governance_signal: str) -> tuple[str, bool]:
    """Conflict never forces a specific signal, but it caps how aggressive
    the final call can be, since the pipeline itself is not confident."""
    if governance_signal == "CONFLICT_DETECTED":
        idx = SIGNAL_LADDER.index(signal)
        cap_idx = SIGNAL_LADDER.index("HOLD")
        if idx > cap_idx:
            return "HOLD", True
    return signal, False


def blended_confidence(technical_conf: float, fundamental_conf: float, sentiment_conf: float,
                        risk_conf: float, governance_conf: float) -> float:
    raw = (
        0.25 * technical_conf + 0.25 * fundamental_conf + 0.20 * sentiment_conf
        + 0.15 * risk_conf + 0.15 * governance_conf
    )
    return round(raw, 2)
