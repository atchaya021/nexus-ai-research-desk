"""
Technical Agent — analyzes momentum, moving averages, RSI, volume, volatility.

All logic is deterministic and calculated directly from the local market
dataset. No LLM is involved in the calculation itself.
"""
from __future__ import annotations

from agents.base import BaseAgent, AgentResult, Evidence


class TechnicalAgent(BaseAgent):
    name = "technical"

    def run(self, ticker: str, market_data: dict) -> AgentResult:
        return self._timed(self._analyze, ticker, market_data)

    def _analyze(self, ticker: str, market_data: dict) -> AgentResult:
        t = market_data["technical"]
        price = t["price"]
        dma20 = t["dma_20"]
        dma50 = t["dma_50"]
        rsi = t["rsi_14"]
        volume = t["volume"]
        avg_volume = t["avg_volume_20d"]
        volatility = t["volatility_30d"]
        momentum = t["momentum_10d"]

        score = 50
        factors: list[str] = []
        warnings: list[str] = []

        if price > dma20:
            score += 10
            factors.append(f"Price {price:.2f} is above the 20-day moving average ({dma20:.2f})")
        else:
            score -= 10
            factors.append(f"Price {price:.2f} is below the 20-day moving average ({dma20:.2f})")

        if price > dma50:
            score += 8
            factors.append(f"Price is above the 50-day moving average ({dma50:.2f})")
        else:
            score -= 8
            factors.append(f"Price is below the 50-day moving average ({dma50:.2f})")

        vol_ratio = volume / avg_volume if avg_volume else 1.0
        if vol_ratio > 1.5:
            score += 8
            factors.append(f"Volume is {vol_ratio:.2f}x the 20-day average, indicating strong participation")
        elif vol_ratio < 0.6:
            score -= 4
            factors.append(f"Volume is only {vol_ratio:.2f}x the 20-day average, indicating weak participation")

        if 50 <= rsi <= 70:
            score += 10
            factors.append(f"RSI(14) at {rsi:.1f} shows healthy bullish momentum without being overbought")
        elif rsi > 75:
            score -= 6
            warnings.append(f"RSI(14) at {rsi:.1f} is in overbought territory (>75)")
            factors.append(f"RSI(14) at {rsi:.1f} signals overbought conditions")
        elif rsi < 30:
            score -= 10
            factors.append(f"RSI(14) at {rsi:.1f} signals oversold conditions")
        else:
            factors.append(f"RSI(14) at {rsi:.1f} is neutral")

        if momentum > 0:
            score += 6
            factors.append(f"10-day price momentum is positive at +{momentum:.1f}%")
        else:
            score -= 6
            factors.append(f"10-day price momentum is negative at {momentum:.1f}%")

        if volatility > 20:
            warnings.append(f"30-day volatility of {volatility:.1f}% is elevated")
        score = max(0, min(100, score))

        if score >= 65:
            signal = "BULLISH"
        elif score <= 40:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        confidence = round(score / 100, 2)

        evidence = [
            Evidence(
                source="Market Data Feed (Demo)",
                document="data/market.json",
                chunk=(
                    f"{ticker}: price={price}, 20DMA={dma20}, 50DMA={dma50}, "
                    f"RSI14={rsi}, volume={volume}, avg_volume_20d={avg_volume}, "
                    f"volatility_30d={volatility}%, momentum_10d={momentum}%"
                ),
                relevance=1.0,
                kind="dataset",
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
