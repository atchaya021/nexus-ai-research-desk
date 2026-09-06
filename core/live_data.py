"""
Live market data via yfinance (Yahoo Finance) — free, no API key required.

This is the REAL data path: real historical prices, real computed technical
indicators (DMA/RSI/volatility/momentum from actual price history), and
whatever fundamentals Yahoo exposes for the ticker (P/E, margins, debt/equity
where available).

Every call is wrapped so a network failure, a Yahoo rate-limit, or a blocked
host NEVER crashes the app — it falls back to the last-known cached snapshot
in data/market.json (labeled DEMO/CACHED in the UI) using the exact same
mechanism as the "Simulate Data Failure" demo control. This is not a
hypothetical fallback: some sandboxed/cloud environments block Yahoo's
endpoints outright, so this path is exercised in practice, not just in theory.
"""
from __future__ import annotations

import time
import numpy as np

NSE_TICKERS = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "INFOSYS": "INFY.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
}

INDEX_TICKERS = {"NIFTY": "^NSEI", "SENSEX": "^BSESN", "BANKNIFTY": "^NSEBANK"}

_CACHE: dict = {}
_CACHE_TTL_SECONDS = 300  # avoid hammering Yahoo on every rerun/widget interaction


def _cache_get(key):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry[0]) < _CACHE_TTL_SECONDS:
        return entry[1]
    return None


def _cache_set(key, value):
    _CACHE[key] = (time.time(), value)


def _rsi(closes: "np.ndarray", period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = gains.mean()
    avg_loss = losses.mean()
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def fetch_live_technical(ticker: str) -> dict | None:
    """Returns a technical dict built from REAL historical prices, or None on
    any failure (network blocked, rate-limited, ticker not found, etc.)."""
    cache_key = f"tech:{ticker}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        import yfinance as yf

        yf_symbol = NSE_TICKERS.get(ticker)
        if not yf_symbol:
            return None
        hist = yf.Ticker(yf_symbol).history(period="4mo", interval="1d")
        if hist is None or hist.empty or len(hist) < 21:
            return None

        closes = hist["Close"].to_numpy()
        volumes = hist["Volume"].to_numpy()

        price = float(closes[-1])
        previous_close = float(closes[-2])
        dma_20 = float(closes[-20:].mean())
        dma_50 = float(closes[-50:].mean()) if len(closes) >= 50 else float(closes.mean())
        volume = float(volumes[-1])
        avg_volume_20d = float(volumes[-20:].mean())
        daily_returns = np.diff(closes[-31:]) / closes[-31:-1] if len(closes) >= 31 else np.diff(closes) / closes[:-1]
        volatility_30d = round(float(np.std(daily_returns) * np.sqrt(252) * 100), 1) if len(daily_returns) > 1 else 0.0
        momentum_10d = round(float((closes[-1] - closes[-10]) / closes[-10] * 100), 1) if len(closes) >= 10 else 0.0
        rsi_14 = _rsi(closes, 14)

        result = {
            "price": round(price, 2),
            "previous_close": round(previous_close, 2),
            "volume": int(volume),
            "avg_volume_20d": int(avg_volume_20d),
            "dma_20": round(dma_20, 2),
            "dma_50": round(dma_50, 2),
            "rsi_14": rsi_14,
            "volatility_30d": volatility_30d,
            "momentum_10d": momentum_10d,
            "week52_high": round(float(hist["High"].max()), 2),
            "week52_low": round(float(hist["Low"].min()), 2),
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        return None


def fetch_live_fundamentals(ticker: str) -> dict | None:
    cache_key = f"fund:{ticker}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        import yfinance as yf

        yf_symbol = NSE_TICKERS.get(ticker)
        if not yf_symbol:
            return None
        info = yf.Ticker(yf_symbol).info
        if not info or "trailingPE" not in info and "revenueGrowth" not in info:
            return None

        result = {
            "revenue_growth_yoy": round((info.get("revenueGrowth") or 0.0) * 100, 1),
            "eps_growth_yoy": round((info.get("earningsGrowth") or 0.0) * 100, 1),
            "profit_margin": round((info.get("profitMargins") or 0.0) * 100, 1),
            "debt_to_equity": round((info.get("debtToEquity") or 0.0) / 100, 2),
            "pe_ratio": round(info.get("trailingPE") or 0.0, 1),
            "sector_avg_pe": round(info.get("trailingPE") or 0.0, 1),  # Yahoo has no clean sector-avg field
            "next_earnings_date": "UNAVAILABLE",
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        return None


_POSITIVE_WORDS = {"beat", "beats", "surge", "surges", "growth", "profit", "profits", "upgrade", "upgrades",
                    "wins", "win", "rally", "rallies", "gain", "gains", "record", "expands", "expansion",
                    "strong", "outperform", "raises", "raise", "jump", "jumps", "bullish", "buy"}
_NEGATIVE_WORDS = {"miss", "misses", "falls", "fall", "decline", "declines", "downgrade", "downgrades",
                    "loss", "losses", "probe", "lawsuit", "fraud", "cut", "cuts", "weak", "plunge", "plunges",
                    "drop", "drops", "bearish", "sell", "warning", "concern", "concerns", "slump"}


def _classify_tone(title: str) -> str:
    lower = title.lower()
    pos = sum(1 for w in _POSITIVE_WORDS if w in lower)
    neg = sum(1 for w in _NEGATIVE_WORDS if w in lower)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def fetch_live_news(ticker: str) -> dict | None:
    cache_key = f"news:{ticker}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        import yfinance as yf

        yf_symbol = NSE_TICKERS.get(ticker)
        if not yf_symbol:
            return None
        items = yf.Ticker(yf_symbol).news
        if not items:
            return None

        headlines = []
        for item in items[:8]:
            content = item.get("content", item)
            title = content.get("title") or item.get("title")
            if not title:
                continue
            pub = content.get("pubDate") or ""
            tone = _classify_tone(title)
            headlines.append({"title": title, "tone": tone, "date": pub[:10] if pub else "recent"})

        if not headlines:
            return None
        pos = sum(1 for h in headlines if h["tone"] == "positive")
        neg = sum(1 for h in headlines if h["tone"] == "negative")
        neu = sum(1 for h in headlines if h["tone"] == "neutral")
        result = {
            "positive_count": pos, "negative_count": neg, "neutral_count": neu,
            "institutional_flow": "UNAVAILABLE",  # Yahoo does not expose a free institutional-flow signal
            "headlines": headlines,
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        return None


def fetch_live_indices() -> dict | None:
    cache_key = "indices"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        import yfinance as yf

        out = {}
        for name, symbol in INDEX_TICKERS.items():
            hist = yf.Ticker(symbol).history(period="5d")
            if hist is None or hist.empty:
                return None
            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            out[name] = {"value": round(last, 2), "change_pct": round((last - prev) / prev * 100, 2)}
        _cache_set(cache_key, out)
        return out
    except Exception:
        return None
