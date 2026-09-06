"""
Governance / Conflict Agent — reviews the outputs of the other agents for
disagreement, missing evidence, low confidence, and stale/degraded data.
It never forces artificial consensus; its job is to flag when the system
should be less confident, not to make the signals agree.
"""
from __future__ import annotations

from agents.base import BaseAgent, AgentResult, Evidence


DIRECTIONAL_SIGNALS = {"BULLISH": 1, "BEARISH": -1, "NEUTRAL": 0}


class GovernanceAgent(BaseAgent):
    name = "governance"

    def run(self, technical, fundamental, sentiment, risk, data_degraded: bool = False) -> AgentResult:
        return self._timed(self._analyze, technical, fundamental, sentiment, risk, data_degraded)

    def _analyze(self, technical, fundamental, sentiment, risk, data_degraded: bool) -> AgentResult:
        factors: list[str] = []
        warnings: list[str] = []

        directional = [technical, fundamental, sentiment]
        directions = [DIRECTIONAL_SIGNALS.get(a.signal, 0) for a in directional if a.status == "ok"]

        conflict = False
        if directions:
            bullish_count = sum(1 for d in directions if d > 0)
            bearish_count = sum(1 for d in directions if d < 0)
            if bullish_count > 0 and bearish_count > 0:
                conflict = True

        if risk.signal == "CAUTION" and any(a.signal == "BULLISH" for a in [technical, fundamental]):
            conflict = True
            factors.append("Market signals are constructive but Risk Agent flags portfolio-level caution")

        unavailable_agents = [a.agent for a in [technical, fundamental, sentiment, risk] if a.status != "ok"]
        if unavailable_agents:
            warnings.append(f"Agents unavailable or degraded: {', '.join(unavailable_agents)}")
            factors.append(f"{len(unavailable_agents)} agent(s) did not return a full result")

        low_confidence_agents = [
            a.agent for a in [technical, fundamental, sentiment, risk]
            if a.status == "ok" and a.confidence < 0.5
        ]
        if low_confidence_agents:
            warnings.append(f"Low-confidence agents: {', '.join(low_confidence_agents)}")

        missing_evidence_agents = [
            a.agent for a in [technical, fundamental, sentiment, risk]
            if a.status == "ok" and len(a.evidence) == 0
        ]
        if missing_evidence_agents:
            warnings.append(f"No evidence attached from: {', '.join(missing_evidence_agents)}")

        if data_degraded:
            warnings.append("Live market data source is degraded; using cached/verified state")

        if conflict:
            signal = "CONFLICT_DETECTED"
            factors.insert(0, "Directional disagreement detected across independent agents")
        elif unavailable_agents or low_confidence_agents or missing_evidence_agents:
            signal = "REVIEW_RECOMMENDED"
        else:
            signal = "CONSISTENT"
            factors.append("No material conflict detected across agent signals")

        # Governance confidence reflects how much we trust the pipeline's own output,
        # not the market call itself.
        penalty = 0.0
        if conflict:
            penalty += 0.25
        penalty += 0.08 * len(unavailable_agents)
        penalty += 0.05 * len(low_confidence_agents)
        if data_degraded:
            penalty += 0.15
        confidence = round(max(0.1, 0.9 - penalty), 2)
        score = round(confidence * 100)

        evidence = [
            Evidence(
                source="Governance Review",
                document="internal",
                chunk=(
                    f"technical={technical.signal}, fundamental={fundamental.signal}, "
                    f"sentiment={sentiment.signal}, risk={risk.signal}, conflict={conflict}, "
                    f"data_degraded={data_degraded}"
                ),
                relevance=1.0,
                kind="calculated",
            )
        ]

        return AgentResult(
            agent=self.name,
            status="ok",
            signal=signal,
            confidence=confidence,
            score=score,
            factors=factors,
            evidence=evidence,
            warnings=warnings,
        )
