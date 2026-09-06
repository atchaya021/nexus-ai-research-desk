"""
Orchestrator — runs Technical, Fundamental, Sentiment, and Risk agents in
parallel via a real ThreadPoolExecutor, then runs Governance and Synthesis
sequentially (since they depend on the parallel agents' outputs).

Produces a structured decision trace (timestamped) suitable for display as
an audit log — not a hidden chain-of-thought.
"""
from __future__ import annotations

import time
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict

from agents.technical import TechnicalAgent
from agents.fundamental import FundamentalAgent
from agents.sentiment import SentimentAgent
from agents.risk import RiskAgent
from agents.governance import GovernanceAgent
from agents.synthesis import synthesize, SynthesisResult
from agents.base import AgentResult


@dataclass
class TraceEvent:
    timestamp: str
    message: str


@dataclass
class InvestigationResult:
    ticker: str
    question: str
    technical: AgentResult
    fundamental: AgentResult
    sentiment: AgentResult
    risk: AgentResult
    governance: AgentResult
    synthesis: SynthesisResult
    trace: list[TraceEvent] = field(default_factory=list)
    total_latency_ms: float = 0.0
    rag_mode: str = "UNKNOWN"
    data_degraded: bool = False
    behavioral: dict | None = None

    def to_dict(self) -> dict:
        d = {
            "ticker": self.ticker,
            "question": self.question,
            "technical": self.technical.to_dict(),
            "fundamental": self.fundamental.to_dict(),
            "sentiment": self.sentiment.to_dict(),
            "risk": self.risk.to_dict(),
            "governance": self.governance.to_dict(),
            "synthesis": self.synthesis.to_dict(),
            "trace": [asdict(t) for t in self.trace],
            "total_latency_ms": self.total_latency_ms,
            "rag_mode": self.rag_mode,
            "data_degraded": self.data_degraded,
            "behavioral": self.behavioral,
        }
        return d


def _now() -> str:
    return dt.datetime.now().strftime("%H:%M:%S")


def run_investigation(
    ticker: str,
    question: str,
    market_data: dict,
    news_data: dict,
    profile: dict,
    portfolio: dict,
    proposed_allocation_pct: float | None = None,
    data_degraded: bool = False,
    force_conflict: bool = False,
    behavioral: dict | None = None,
) -> InvestigationResult:
    trace: list[TraceEvent] = []
    start = time.time()

    trace.append(TraceEvent(_now(), f"Investigation started for {ticker}: \"{question}\""))
    if behavioral and behavioral.get("sample_size"):
        trace.append(TraceEvent(
            _now(),
            f"Behavioral history loaded: {behavioral['sample_size']} past investigation(s) for this profile"
        ))
    trace.append(TraceEvent(_now(), "Technical Agent started"))
    trace.append(TraceEvent(_now(), "Fundamental Agent started"))
    trace.append(TraceEvent(_now(), "Sentiment Agent started"))
    trace.append(TraceEvent(_now(), "Risk Agent started"))

    technical_agent = TechnicalAgent()
    fundamental_agent = FundamentalAgent()
    sentiment_agent = SentimentAgent()
    risk_agent = RiskAgent()

    results: dict[str, AgentResult] = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(technical_agent.run, ticker, market_data): "technical",
            executor.submit(fundamental_agent.run, ticker, market_data, question): "fundamental",
            executor.submit(sentiment_agent.run, ticker, news_data): "sentiment",
            executor.submit(
                risk_agent.run, ticker, market_data, profile, portfolio, proposed_allocation_pct, behavioral
            ): "risk",
        }
        for future in as_completed(futures):
            key = futures[future]
            result = future.result()
            results[key] = result
            trace.append(TraceEvent(_now(), f"{key.capitalize()} Agent -> {result.signal} ({result.confidence*100:.0f}%)"))

    technical, fundamental, sentiment, risk = (
        results["technical"], results["fundamental"], results["sentiment"], results["risk"],
    )

    if force_conflict:
        # Deterministic, clearly-labeled demo scenario — do not fabricate silently.
        sentiment.signal = "BEARISH"
        sentiment.confidence = min(sentiment.confidence, 0.55)
        sentiment.warnings.append("DEMO: signal conflict simulation active")
        risk.signal = "CAUTION"
        risk.score = max(risk.score, 74)
        risk.warnings.append("DEMO: signal conflict simulation active")

    governance_agent = GovernanceAgent()
    governance = governance_agent.run(technical, fundamental, sentiment, risk, data_degraded=data_degraded)
    trace.append(TraceEvent(_now(), f"Governance review -> {governance.signal}"))

    evidence_count = sum(len(a.evidence) for a in [technical, fundamental, sentiment, risk])
    trace.append(TraceEvent(_now(), f"{evidence_count} evidence item(s) collected across agents"))

    synthesis = synthesize(
        ticker, question, technical, fundamental, sentiment, risk, governance, profile, portfolio
    )
    if data_degraded:
        from utils.fallback import apply_degradation
        pre_degradation_confidence = synthesis.confidence
        synthesis.confidence = apply_degradation(synthesis.confidence, degraded=True)
        trace.append(
            TraceEvent(_now(),
                       f"Confidence downgraded due to degraded data source: {pre_degradation_confidence*100:.0f}% -> {synthesis.confidence*100:.0f}%")
        )
    trace.append(TraceEvent(_now(), "Portfolio suitability evaluated against investor profile"))
    trace.append(TraceEvent(_now(), f"Final synthesis complete -> {synthesis.final_signal} ({synthesis.confidence*100:.0f}%)"))

    total_latency_ms = round((time.time() - start) * 1000, 1)

    from core.rag import get_engine as get_rag
    rag_mode = get_rag().mode

    return InvestigationResult(
        ticker=ticker,
        question=question,
        technical=technical,
        fundamental=fundamental,
        sentiment=sentiment,
        risk=risk,
        governance=governance,
        synthesis=synthesis,
        trace=trace,
        total_latency_ms=total_latency_ms,
        rag_mode=rag_mode,
        data_degraded=data_degraded,
        behavioral=behavioral,
    )
