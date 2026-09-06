"""NEXUS — Portfolio page."""
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

from core.profiler import load_market, load_portfolios
from core.data_gateway import get_market_snapshot
from core.simulator import simulate_allocation_change
from core.state import init_state
from components.styles import inject, warning_strip
from components.sidebar import render_sidebar, TICKERS

st.set_page_config(page_title="NEXUS | Portfolio", layout="wide", page_icon="assets/logo.svg")
inject()
init_state()

market_all = load_market()
portfolios = load_portfolios()
profile, portfolio = render_sidebar(portfolios)

st.markdown('<div class="nx-header-title" style="font-size:1.9rem;">Portfolio</div>', unsafe_allow_html=True)
st.caption(f"Demo portfolio for the {profile['name']} investor profile.")

k1, k2, k3 = st.columns(3)
k1.metric("Portfolio Value", f"₹{portfolio['portfolio_value']:,}")
k2.metric("Portfolio Risk Score", f"{portfolio['portfolio_risk_score']}/100")
k3.metric("Number of Holdings", len(portfolio["holdings"]))

st.markdown('<div class="nx-section-title">Holdings</div>', unsafe_allow_html=True)
rows = []
for tkr, h in portfolio["holdings"].items():
    snap, sources = get_market_snapshot(tkr, market_all, st.session_state.use_live_data)
    price = snap["technical"]["price"]
    mkt_value = price * h["quantity"]
    pnl_pct = (price - h["avg_price"]) / h["avg_price"] * 100
    rows.append({
        "Ticker": tkr, "Qty": h["quantity"], "Avg Price": h["avg_price"],
        "Current Price": price, "Allocation %": h["allocation_pct"],
        "Market Value": round(mkt_value, 2), "P&L %": round(pnl_pct, 2),
        "Data": sources["technical"],
    })
st.dataframe(rows, width="stretch", hide_index=True)

st.markdown('<div class="nx-section-title">Sector Exposure</div>', unsafe_allow_html=True)
ch1, ch2 = st.columns(2)
with ch1:
    sectors = list(portfolio["sector_exposure"].keys())
    values = list(portfolio["sector_exposure"].values())
    fig = go.Figure(data=[go.Pie(labels=sectors, values=values, hole=0.55)])
    fig.update_layout(title="Sector Allocation", template="plotly_dark",
                       paper_bgcolor="#11151e", height=300, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, width="stretch")
with ch2:
    fig2 = go.Figure(go.Indicator(
        mode="gauge+number", value=portfolio["portfolio_risk_score"],
        title={"text": "Portfolio Risk Score"},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#4aa3e0"},
               "steps": [{"range": [0, 45], "color": "#1e2430"},
                         {"range": [45, 65], "color": "#2a2515"},
                         {"range": [65, 100], "color": "#2a1515"}]},
    ))
    fig2.update_layout(template="plotly_dark", paper_bgcolor="#11151e", height=300,
                        margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig2, width="stretch")

st.markdown('<div class="nx-section-title">What-if Allocation Simulator</div>', unsafe_allow_html=True)
s1, s2 = st.columns([1, 2])
with s1:
    sim_ticker = st.selectbox("Stock", TICKERS, format_func=lambda t: market_all[t]["name"], key="sim_ticker")
    current = portfolio["holdings"].get(sim_ticker, {}).get("allocation_pct", 0.0)
    proposed = st.slider("Proposed allocation (%)", 0.0, 30.0, min(30.0, current + 5.0), 0.5, key="sim_slider")
with s2:
    snap, _ = get_market_snapshot(sim_ticker, market_all, st.session_state.use_live_data)
    sim = simulate_allocation_change(sim_ticker, snap, profile, portfolio, proposed)
    m1, m2, m3 = st.columns(3)
    m1.metric("Current → Proposed", f"{sim.current_allocation:.1f}% → {sim.proposed_allocation:.1f}%")
    m2.metric("Risk Score Change", f"{sim.current_risk_score} → {sim.proposed_risk_score}", f"{sim.delta:+d}")
    m3.metric("Signal", f"{sim.current_signal} → {sim.proposed_signal}")
    if sim.threshold_exceeded:
        st.markdown(warning_strip(f"Risk threshold exceeded — exceeds {profile['name']} preferred maximum of {sim.max_preferred_pct:.0f}%"), unsafe_allow_html=True)
    else:
        st.caption("Within preferred risk threshold.")
