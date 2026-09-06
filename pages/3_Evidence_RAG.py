"""NEXUS — Evidence & RAG explorer page."""
from __future__ import annotations

import streamlit as st

from core.profiler import load_portfolios
from core.rag import get_engine, TICKER_TO_FILE, DOC_LABELS
from core.state import init_state
from components.styles import inject, source_tag
from components.sidebar import render_sidebar, TICKERS

st.set_page_config(page_title="NEXUS | Evidence & RAG", layout="wide", page_icon="assets/logo.svg")
inject()
init_state()

portfolios = load_portfolios()
profile, portfolio = render_sidebar(portfolios)

st.markdown('<div class="nx-header-title" style="font-size:1.9rem;">Evidence &amp; RAG</div>', unsafe_allow_html=True)
st.caption("The Fundamental Agent retrieves from this same engine during an investigation. "
           "Use this page to inspect the underlying documents and query retrieval directly.")

engine = get_engine()
st.markdown(f"**RAG mode:** {source_tag(engine.mode)}", unsafe_allow_html=True)
st.caption(
    "VECTOR = TF-IDF cosine-similarity retrieval (scikit-learn) over the filing text below. "
    "KEYWORD_FALLBACK = plain substring matching, used automatically if vectorization fails. "
    "Either way, retrieval never crashes the app."
)

st.markdown('<div class="nx-section-title">Ad-hoc Retrieval Query</div>', unsafe_allow_html=True)
q1, q2 = st.columns([1, 2])
with q1:
    tkr = st.selectbox("Company", TICKERS, key="rag_ticker")
with q2:
    query = st.text_input("Query", value="revenue growth and margin pressure")

if st.button("Retrieve"):
    results = engine.retrieve(tkr, query, top_k=4)
    if not results:
        st.warning("No matching chunks retrieved for this query.")
    for r in results:
        st.markdown(f"""
        <div class="nx-card">
        <span class="nx-evidence-src">{r['source']}</span>
        <span style="color:var(--muted);font-size:0.75rem;"> · {r['document']} · relevance {r['relevance']:.2f}</span><br>
        <span class="nx-evidence-chunk">{r['chunk']}</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="nx-section-title">Source Documents</div>', unsafe_allow_html=True)
st.caption(
    "These are curated Q1 FY27 earnings-summary documents used as the RAG corpus for this "
    "hackathon build (see the About page for why full real regulatory filings weren't scraped live)."
)
for tkr in TICKERS:
    fname = TICKER_TO_FILE.get(tkr)
    label = DOC_LABELS.get(fname, fname)
    with st.expander(f"{label} ({fname})"):
        chunks = [c for c in engine.chunks if c.doc_file == fname]
        for c in chunks:
            st.markdown(f'<div class="nx-row-text" style="padding:4px 0;">{c.text}</div>', unsafe_allow_html=True)
            st.markdown("---")
