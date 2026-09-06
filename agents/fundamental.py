"""
Fundamental Agent — analyzes revenue growth, earnings growth, margins, debt,
and valuation, grounding its reasoning in retrieved filing evidence via RAG.

The agent never claims "according to the filing" unless a filing chunk was
actually retrieved for this ticker/query and is attached as evidence.
"""
from __future__ import annotations

from agents.base import BaseAgent, AgentResult, Evidence
from core.rag import get_engine


class FundamentalAgent(BaseAgent):
    name = "fundamental"

    def run(self, ticker: str, market_data: dict, question: str) -> AgentResult:
        return self._timed(self._analyze, ticker, market_data, question)

    def _analyze(self, ticker: str, market_data: dict, question: str) -> AgentResult:
        f = market_data["fundamental"]
        rev_growth = f["revenue_growth_yoy"]
        eps_growth = f["eps_growth_yoy"]
        margin = f["profit_margin"]
        de_ratio = f["debt_to_equity"]
        pe = f["pe_ratio"]
        sector_pe = f["sector_avg_pe"]

        score = 50
        factors: list[str] = []
        warnings: list[str] = []

        if rev_growth >= 8:
            score += 12
            factors.append(f"Revenue growth of {rev_growth:.1f}% YoY is strong")
        elif rev_growth >= 4:
            score += 4
            factors.append(f"Revenue growth of {rev_growth:.1f}% YoY is moderate")
        else:
            score -= 8
            factors.append(f"Revenue growth of {rev_growth:.1f}% YoY is weak")

        if eps_growth >= 10:
            score += 10
            factors.append(f"EPS growth of {eps_growth:.1f}% YoY is strong")
        elif eps_growth >= 4:
            score += 3
            factors.append(f"EPS growth of {eps_growth:.1f}% YoY is moderate")
        else:
            score -= 6
            factors.append(f"EPS growth of {eps_growth:.1f}% YoY is soft")

        if de_ratio < 0.3:
            score += 6
            factors.append(f"Debt/equity of {de_ratio:.2f} indicates a conservative balance sheet")
        elif de_ratio > 0.8:
            score -= 6
            warnings.append(f"Debt/equity of {de_ratio:.2f} is elevated")
            factors.append(f"Debt/equity of {de_ratio:.2f} is on the higher side")
        else:
            factors.append(f"Debt/equity of {de_ratio:.2f} is within a reasonable range")

        pe_premium = (pe - sector_pe) / sector_pe * 100
        if pe_premium > 15:
            score -= 6
            warnings.append(f"Trading at a {pe_premium:.0f}% P/E premium to sector average")
            factors.append(f"P/E of {pe:.1f}x is at a {pe_premium:.0f}% premium to the sector average ({sector_pe:.1f}x)")
        elif pe_premium < -10:
            score += 5
            factors.append(f"P/E of {pe:.1f}x is at a discount to the sector average ({sector_pe:.1f}x)")
        else:
            factors.append(f"P/E of {pe:.1f}x is broadly in line with the sector average ({sector_pe:.1f}x)")

        score = max(0, min(100, score))
        if score >= 65:
            signal = "BULLISH"
        elif score <= 40:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"
        confidence = round(score / 100, 2)

        evidence: list[Evidence] = [
            Evidence(
                source="Fundamental Data (Demo)",
                document="data/market.json",
                chunk=(
                    f"{ticker}: revenue_growth_yoy={rev_growth}%, eps_growth_yoy={eps_growth}%, "
                    f"profit_margin={margin}%, debt_to_equity={de_ratio}, pe_ratio={pe}, sector_avg_pe={sector_pe}"
                ),
                relevance=1.0,
                kind="dataset",
            )
        ]

        rag_query = f"{question} revenue growth margins debt valuation"
        try:
            retrieved = get_engine().retrieve(ticker, rag_query, top_k=2)
            for r in retrieved:
                evidence.append(
                    Evidence(
                        source=r["source"],
                        document=r["document"],
                        chunk=r["chunk"],
                        relevance=r["relevance"],
                        kind="document",
                    )
                )
                factors.append(f"Filing evidence retrieved from {r['source']} (relevance {r['relevance']:.2f})")
        except Exception:
            warnings.append("Filing retrieval unavailable — relying on structured fundamentals only")

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
