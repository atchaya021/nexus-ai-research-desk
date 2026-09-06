"""
Single point of truth for "where did this number come from".

Every page calls through here instead of touching data/market.json or
core/live_data.py directly, so the LIVE vs DEMO label the UI shows is always
accurate and computed the same way everywhere.
"""
from __future__ import annotations

from core import live_data


def get_market_snapshot(ticker: str, demo_market: dict, use_live: bool) -> tuple[dict, dict]:
    """Returns (market_data_dict, source_labels) where market_data_dict has the
    same shape as an entry in data/market.json ({name, sector, technical,
    fundamental}), and source_labels marks each section LIVE or DEMO."""
    demo_entry = demo_market[ticker]
    technical = None
    fundamental = None

    if use_live:
        technical = live_data.fetch_live_technical(ticker)
        fundamental = live_data.fetch_live_fundamentals(ticker)
        if fundamental is not None:
            # Yahoo's free tier has no reliable sector-average P/E field, so that
            # one reference figure is carried over from the curated demo dataset
            # even in LIVE mode. Everything else in `fundamental` is live.
            fundamental["sector_avg_pe"] = demo_market[ticker]["fundamental"]["sector_avg_pe"]

    sources = {
        "technical": "LIVE" if technical else "DEMO (cached)",
        "fundamental": "LIVE" if fundamental else "DEMO (cached)",
    }
    result = {
        "name": demo_entry["name"],
        "sector": demo_entry["sector"],
        "technical": technical or demo_entry["technical"],
        "fundamental": fundamental or demo_entry["fundamental"],
    }
    return result, sources


def get_news_snapshot(ticker: str, demo_news: dict, use_live: bool) -> tuple[dict, str]:
    demo_entry = demo_news[ticker]
    news = live_data.fetch_live_news(ticker) if use_live else None
    if news:
        return news, "LIVE"
    return demo_entry, "DEMO (cached)"


def get_indices_snapshot(demo_indices: dict, use_live: bool) -> tuple[dict, str]:
    indices = live_data.fetch_live_indices() if use_live else None
    if indices:
        return indices, "LIVE"
    return demo_indices, "DEMO (cached)"
