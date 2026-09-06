"""
Sentiment Agent — analyzes news tone counts and institutional flow.
"""
from __future__ import annotations

from agents.base import BaseAgent, AgentResult, Evidence


class SentimentAgent(BaseAgent):
    name = "sentiment"

    def run(self, ticker: str, news_data: dict) -> AgentResult:
        return self._timed(self._analyze, ticker, news_data)

    def _analyze(self, ticker: str, news_data: dict) -> AgentResult:
        pos = news_data["positive_count"]
        neg = news_data["negative_count"]
        neu = news_data["neutral_count"]
        flow = news_data["institutional_flow"]
        total = pos + neg + neu

        score = 50
        factors: list[str] = []
        warnings: list[str] = []

        if total == 0:
            warnings.append("No news volume available for this ticker")
        else:
            net_ratio = (pos - neg) / total
            score += round(net_ratio * 35)
            factors.append(f"News mix: {pos} positive / {neg} negative / {neu} neutral (net tone {net_ratio:+.2f})")

        if flow == "NET_BUYING":
            score += 12
            factors.append("Institutional flow signal indicates net buying")
        elif flow == "NET_SELLING":
            score -= 12
            factors.append("Institutional flow signal indicates net selling")
        else:
            factors.append("Institutional flow signal is neutral")

        if neg > pos:
            warnings.append("Negative headline count exceeds positive headline count")

        score = max(0, min(100, score))
        if score >= 62:
            signal = "BULLISH"
        elif score <= 42:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"
        confidence = round(score / 100, 2)

        evidence = [
            Evidence(
                source="News & Flow Data (Demo)",
                document="data/news.json",
                chunk=f"{ticker}: positive={pos}, negative={neg}, neutral={neu}, institutional_flow={flow}",
                relevance=1.0,
                kind="dataset",
            )
        ]
        headlines = news_data.get("headlines", [])[:2]
        for h in headlines:
            evidence.append(
                Evidence(
                    source="News Headline (Demo)",
                    document="data/news.json",
                    chunk=f"[{h['tone'].upper()}] {h['title']} ({h['date']})",
                    relevance=0.8,
                    kind="dataset",
                )
            )

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
