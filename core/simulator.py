"""
Counterfactual portfolio simulator: "what if I change my position size?"

This is scenario analysis over the SAME deterministic Risk Agent logic used
in the main investigation — not a prediction of future returns.
"""
from __future__ import annotations

from dataclasses import dataclass
from agents.risk import RiskAgent


@dataclass
class CounterfactualResult:
    current_allocation: float
    proposed_allocation: float
    current_risk_score: int
    proposed_risk_score: int
    current_signal: str
    proposed_signal: str
    threshold_exceeded: bool
    max_preferred_pct: float
    delta: int


def simulate_allocation_change(ticker: str, market_data: dict, profile: dict, portfolio: dict,
                                proposed_allocation_pct: float) -> CounterfactualResult:
    current_allocation = portfolio.get("holdings", {}).get(ticker, {}).get("allocation_pct", 0.0)
    agent = RiskAgent()

    current_result = agent.run(ticker, market_data, profile, portfolio, proposed_allocation_pct=current_allocation)
    proposed_result = agent.run(ticker, market_data, profile, portfolio, proposed_allocation_pct=proposed_allocation_pct)

    max_pref = profile["max_preferred_position_pct"]
    threshold_exceeded = proposed_allocation_pct > max_pref

    return CounterfactualResult(
        current_allocation=current_allocation,
        proposed_allocation=proposed_allocation_pct,
        current_risk_score=current_result.score,
        proposed_risk_score=proposed_result.score,
        current_signal=current_result.signal,
        proposed_signal=proposed_result.signal,
        threshold_exceeded=threshold_exceeded,
        max_preferred_pct=max_pref,
        delta=proposed_result.score - current_result.score,
    )
