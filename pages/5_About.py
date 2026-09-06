"""NEXUS — About & Architecture page."""
from __future__ import annotations

import streamlit as st

from core.profiler import load_portfolios
from core.state import init_state
from components.styles import inject
from components.sidebar import render_sidebar

st.set_page_config(page_title="NEXUS | About", layout="wide", page_icon="assets/logo.svg")
inject()
init_state()

portfolios = load_portfolios()
profile, portfolio = render_sidebar(portfolios)

st.markdown('<div class="nx-header-title" style="font-size:1.9rem;">About NEXUS</div>', unsafe_allow_html=True)

st.markdown("""
### What this is

NEXUS turns a plain-English question like *"Should I increase my Reliance position?"*
into a parallel investigation run by five specialized agents (Technical, Fundamental,
Sentiment, Risk, Governance), grounds the Fundamental agent's reasoning in retrieved
document evidence, and produces one **personalized** recommendation — the same stock
can get a different call for a Conservative investor than for an Aggressive one,
because the Risk Agent checks portfolio *suitability*, not just market attractiveness.

It is an educational/research prototype built for a hackathon. It is **not financial
advice**, does not execute trades, and does not guarantee returns.
""")

st.markdown('<div class="nx-section-title">Exactly Where Each Number Comes From</div>', unsafe_allow_html=True)

st.markdown("""
Use the **live data toggle in the sidebar** to switch between the two modes below.
Every page tags each figure `LIVE` or `DEMO (cached)` so you never have to guess.
""")

st.markdown("""
<div class="nx-card">
<b style="color:var(--green);">Live mode</b><br>
<b>Prices, volume, 52-week high/low, and index levels</b> — fetched live from
<b>Yahoo Finance via the <code>yfinance</code> library</b> (NSE tickers, e.g.
<code>RELIANCE.NS</code>). Free, no API key.<br><br>
<b>Technical indicators</b> (20/50-day moving average, RSI-14, 30-day volatility,
10-day momentum) — <b>calculated by NEXUS from that real historical price series</b>,
not fetched pre-computed. See <code>core/live_data.py</code>.<br><br>
<b>Fundamentals</b> (revenue growth, EPS growth, margin, debt/equity, P/E) — pulled from
Yahoo's free <code>info</code> endpoint where available. Yahoo's free tier has gaps for
some Indian large-caps (a field can be blank), so any field it doesn't return falls
back to the cached figure for that field only, and the sector-average P/E reference
always comes from the curated dataset since Yahoo's free tier has no clean sector-average
field.<br><br>
<b>News headlines</b> — real recent headlines from <code>yfinance</code>'s news feed for
the ticker. NEXUS classifies each headline's tone (positive/negative/neutral) itself
with a small keyword lexicon, since Yahoo's free feed doesn't include sentiment scoring
or an institutional-flow signal — so "institutional flow" is marked
<code>UNAVAILABLE</code> in LIVE mode rather than invented.
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="nx-card">
<b style="color:var(--muted);">Demo mode (or automatic fallback)</b><br>
A hand-built local dataset (<code>data/market.json</code>, <code>data/news.json</code>,
<code>data/portfolio.json</code>) used when live mode is off, or automatically whenever
a live fetch fails — a blocked network, a Yahoo rate-limit, a missing field, or a
sandbox without outbound access to Yahoo's endpoints (this last case is common when
running inside a restricted CI/sandbox environment; it works normally on a laptop or on
Streamlit Community Cloud with normal outbound internet). The UI always labels this
<code>DEMO (cached)</code> — nothing is silently presented as live when it isn't.
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="nx-card">
<b>RAG evidence documents</b><br>
The Fundamental Agent's evidence panel retrieves from five curated Q1 FY27
earnings-summary text files in <code>data/filings/</code> — one per company, written to
mirror the structure of a real quarterly filing (revenue, margins, balance sheet, risk
factors) so the retrieval and citation mechanics are genuine. These are <b>not</b> scraped
from a live regulatory source: India's exchange filings (NSE/BSE) and MCA/SEBI documents
don't have a simple free bulk API within this hackathon's time budget, and the US SEC
EDGAR full-text system doesn't cover Indian-listed companies. This is stated plainly
rather than passed off as a live regulatory feed. Retrieval itself is real: TF-IDF
vector search (scikit-learn) with automatic keyword fallback — see the Evidence & RAG
page to query it directly.
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="nx-section-title">Architecture</div>', unsafe_allow_html=True)
st.markdown("""
```
USER QUESTION
     │
     ▼
ORCHESTRATOR (core/orchestrator.py)
     │
     ├──▶ Technical Agent    ─┐
     ├──▶ Fundamental Agent   │  run in parallel via
     ├──▶ Sentiment Agent     │  concurrent.futures.ThreadPoolExecutor
     └──▶ Risk Agent         ─┘
                │
                ▼
     Governance Agent (conflict / low-confidence / missing-evidence checks)
                │
                ▼
     Synthesis Agent (blends signals + user profile + portfolio)
                │
                ▼
     Personalized decision + WHY / WHY NOT + confidence
                │
                ▼
     SQLite (sessions, agent_runs, recommendations, portfolio_snapshots)
```

Each agent returns a fixed structured contract — `agent, status, signal, confidence,
score, factors, evidence, warnings, latency_ms` — never free-form prose as its primary
output (`agents/base.py`). The Fundamental Agent's evidence comes from `core/rag.py`.
The LLM (`core/llm.py`, optional local Ollama) is used **only** to phrase the natural
-language synthesis summary; if it's unavailable, a deterministic template with
identical substance is used instead — the app never requires an API key to run.

This follows the same agent-graph shape used in multi-agent financial-intelligence
write-ups (ingestion → extraction → risk scoring → reporting, run as a directed graph),
adapted here to a lighter dependency footprint (`ThreadPoolExecutor` instead of
LangGraph, TF-IDF instead of a downloaded embedding model) so the whole thing installs
and runs in minutes and deploys free on Streamlit Community Cloud.
""")

st.markdown('<div class="nx-section-title">Pages</div>', unsafe_allow_html=True)
p1, p2 = st.columns(2)
with p1:
    st.markdown("""
- **Home** — market overview, watchlist, navigation
- **Investigation** — the core agent pipeline for one stock + question
- **Portfolio** — holdings, sector exposure, what-if allocation simulator
    """)
with p2:
    st.markdown("""
- **Evidence & RAG** — inspect the filing corpus, run ad-hoc retrieval
- **Decision Trace** — full audit timeline + session history from SQLite
- **About** — this page
    """)

st.markdown(
    '<div class="nx-disclaimer">NEXUS is an educational / research prototype. It is not financial advice, '
    'not a registered investment advisor, does not execute trades, and does not guarantee returns. '
    'Always do your own research and consult a qualified financial advisor before investing.</div>',
    unsafe_allow_html=True,
)
