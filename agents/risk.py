"""
Risk Agent — evaluates the stock's risk characteristics AND, critically,
whether a larger position is suitable for THIS investor's portfolio and
risk profile. This is what prevents NEXUS from being "just a signal
aggregator": market attractiveness is deliberately kept separate from
portfolio suitability.
"""
from __future__ import annotations

from agents.base import BaseAgent, AgentResult, Evidence

# Minimum number of past investigations for this profile before behavioral
# history is allowed to influence the score. Below this, any observed rate
# (e.g. "1 of 1 overridden") is noise, not a pattern — the agent explicitly
# says so rather than silently ignoring a `behavioral` argument.
MIN_BEHAVIORAL_SAMPLES = 3


class RiskAgent(BaseAgent):
    name = "risk"

    def run(self, ticker: str, market_data: dict, profile: dict, portfolio: dict,
            proposed_allocation_pct: float | None = None,
            behavioral: dict | None = None) -> AgentResult:
        return self._timed(
            self._analyze, ticker, market_data, profile, portfolio, proposed_allocation_pct, behavioral
        )

    def _analyze(self, ticker: str, market_data: dict, profile: dict, portfolio: dict,
                 proposed_allocation_pct: float | None,
                 behavioral: dict | None = None) -> AgentResult:
        t = market_data["technical"]
        volatility = t["volatility_30d"]
        sector = market_data["sector"]

        holdings = portfolio.get("holdings", {})
        current_alloc = holdings.get(ticker, {}).get("allocation_pct", 0.0)
        sector_exposure = portfolio.get("sector_exposure", {}).get(sector, 0.0)
        max_pref = profile["max_preferred_position_pct"]
        vol_tolerance = profile["volatility_tolerance"]

        proposed = proposed_allocation_pct if proposed_allocation_pct is not None else current_alloc

        factors: list[str] = []
        warnings: list[str] = []
        risk_score = 30  # baseline

        # Position concentration risk
        if proposed > max_pref:
            over_by = proposed - max_pref
            risk_score += min(40, round(over_by * 4))
            warnings.append(
                f"Proposed position ({proposed:.1f}%) exceeds the {profile['name']} profile's "
                f"preferred maximum of {max_pref:.1f}% by {over_by:.1f} points"
            )
            factors.append(f"Position concentration exceeds preferred maximum for {profile['name']} profile")
        else:
            factors.append(f"Position size of {proposed:.1f}% is within the preferred maximum of {max_pref:.1f}%")

        # Sector concentration
        if sector_exposure > 20:
            risk_score += 15
            warnings.append(f"Sector exposure to {sector} is already {sector_exposure:.1f}% of portfolio")
            factors.append(f"High existing sector concentration in {sector} ({sector_exposure:.1f}%)")
        elif sector_exposure > 12:
            risk_score += 7
            factors.append(f"Moderate sector concentration in {sector} ({sector_exposure:.1f}%)")
        else:
            factors.append(f"Sector concentration in {sector} is limited ({sector_exposure:.1f}%)")

        # Volatility vs tolerance
        vol_thresholds = {"LOW": 12, "MEDIUM": 18, "HIGH": 30}
        threshold = vol_thresholds.get(vol_tolerance, 18)
        if volatility > threshold:
            risk_score += 15
            warnings.append(
                f"Stock volatility ({volatility:.1f}%) exceeds this investor's {vol_tolerance} tolerance threshold (~{threshold}%)"
            )
            factors.append(f"30-day volatility of {volatility:.1f}% exceeds {vol_tolerance} tolerance")
        else:
            factors.append(f"30-day volatility of {volatility:.1f}% is within {vol_tolerance} tolerance")

        # Horizon-based drawdown sensitivity
        horizon = profile["investment_horizon"]
        if "1-3" in horizon and volatility > 15:
            risk_score += 8
            factors.append("Shorter investment horizon increases sensitivity to near-term drawdowns")

        # Behavioral history — this profile's demonstrated pattern across
        # PAST investigations (any ticker), not just this stock. Only applied
        # once there's enough history to call it a pattern rather than noise,
        # and always cited with the exact counts it's based on.
        behavioral_note: str | None = None
        behavioral_evidence: Evidence | None = None
        sample_size = (behavioral or {}).get("sample_size", 0)
        if behavioral and sample_size >= MIN_BEHAVIORAL_SAMPLES:
            override_rate = behavioral.get("override_rate")
            caution_rate = behavioral.get("caution_rate")

            if override_rate is not None and override_rate > 0.4:
                adj = min(10, round(override_rate * 15))
                risk_score += adj
                behavioral_note = (
                    f"Behavioral pattern: proposed allocations exceeded this profile's own "
                    f"preferred ceiling in {behavioral['override_count']} of the last {sample_size} "
                    f"investigations ({override_rate * 100:.0f}%) — risk score adjusted +{adj}"
                )
                warnings.append(behavioral_note)
                factors.append(
                    f"Demonstrated tendency toward oversized position requests "
                    f"({override_rate * 100:.0f}% of last {sample_size} investigations)"
                )
            elif caution_rate is not None and caution_rate >= 0.5:
                behavioral_note = (
                    f"Behavioral note: {behavioral['caution_count']} of the last {sample_size} "
                    f"investigations for this profile ({caution_rate * 100:.0f}%) also received a "
                    f"CAUTION risk signal — no score adjustment, informational only"
                )
                factors.append(behavioral_note)
            else:
                factors.append(
                    f"Behavioral history reviewed ({sample_size} past investigations for this "
                    f"profile) — no pattern crossed an adjustment threshold"
                )

            behavioral_evidence = Evidence(
                source="Behavioral History (this profile's session log)",
                document="database/nexus.db:recommendations",
                chunk=(
                    f"sample_size={sample_size}, override_rate={override_rate}, "
                    f"caution_rate={caution_rate}"
                ),
                relevance=0.8,
                kind="calculated",
            )
        elif behavioral and sample_size:
            factors.append(
                f"Behavioral history has only {sample_size} past investigation(s) for this profile "
                f"— below the {MIN_BEHAVIORAL_SAMPLES} needed to treat any pattern as reliable"
            )

        risk_score = max(0, min(100, risk_score))

        if risk_score >= 65:
            signal = "CAUTION"
        elif risk_score >= 45:
            signal = "MONITOR"
        else:
            signal = "ACCEPTABLE"

        confidence = round(min(0.95, 0.55 + risk_score / 250), 2)

        evidence = [
            Evidence(
                source="Portfolio Snapshot (Demo)",
                document="data/portfolio.json",
                chunk=(
                    f"Profile={profile['name']}, current_allocation={current_alloc:.1f}%, "
                    f"proposed_allocation={proposed:.1f}%, sector_exposure({sector})={sector_exposure:.1f}%, "
                    f"max_preferred_position={max_pref:.1f}%, volatility_tolerance={vol_tolerance}"
                ),
                relevance=1.0,
                kind="dataset",
            )
        ]
        if behavioral_evidence is not None:
            evidence.append(behavioral_evidence)

        return AgentResult(
            agent=self.name,
            status="ok",
            signal=signal,
            confidence=confidence,
            score=risk_score,
            factors=factors,
            evidence=evidence,
            warnings=warnings,
        )
