"""
Loads investor profiles and their associated demo portfolios.
"""
from __future__ import annotations

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_portfolios() -> dict:
    with open(os.path.join(DATA_DIR, "portfolio.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_market() -> dict:
    with open(os.path.join(DATA_DIR, "market.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_news() -> dict:
    with open(os.path.join(DATA_DIR, "news.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def get_profile(portfolios: dict, key: str) -> dict:
    return portfolios[key]["profile"]


def get_portfolio(portfolios: dict, key: str) -> dict:
    entry = portfolios[key]
    return {
        "portfolio_value": entry["portfolio_value"],
        "holdings": entry["holdings"],
        "sector_exposure": entry["sector_exposure"],
        "portfolio_risk_score": entry["portfolio_risk_score"],
    }
