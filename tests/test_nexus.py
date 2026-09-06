"""
Basic tests for NEXUS core logic. Run with: pytest tests/ -q
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.profiler import load_market, load_news, load_portfolios, get_profile, get_portfolio
from core.orchestrator import run_investigation
from core.rag import get_engine
from agents.technical import TechnicalAgent
from agents.risk import RiskAgent

market = load_market()
news = load_news()
portfolios = load_portfolios()


def test_technical_agent_returns_structured_result():
    agent = TechnicalAgent()
    result = agent.run("RELIANCE", market["RELIANCE"])
    assert result.agent == "technical"
    assert result.signal in {"BULLISH", "BEARISH", "NEUTRAL"}
    assert 0.0 <= result.confidence <= 1.0
    assert len(result.factors) > 0
    assert len(result.evidence) > 0


def test_risk_agent_flags_concentration_breach():
    agent = RiskAgent()
    profile = get_profile(portfolios, "conservative")
    portfolio = get_portfolio(portfolios, "conservative")
    result = agent.run("RELIANCE", market["RELIANCE"], profile, portfolio, proposed_allocation_pct=20.0)
    assert result.signal in {"CAUTION", "MONITOR"}
    assert result.score > 0


def test_personalization_differs_across_profiles():
    """Same stock, same market event, different profiles -> not guaranteed to
    differ in every case, but risk score and/or signal must reflect the
    different profile constraints (this is the core mandatory demo)."""
    signals = {}
    risk_scores = {}
    for key in ["conservative", "moderate", "aggressive"]:
        profile = get_profile(portfolios, key)
        portfolio = get_portfolio(portfolios, key)
        current = portfolio["holdings"].get("RELIANCE", {}).get("allocation_pct", 0.0)
        inv = run_investigation(
            "RELIANCE", "Should I increase my Reliance position?",
            market["RELIANCE"], news["RELIANCE"], profile, portfolio,
            proposed_allocation_pct=current + 3,
        )
        signals[key] = inv.synthesis.final_signal
        risk_scores[key] = inv.risk.score

    assert len(set(risk_scores.values())) > 1, "Risk scores should differ across profiles with different constraints"


def test_conflict_detection_reduces_confidence():
    profile = get_profile(portfolios, "moderate")
    portfolio = get_portfolio(portfolios, "moderate")
    baseline = run_investigation("RELIANCE", "test", market["RELIANCE"], news["RELIANCE"], profile, portfolio,
                                  proposed_allocation_pct=11)
    conflicted = run_investigation("RELIANCE", "test", market["RELIANCE"], news["RELIANCE"], profile, portfolio,
                                    proposed_allocation_pct=11, force_conflict=True)
    assert conflicted.governance.signal == "CONFLICT_DETECTED"
    assert conflicted.synthesis.confidence <= baseline.synthesis.confidence


def test_degraded_mode_reduces_confidence_and_does_not_crash():
    profile = get_profile(portfolios, "moderate")
    portfolio = get_portfolio(portfolios, "moderate")
    baseline = run_investigation("RELIANCE", "test", market["RELIANCE"], news["RELIANCE"], profile, portfolio,
                                  proposed_allocation_pct=11)
    degraded = run_investigation("RELIANCE", "test", market["RELIANCE"], news["RELIANCE"], profile, portfolio,
                                  proposed_allocation_pct=11, data_degraded=True)
    assert degraded.data_degraded is True
    assert degraded.synthesis.confidence < baseline.synthesis.confidence


def test_rag_retrieval_returns_evidence_with_fallback():
    engine = get_engine()
    assert engine.mode in {"VECTOR", "KEYWORD_FALLBACK", "UNAVAILABLE"}
    results = engine.retrieve("RELIANCE", "revenue growth margins debt", top_k=2)
    if engine.mode != "UNAVAILABLE":
        assert len(results) > 0
        assert all("relevance" in r for r in results)


def test_all_five_agents_execute_in_investigation():
    profile = get_profile(portfolios, "moderate")
    portfolio = get_portfolio(portfolios, "moderate")
    inv = run_investigation("TCS", "How does TCS look?", market["TCS"], news["TCS"], profile, portfolio)
    for agent_result in [inv.technical, inv.fundamental, inv.sentiment, inv.risk, inv.governance]:
        assert agent_result.status in {"ok", "degraded", "unavailable"}
    assert inv.synthesis.final_signal in {"ACCUMULATE", "HOLD", "WATCH", "REDUCE", "AVOID"}
