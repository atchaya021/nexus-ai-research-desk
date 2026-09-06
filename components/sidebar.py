"""Shared sidebar — investor profile, portfolio glance, data-source toggle,
and demo resilience controls. Identical on every page so switching pages
never loses context."""
from __future__ import annotations

import streamlit as st
from core.profiler import get_profile, get_portfolio
from components.styles import badge

PROFILE_KEYS = ["conservative", "moderate", "aggressive"]
TICKERS = ["RELIANCE", "TCS", "INFOSYS", "HDFCBANK", "ICICIBANK"]


def render_sidebar(portfolios: dict) -> tuple[dict, dict]:
    with st.sidebar:
        st.markdown("### Investor Profile")
        profile_label = st.radio(
            "Risk profile", ["Conservative", "Moderate", "Aggressive"],
            index=PROFILE_KEYS.index(st.session_state.profile_key),
            label_visibility="collapsed", key="profile_radio",
        )
        st.session_state.profile_key = profile_label.lower()

        profile = get_profile(portfolios, st.session_state.profile_key)
        portfolio = get_portfolio(portfolios, st.session_state.profile_key)

        st.markdown(f"""
        <div class="nx-card">
        <b>{profile['name']}</b><br>
        Risk tolerance: {profile['risk_tolerance']}<br>
        Horizon: {profile['investment_horizon']}<br>
        Max position: {profile['max_preferred_position_pct']}%<br>
        Volatility tolerance: {profile['volatility_tolerance']}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### Portfolio")
        st.write(f"Value: ₹{portfolio['portfolio_value']:,}")
        st.write(f"Risk score: {portfolio['portfolio_risk_score']}/100")
        for tkr, h in portfolio["holdings"].items():
            st.caption(f"{tkr}: {h['allocation_pct']}% alloc, qty {h['quantity']}")

        st.markdown("### Data Source")
        st.session_state.use_live_data = st.toggle(
            "Use live market data (Yahoo Finance)", value=st.session_state.use_live_data,
            help="When on, NEXUS fetches real prices/history via yfinance. "
                 "If the live fetch fails for any reason, it falls back to the "
                 "cached demo dataset automatically and labels it DEMO.",
        )

        st.markdown("### Demo Controls")
        if st.button("Simulate Data Failure", width="stretch"):
            st.session_state.data_degraded = not st.session_state.data_degraded
        if st.button("Simulate Signal Conflict", width="stretch"):
            st.session_state.force_conflict = not st.session_state.force_conflict
        if st.session_state.data_degraded:
            st.markdown(badge("DATA DEGRADED"), unsafe_allow_html=True)
        if st.session_state.force_conflict:
            st.markdown(badge("CONFLICT MODE"), unsafe_allow_html=True)

        st.caption(f"Session: {st.session_state.session_id}")

    return profile, portfolio
