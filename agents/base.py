"""
Base contract for all NEXUS agents.

Every specialized agent returns an AgentResult with a consistent shape so the
orchestrator, governance layer, synthesis layer, and UI can treat all five
agents uniformly. Agents never return free-form prose as their primary output.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Evidence:
    source: str          # e.g. "Reliance Q1 FY27 Filing"
    document: str         # filename or dataset name
    chunk: str             # the retrieved / cited text
    relevance: float       # 0.0 - 1.0
    kind: str = "document"  # document | dataset | calculated

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AgentResult:
    agent: str
    status: str            # "ok" | "degraded" | "unavailable"
    signal: str             # e.g. BULLISH / BEARISH / NEUTRAL / CAUTION / CONFLICT
    confidence: float        # 0.0 - 1.0
    score: int                # 0-100, human readable version of confidence/strength
    factors: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    started_at: float = 0.0
    finished_at: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["evidence"] = [e.to_dict() if isinstance(e, Evidence) else e for e in self.evidence]
        return d


class BaseAgent:
    """All agents subclass this and implement `run`."""

    name = "base"

    def _timed(self, fn, *args, **kwargs) -> AgentResult:
        start = time.time()
        try:
            result = fn(*args, **kwargs)
            result.started_at = start
            result.finished_at = time.time()
            result.latency_ms = round((result.finished_at - start) * 1000, 1)
            return result
        except Exception as exc:  # agent must never crash the pipeline
            finished = time.time()
            return AgentResult(
                agent=self.name,
                status="unavailable",
                signal="UNAVAILABLE",
                confidence=0.0,
                score=0,
                factors=[],
                evidence=[],
                warnings=[f"Agent failed: {exc}"],
                latency_ms=round((finished - start) * 1000, 1),
                started_at=start,
                finished_at=finished,
            )

    def run(self, *args, **kwargs) -> AgentResult:
        raise NotImplementedError
