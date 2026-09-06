"""NEXUS — Investigation page."""
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

from core.profiler import load_market, load_news, load_portfolios
from core.data_gateway import get_market_snapshot, get_news_snapshot
from core.orchestrator import run_investigation
from core.simulator import simulate_allocation_change
from core import database
from core.state import init_state
from components.styles import inject, badge, source_tag, signal_color, row, warning_strip, safe_page_link
from components.sidebar import render_sidebar, TICKERS
from utils.metrics import evidence_coverage, signal_agreement, total_evidence_sources, avg_agent_latency_ms

st.set_page_config(page_title="NEXUS | Investigation", layout="wide", page_icon="assets/logo.svg")
inject()
init_state()

market_all = load_market()
news_all = load_news()
portfolios = load_portfolios()

profile, portfolio = render_sidebar(portfolios)

st.markdown('<div class="nx-header-title" style="font-size:1.9rem;">Investigation</div>', unsafe_allow_html=True)
st.caption("Ask a question. Technical, Fundamental, Sentiment, and Risk agents run in parallel; "
           "Governance and Synthesis combine their outputs into one personalized call.")

i1, i2 = st.columns([1, 3])
with i1:
    ticker = st.selectbox("Stock", TICKERS, format_func=lambda t: market_all[t]["name"],
                           index=TICKERS.index(st.session_state.ticker))
    st.session_state.ticker = ticker
with i2:
    default_q = f"Should I increase my {market_all[ticker]['name']} position?"
    question = st.text_input("Question", value=default_q)

market_snapshot, market_sources = get_market_snapshot(ticker, market_all, st.session_state.use_live_data)
news_snapshot, news_source = get_news_snapshot(ticker, news_all, st.session_state.use_live_data)

sc1, sc2 = st.columns(2)
sc1.markdown(f"Technical data &nbsp; {source_tag(market_sources['technical'])}", unsafe_allow_html=True)
sc2.markdown(f"News data &nbsp; {source_tag(news_source)}", unsafe_allow_html=True)

current_alloc = portfolio["holdings"].get(ticker, {}).get("allocation_pct", 0.0)
proposed_alloc = st.slider(
    "Proposed new allocation (%) — used by the Risk Agent",
    min_value=0.0, max_value=25.0, value=min(25.0, current_alloc + 3.0), step=0.5,
)

behavioral = database.get_behavioral_history(profile["name"], profile["max_preferred_position_pct"])
if behavioral["sample_size"]:
    bc1, bc2, bc3 = st.columns(3)
    bc1.metric("Past investigations (this profile)", behavioral["sample_size"])
    bc2.metric("Avg confidence", f"{behavioral['avg_confidence']*100:.0f}%" if behavioral["avg_confidence"] is not None else "—")
    bc3.metric("Override rate", f"{behavioral['override_rate']*100:.0f}%" if behavioral["override_rate"] is not None else "—")
    st.caption(
        "Behavioral history spans every session for this profile (Streamlit + React), "
        "and is fed to the Risk Agent below once it reaches "
        f"{3} past investigations."
    )

run = st.button("Run Investigation", type="primary")

if run:
    with st.spinner("Running parallel agent investigation..."):
        investigation = run_investigation(
            ticker=ticker, question=question,
            market_data=market_snapshot, news_data=news_snapshot,
            profile=profile, portfolio=portfolio,
            proposed_allocation_pct=proposed_alloc,
            data_degraded=st.session_state.data_degraded,
            force_conflict=st.session_state.force_conflict,
            behavioral=behavioral,
        )
        database.log_investigation(
            st.session_state.session_id, ticker, profile["name"], investigation,
            proposed_allocation_pct=proposed_alloc,
        )
        database.log_portfolio_snapshot(st.session_state.session_id, profile["name"], portfolio)
        st.session_state.investigation = investigation

investigation = st.session_state.investigation

if investigation and investigation.ticker == ticker:
    st.markdown('<div class="nx-section-title">Agent War Room</div>', unsafe_allow_html=True)
    agents = [investigation.technical, investigation.fundamental, investigation.sentiment,
              investigation.risk, investigation.governance]
    cols = st.columns(5)
    for col, a in zip(cols, agents):
        with col:
            st.markdown(f"""
            <div class="nx-card">
            <b>{a.agent.upper()}</b><br>
            {badge(a.signal)}<br>
            <span style="color:var(--muted);font-size:0.78rem;">confidence {a.confidence*100:.0f}% &middot; score {a.score}</span><br>
            <span style="color:var(--muted-2);font-size:0.74rem;">latency {a.latency_ms:.0f} ms &middot; {a.status}</span>
            """, unsafe_allow_html=True)
            for f in a.factors[:3]:
                st.markdown(row(f, "neutral"), unsafe_allow_html=True)
            for w in a.warnings[:2]:
                st.markdown(warning_strip(w), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="nx-section-title">Evidence</div>', unsafe_allow_html=True)
    st.caption(f"RAG mode: {investigation.rag_mode}")
    all_evidence = []
    for a in [investigation.technical, investigation.fundamental, investigation.sentiment, investigation.risk]:
        all_evidence.extend(a.evidence)
    for e in all_evidence:
        st.markdown(f"""
        <div class="nx-card">
        <span class="nx-evidence-src">{e.source}</span>
        <span style="color:var(--muted-2);font-size:0.74rem;"> &middot; {e.document} &middot; relevance {e.relevance:.2f}</span><br>
        <span class="nx-evidence-chunk">{e.chunk}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="nx-section-title">Synthesis</div>', unsafe_allow_html=True)
    syn = investigation.synthesis
    syc1, syc2 = st.columns([1, 2])
    with syc1:
        st.markdown(f"""
        <div class="nx-card" style="text-align:center;">
        <div style="font-family:'Playfair Display',serif;font-size:2.1rem;font-weight:700;color:{signal_color(syn.final_signal)};">{syn.final_signal}</div>
        <div style="color:var(--muted);letter-spacing:0.06em;">{syn.confidence*100:.0f}% CONFIDENCE</div>
        </div>
        """, unsafe_allow_html=True)
    with syc2:
        st.write(syn.summary)
        st.caption(syn.personalization_reason)

    wc1, wc2 = st.columns(2)
    with wc1:
        st.markdown("**Why**")
        for f in syn.positive_factors:
            st.markdown(row(f, "positive"), unsafe_allow_html=True)
    with wc2:
        st.markdown("**Why not**")
        for f in (syn.negative_factors + syn.risk_factors)[:6]:
            st.markdown(row(f, "negative"), unsafe_allow_html=True)

    st.markdown("**Portfolio impact — counterfactual simulator**")
    sim = simulate_allocation_change(ticker, market_snapshot, profile, portfolio, proposed_alloc)
    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("Allocation", f"{sim.proposed_allocation:.1f}%", f"{sim.proposed_allocation - sim.current_allocation:+.1f}pp")
    pc2.metric("Risk Score", f"{sim.proposed_risk_score}", f"{sim.delta:+d}")
    pc3.metric("Signal", sim.proposed_signal)
    if sim.threshold_exceeded:
        st.markdown(warning_strip(
            f"Risk threshold exceeded — proposed allocation exceeds the {profile['name']} profile's "
            f"preferred maximum of {sim.max_preferred_pct:.0f}%"
        ), unsafe_allow_html=True)

    st.markdown('<div class="nx-section-title">Charts</div>', unsafe_allow_html=True)
    ch1, ch2 = st.columns(2)
    with ch1:
        t = market_snapshot["technical"]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["Prev Close", "Price", "20DMA", "50DMA"],
                              y=[t["previous_close"], t["price"], t["dma_20"], t["dma_50"]],
                              marker_color=["#5f5f6b", "#6f93b8", "#4fa87c", "#cf9f52"]))
        fig.update_layout(title="Price vs Moving Averages", template="plotly_dark",
                           paper_bgcolor="#131318", plot_bgcolor="#131318", height=280,
                           font=dict(family="IBM Plex Mono, monospace"),
                           margin=dict(l=10, r=10, t=40, b=10),
                           transition=dict(duration=500, easing="cubic-in-out"))
        st.plotly_chart(fig, width="stretch")
    with ch2:
        fig2 = go.Figure()
        agent_names = [a.agent for a in agents]
        agent_scores = [a.score for a in agents]
        colors = [signal_color(a.signal) for a in agents]
        fig2.add_trace(go.Bar(x=agent_names, y=agent_scores, marker_color=colors))
        fig2.update_layout(title="Agent Signal Comparison", template="plotly_dark",
                            paper_bgcolor="#131318", plot_bgcolor="#131318", height=280,
                            font=dict(family="IBM Plex Mono, monospace"),
                            margin=dict(l=10, r=10, t=40, b=10),
                            transition=dict(duration=500, easing="cubic-in-out"))
        st.plotly_chart(fig2, width="stretch")

    st.markdown('<div class="nx-section-title">Performance</div>', unsafe_allow_html=True)
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total latency", f"{investigation.total_latency_ms:.0f} ms")
    m2.metric("Avg agent latency", f"{avg_agent_latency_ms(investigation):.0f} ms")
    m3.metric("Evidence coverage", f"{evidence_coverage(investigation)*100:.0f}%")
    m4.metric("Signal agreement", f"{signal_agreement(investigation)*100:.0f}%")
    m5.metric("Sources retrieved", total_evidence_sources(investigation))
    m6.metric("Portfolio risk", f"{portfolio['portfolio_risk_score']}/100")

    safe_page_link("pages/4_Decision_Trace.py", "View full decision trace")
else:
    st.info("Select a stock and click Run Investigation to launch the parallel agent pipeline.")
