"""NEXUS — Decision Trace & Metrics page."""
from __future__ import annotations

import sqlite3
import streamlit as st

from core.profiler import load_portfolios
from core.database import DB_PATH, _connect
from core.state import init_state
from components.styles import inject
from components.sidebar import render_sidebar
from utils.metrics import evidence_coverage, signal_agreement, total_evidence_sources, avg_agent_latency_ms

st.set_page_config(page_title="NEXUS | Decision Trace", layout="wide", page_icon="assets/logo.svg")
inject()
init_state()

portfolios = load_portfolios()
profile, portfolio = render_sidebar(portfolios)

st.markdown('<div class="nx-header-title" style="font-size:1.9rem;">Decision Trace</div>', unsafe_allow_html=True)

investigation = st.session_state.investigation

if investigation:
    st.markdown(f'<div class="nx-section-title">Last Investigation &mdash; {investigation.ticker}</div>', unsafe_allow_html=True)
    st.caption(f'"{investigation.question}"')
    for event in investigation.trace:
        st.markdown(f'<div class="nx-trace-line">{event.timestamp}  {event.message}</div>', unsafe_allow_html=True)

    st.markdown('<div class="nx-section-title">Performance &mdash; This Investigation</div>', unsafe_allow_html=True)
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total latency", f"{investigation.total_latency_ms:.0f} ms")
    m2.metric("Avg agent latency", f"{avg_agent_latency_ms(investigation):.0f} ms")
    m3.metric("Evidence coverage", f"{evidence_coverage(investigation)*100:.0f}%")
    m4.metric("Signal agreement", f"{signal_agreement(investigation)*100:.0f}%")
    m5.metric("Sources retrieved", total_evidence_sources(investigation))
    m6.metric("RAG mode", investigation.rag_mode)
else:
    st.info("No investigation has been run yet in this session. Go to the Investigation page to run one.")

st.markdown('<div class="nx-section-title">Session History (SQLite)</div>', unsafe_allow_html=True)
st.caption(f"Local database: {DB_PATH}")
try:
    conn = _connect()
    rows = conn.execute(
        "SELECT timestamp, stock, user_profile, final_decision, confidence "
        "FROM recommendations WHERE session_id=? ORDER BY id DESC LIMIT 25",
        (st.session_state.session_id,),
    ).fetchall()
    conn.close()
    if rows:
        st.dataframe(
            [{"Time": r[0][11:19], "Stock": r[1], "Profile": r[2], "Decision": r[3], "Confidence": f"{r[4]*100:.0f}%"} for r in rows],
            width="stretch", hide_index=True,
        )
    else:
        st.caption("No recommendations logged yet this session.")
except sqlite3.Error as e:
    st.warning(f"Could not read session history: {e}")
