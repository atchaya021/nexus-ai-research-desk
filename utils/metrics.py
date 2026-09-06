"""
Session performance metrics — computed from real values produced during
the session, never randomly generated.
"""
from __future__ import annotations


def evidence_coverage(investigation) -> float:
    """Fraction of the four core agents that returned at least one evidence item."""
    agents = [investigation.technical, investigation.fundamental, investigation.sentiment, investigation.risk]
    with_evidence = sum(1 for a in agents if len(a.evidence) > 0)
    return round(with_evidence / len(agents), 2)


def signal_agreement(investigation) -> float:
    """Fraction of the three directional agents (technical/fundamental/sentiment)
    that agree with the majority direction."""
    signals = [investigation.technical.signal, investigation.fundamental.signal, investigation.sentiment.signal]
    from collections import Counter
    counts = Counter(signals)
    majority = counts.most_common(1)[0][1]
    return round(majority / len(signals), 2)


def total_evidence_sources(investigation) -> int:
    agents = [investigation.technical, investigation.fundamental, investigation.sentiment, investigation.risk]
    return sum(len(a.evidence) for a in agents)


def avg_agent_latency_ms(investigation) -> float:
    agents = [investigation.technical, investigation.fundamental, investigation.sentiment,
              investigation.risk, investigation.governance]
    vals = [a.latency_ms for a in agents]
    return round(sum(vals) / len(vals), 2) if vals else 0.0
