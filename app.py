"""
NEXUS — The Retail Investor's AI Research Desk
Home / Market Overview page.

Educational / research prototype. Not financial advice.
"""
from __future__ import annotations

import streamlit as st

from core.profiler import load_market, load_news, load_portfolios
from core.data_gateway import get_indices_snapshot, get_market_snapshot
from core.state import init_state
from components.styles import inject, source_tag, safe_page_link
from components.sidebar import render_sidebar, TICKERS

st.set_page_config(page_title="NEXUS | AI Research Desk", layout="wide", page_icon="assets/logo.svg")
inject()
init_state()

market_all = load_market()
news_all = load_news()
portfolios = load_portfolios()

profile, portfolio = render_sidebar(portfolios)

# ---------------------------------------------------------------- header --
h1, h2, h3, h4 = st.columns([2.4, 1, 1, 1])
with h1:
    st.markdown('<div class="nx-header-title">NEXUS</div>', unsafe_allow_html=True)
    st.markdown('<div class="nx-header-sub">The Retail Investor\'s AI Research Desk</div>', unsafe_allow_html=True)
with h2:
    st.metric("MARKET STATUS", "OPEN" if not st.session_state.data_degraded else "DEGRADED")
with h3:
    st.metric("DATA MODE", "LIVE" if st.session_state.use_live_data else "DEMO")
with h4:
    st.metric("SESSION ID", st.session_state.session_id)

st.caption(
    "Educational / research prototype. Not financial advice. Not a regulated investment advisor. "
    "Toggle live data in the sidebar — see the About page for exactly where every number comes from."
)

# ---------------------------------------------------------- market overview --
st.markdown('<div class="nx-section-title">Market Overview</div>', unsafe_allow_html=True)
indices, idx_source = get_indices_snapshot(market_all["_indices"], st.session_state.use_live_data)
st.markdown(source_tag(idx_source), unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
c1.metric("NIFTY", f"{indices['NIFTY']['value']:,}", f"{indices['NIFTY']['change_pct']:+.2f}%")
c2.metric("SENSEX", f"{indices['SENSEX']['value']:,}", f"{indices['SENSEX']['change_pct']:+.2f}%")
c3.metric("BANK NIFTY", f"{indices['BANKNIFTY']['value']:,}", f"{indices['BANKNIFTY']['change_pct']:+.2f}%")

st.markdown('<div class="nx-section-title">Watchlist</div>', unsafe_allow_html=True)
wl_cols = st.columns(5)
for i, tkr in enumerate(TICKERS):
    snap, sources = get_market_snapshot(tkr, market_all, st.session_state.use_live_data)
    t = snap["technical"]
    chg = (t["price"] - t["previous_close"]) / t["previous_close"] * 100
    with wl_cols[i]:
        st.metric(tkr, f"{t['price']:.2f}", f"{chg:+.2f}%")
        st.markdown(source_tag(sources["technical"]), unsafe_allow_html=True)

# --------------------------------------------------------------- navigation --
st.markdown('<div class="nx-section-title">Research Desk</div>', unsafe_allow_html=True)
n1, n2, n3 = st.columns(3)
with n1:
    st.markdown("""
    <div class="nx-nav-card"><div class="nx-kicker">01</div><h4>Investigation</h4>
    <p>Ask a question about a stock. Five agents run in parallel, retrieve evidence, and
    produce a personalized ACCUMULATE / HOLD / WATCH / REDUCE / AVOID call.</p></div>
    """, unsafe_allow_html=True)
    safe_page_link("pages/1_Investigation.py", "Open Investigation")
with n2:
    st.markdown("""
    <div class="nx-nav-card"><div class="nx-kicker">02</div><h4>Portfolio</h4>
    <p>See holdings, sector exposure, and risk score for the selected investor profile,
    and run a what-if allocation simulator.</p></div>
    """, unsafe_allow_html=True)
    safe_page_link("pages/2_Portfolio.py", "Open Portfolio")
with n3:
    st.markdown("""
    <div class="nx-nav-card"><div class="nx-kicker">03</div><h4>Evidence &amp; RAG</h4>
    <p>Browse the underlying filing documents and run ad-hoc retrieval queries against
    the evidence engine directly.</p></div>
    """, unsafe_allow_html=True)
    safe_page_link("pages/3_Evidence_RAG.py", "Open Evidence & RAG")

n4, n5, n6 = st.columns(3)
with n4:
    st.markdown("""
    <div class="nx-nav-card"><div class="nx-kicker">04</div><h4>Decision Trace</h4>
    <p>Full timestamped audit trail of the last investigation, plus session performance
    metrics and history.</p></div>
    """, unsafe_allow_html=True)
    safe_page_link("pages/4_Decision_Trace.py", "Open Decision Trace")
with n5:
    st.markdown("""
    <div class="nx-nav-card"><div class="nx-kicker">05</div><h4>About &amp; Architecture</h4>
    <p>What NEXUS does, exactly where every number comes from, the agent architecture,
    and the disclaimer.</p></div>
    """, unsafe_allow_html=True)
    safe_page_link("pages/5_About.py", "Open About")
with n6:
    st.markdown("""
    <div class="nx-nav-card" style="opacity:0.5;"><div class="nx-kicker">06</div><h4>Coming next</h4>
    <p>Multi-stock comparison view and alert rules — not built in this hackathon
    scope.</p></div>
    """, unsafe_allow_html=True)

st.markdown(
    '<div class="nx-disclaimer">NEXUS is an educational / research prototype for explainable, multi-agent '
    'decision support. It does not execute trades, is not a registered investment advisor, and does not '
    'guarantee returns.</div>',
    unsafe_allow_html=True,
)
