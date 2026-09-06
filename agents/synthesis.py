"""
Synthesis Agent — the final decision layer.

Combines technical, fundamental, sentiment, risk, and governance outputs with
the user's profile and portfolio into one personalized, explainable
recommendation. Deterministic by default; if an LLM is available it is used
ONLY to phrase the natural-language summary, never to alter the signal,
confidence, or evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

from agents.base import AgentResult
from core import scoring
from core.llm import get_engine as get_llm


@dataclass
class SynthesisResult:
    final_signal: str
    confidence: float
    summary: str
    positive_factors: list[str] = field(default_factory=list)
    negative_factors: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    personalization_reason: str = ""
    decision_trace: list[str] = field(default_factory=list)
    risk_downgrade_steps: int = 0
    governance_capped: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def synthesize(
    ticker: str,
    question: str,
    technical: AgentResult,
    fundamental: AgentResult,
    sentiment: AgentResult,
    risk: AgentResult,
    governance: AgentResult,
    profile: dict,
    portfolio: dict,
    question_mode: str = "GENERAL",
) -> SynthesisResult:
    trace: list[str] = []

    m_score = scoring.market_score(technical.score, fundamental.score, sentiment.score)
    base_signal = scoring.base_signal_from_market_score(m_score)
    trace.append(f"Blended market score (technical/fundamental/sentiment) = {m_score}/100 -> base signal {base_signal}")

    risk_adjusted, downgrade_steps = scoring.apply_risk_adjustment(base_signal, risk.signal, risk.score)
    if downgrade_steps:
        trace.append(
            f"Risk Agent signal '{risk.signal}' (score {risk.score}) downgraded recommendation by {downgrade_steps} level(s) -> {risk_adjusted}"
        )
    else:
        trace.append(f"Risk Agent signal '{risk.signal}' did not require a downgrade")

    final_signal, governance_capped = scoring.apply_governance_adjustment(risk_adjusted, governance.signal)
    if governance_capped:
        trace.append("Governance conflict detected — recommendation capped at HOLD to avoid overstating confidence")

    confidence = scoring.blended_confidence(
        technical.confidence, fundamental.confidence, sentiment.confidence, risk.confidence, governance.confidence
    )
    trace.append(f"Blended confidence across all agents = {confidence:.2f}")

    positive_factors = [f for f in technical.factors + fundamental.factors + sentiment.factors
                         if _looks_positive(f)]
    negative_factors = [f for f in technical.factors + fundamental.factors + sentiment.factors
                         if _looks_negative(f)]
    risk_factors = list(risk.factors) + list(governance.warnings)

    evidence = []
    for agent_result in [technical, fundamental, sentiment, risk]:
        evidence.extend(e.to_dict() if hasattr(e, "to_dict") else e for e in agent_result.evidence)

    personalization_reason = _personalization_reason(profile, risk, final_signal, base_signal)

    summary = _build_summary(ticker, question, final_signal, confidence, profile, m_score, risk)

    return SynthesisResult(
        final_signal=final_signal,
        confidence=confidence,
        summary=summary,
        positive_factors=positive_factors[:6],
        negative_factors=negative_factors[:6],
        risk_factors=risk_factors[:6],
        evidence=evidence,
        personalization_reason=personalization_reason,
        decision_trace=trace,
        risk_downgrade_steps=downgrade_steps,
        governance_capped=governance_capped,
    )


def _looks_positive(factor: str) -> bool:
    positive_markers = ["above", "strong", "healthy", "positive", "buying", "discount", "within", "limited", "improve"]
    negative_markers = ["below", "weak", "overbought", "oversold", "negative", "selling", "premium", "exceed",
                         "elevated", "pressure", "high existing", "soft"]
    lower = factor.lower()
    if any(n in lower for n in negative_markers):
        return False
    return any(p in lower for p in positive_markers)


def _looks_negative(factor: str) -> bool:
    negative_markers = ["below", "weak", "overbought", "oversold", "negative", "selling", "premium", "exceed",
                         "elevated", "pressure", "high existing", "soft"]
    return any(n in factor.lower() for n in negative_markers)


def _personalization_reason(profile: dict, risk: AgentResult, final_signal: str, base_signal: str) -> str:
    name = profile["name"]
    max_pref = profile["max_preferred_position_pct"]
    vol_tol = profile["volatility_tolerance"]
    if final_signal != base_signal:
        return (
            f"For the {name} profile (max preferred position {max_pref:.0f}%, {vol_tol} volatility tolerance), "
            f"the raw market signal of {base_signal} was adjusted to {final_signal} because the Risk Agent scored "
            f"portfolio suitability at {risk.score}/100 ({risk.signal})."
        )
    return (
        f"For the {name} profile (max preferred position {max_pref:.0f}%, {vol_tol} volatility tolerance), "
        f"the Risk Agent found no portfolio-suitability concerns significant enough to adjust the market signal."
    )


def _build_summary(ticker: str, question: str, final_signal: str, confidence: float,
                    profile: dict, m_score: float, risk: AgentResult) -> str:
    llm = get_llm()
    prompt = (
        "You are a financial research assistant writing a two-sentence, neutral, factual summary. "
        "Do not invent numbers. Use only the facts given.\n"
        f"Question: {question}\n"
        f"Ticker: {ticker}\n"
        f"Investor profile: {profile['name']}\n"
        f"Final recommendation: {final_signal}\n"
        f"Confidence: {confidence*100:.0f}%\n"
        f"Blended market score: {m_score}/100\n"
        f"Risk signal: {risk.signal} (score {risk.score}/100)\n"
        "Write the two-sentence summary now, no preamble:"
    )
    generated = llm.generate(prompt)
    if generated:
        return generated

    # Deterministic fallback template — identical substance, template phrasing.
    return (
        f"Based on a blended market score of {m_score}/100 and a {profile['name'].lower()} risk profile, "
        f"NEXUS assigns a {final_signal} signal for {ticker} at {confidence*100:.0f}% confidence. "
        f"Portfolio-level risk assessment scored {risk.score}/100 ({risk.signal})."
    )
