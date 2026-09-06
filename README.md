# NEXUS — The Retail Investor's AI Research Desk

**Multi-Agent Financial Intelligence System for Retail Investors**

NEXUS turns a plain-English question — *"Should I increase my Reliance position?"* — into a
parallel investigation run by five specialized agents, grounds the answer in retrieved
evidence, adapts the conclusion to the investor's actual risk profile and portfolio, and
shows its work: every signal, every confidence score, every piece of evidence, and a full
timestamped decision trace.

> **Educational / research prototype.** Not financial advice. Not a registered investment
> advisor. Does not execute trades. Does not guarantee returns. See [Disclaimer](#disclaimer).

---

## Table of Contents

1. [What this actually does](#what-this-actually-does)
2. [Two ways to run it](#two-ways-to-run-it)
3. [Architecture](#architecture)
4. [The agents, in detail](#the-agents-in-detail)
5. [Personalization — why the same stock gets different answers](#personalization)
6. [RAG — evidence retrieval](#rag--evidence-retrieval)
7. [Where the data comes from](#where-the-data-comes-from)
8. [Repository layout](#repository-layout)
9. [Setup: Streamlit app](#setup-streamlit-app)
10. [Setup: FastAPI + React app](#setup-fastapi--react-app)
11. [API reference](#api-reference)
12. [Testing](#testing)
13. [Failure handling & resilience](#failure-handling--resilience)
14. [Deployment](#deployment)
15. [Limitations](#limitations)
16. [Roadmap](#roadmap)
17. [Disclaimer](#disclaimer)

---

## What this actually does

You pick an investor profile (Conservative / Moderate / Aggressive), pick a stock, and ask
a question. NEXUS then:

1. Runs **four agents in parallel** — Technical, Fundamental, Sentiment, Risk — each
   producing an independent, structured, evidence-backed signal.
2. Runs a **Governance agent** that checks whether those four agents actually agree with
   each other, flags missing evidence or low confidence, and never manufactures false
   consensus.
3. Runs a **Synthesis agent** that blends all of the above with the investor's profile and
   *current portfolio* — not just the stock in isolation — into one call: `ACCUMULATE`,
   `HOLD`, `WATCH`, `REDUCE`, or `AVOID`.
4. Shows a **WHY** panel (the factors supporting the call), a **WHY NOT** panel (the
   strongest arguments against it), a **decision trace** (a timestamped audit log of every
   step), and **performance metrics** (latency, evidence coverage, signal agreement).

The core proof point: **the exact same stock, the exact same market data, produces
different recommendations for different investors** — because the Risk agent evaluates
*portfolio suitability*, not just whether the stock looks good in a vacuum. A Conservative
investor already near their preferred position-size ceiling gets told to `WATCH`; an
Aggressive investor with room in their portfolio gets told to `ACCUMULATE` — same ticker,
same day, same price.

---

## Two ways to run it

This repository actually contains **two separate, independently runnable applications**
that share the same agent logic (`agents/`, `core/`) but present it differently:

| | **Streamlit app** (`app.py` + `pages/`) | **FastAPI + React app** (`api.py` + `nexus-frontend/`) |
|---|---|---|
| Stack | Pure Python, server-rendered | Python backend (FastAPI) + TypeScript frontend (React/Vite) |
| Look | Multi-page terminal-style dashboard, gold/dark editorial theme | Landing page + agent "war room" dashboard, built with Framer Motion + Recharts |
| Run with | `streamlit run app.py` | `./start.sh` (runs both servers) |
| Best for | Fastest way to see everything working, easiest to deploy free | A more customizable, componentized frontend if you want to keep building the UI |

Both talk to the **same** `agents/`, `core/rag.py`, `core/orchestrator.py`, and `data/`
files — fix a bug or tune a scoring formula in `agents/risk.py` and it's fixed in both
apps.

---

## Architecture

```
                              USER QUESTION
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │   ORCHESTRATOR             │
                    │   core/orchestrator.py     │
                    └───────────────┬────────────┘
                                    │  concurrent.futures.ThreadPoolExecutor
              ┌───────────┬─────────┼─────────┬───────────┐
              ▼           ▼         ▼         ▼           │
        ┌──────────┐┌──────────┐┌─────────┐┌─────────┐   │
        │TECHNICAL ││FUNDAMENTAL││SENTIMENT││ RISK    │   │
        │ agent    ││  agent    ││  agent  ││ agent   │   │
        └────┬─────┘└─────┬─────┘└────┬────┘└────┬────┘   │
             │             │ RAG       │          │        │
             │             ▼           │          │        │
             │      core/rag.py        │          │        │
             │      (TF-IDF retrieval  │          │        │
             │       over data/filings)│          │        │
             └─────────────┴───────────┴──────────┘        │
                                    │                       │
                                    ▼                       │
                    ┌───────────────────────────┐           │
                    │   GOVERNANCE AGENT         │◀──────────┘
                    │   conflict / confidence /  │
                    │   evidence checks          │
                    └───────────────┬────────────┘
                                    ▼
                    ┌───────────────────────────┐
                    │   SYNTHESIS AGENT          │◀── investor profile
                    │   blends signals +         │◀── current portfolio
                    │   personalizes the call     │
                    └───────────────┬────────────┘
                                    ▼
              Personalized decision + confidence + WHY / WHY NOT
                                    │
                                    ▼
                    SQLite: sessions, agent_runs,
                    recommendations, portfolio_snapshots
                    (core/database.py)
```

Every agent returns a fixed structured contract defined in `agents/base.py`:

```python
@dataclass
class AgentResult:
    agent: str            # "technical" | "fundamental" | "sentiment" | "risk" | "governance"
    status: str            # "ok" | "degraded" | "unavailable"
    signal: str              # e.g. "BULLISH", "CAUTION", "CONFLICT_DETECTED"
    confidence: float         # 0.0 – 1.0
    score: int                 # 0 – 100, human-readable strength/risk score
    factors: list[str]          # plain-language reasons, derived from the actual calculation
    evidence: list[Evidence]     # source, document, chunk, relevance — never fabricated
    warnings: list[str]           # things that reduced confidence
    latency_ms: float              # how long this agent took
```

No agent ever returns free-form prose as its primary output. This is what makes the WHY /
WHY NOT panels and the decision trace possible — they're built directly from these
structured fields, not generated after the fact.

---

## The agents, in detail

### 1. Technical Agent — `agents/technical.py`

Purely deterministic, calculated from price/volume data (no LLM involved). Starts at a
baseline score of 50 and adjusts:

| Signal checked | Effect |
|---|---|
| Price vs 20-day moving average | +10 above / −10 below |
| Price vs 50-day moving average | +8 above / −8 below |
| Volume vs 20-day average | +8 if >1.5×, −4 if <0.6× |
| RSI(14) | +10 if 50–70 (healthy), −6 if >75 (overbought), −10 if <30 (oversold) |
| 10-day momentum | +6 positive / −6 negative |

Score clamped to 0–100. **Signal**: `BULLISH` ≥65, `BEARISH` ≤40, else `NEUTRAL`.
Confidence = score / 100.

### 2. Fundamental Agent — `agents/fundamental.py`

Also deterministic for the numeric scoring, but grounds its factors in **retrieved
document evidence** via the RAG engine (see below). Adjusts a baseline-50 score on:

| Signal checked | Effect |
|---|---|
| Revenue growth YoY | +12 if ≥8%, +4 if ≥4%, −8 otherwise |
| EPS growth YoY | +10 if ≥10%, +3 if ≥4%, −6 otherwise |
| Debt/equity | +6 if <0.3, −6 if >0.8 |
| P/E vs sector average | −6 if >15% premium, +5 if >10% discount |

It then queries `core/rag.py` for the top 2 most relevant filing chunks for the ticker +
question, and attaches them as `Evidence` — the agent never says "according to the filing"
unless a chunk was actually retrieved.

### 3. Sentiment Agent — `agents/sentiment.py`

Reads the positive/negative/neutral news-headline counts and an institutional-flow signal:

- Net tone ratio `(positive − negative) / total` scaled into the score (±35 points)
- Institutional flow: `NET_BUYING` +12, `NET_SELLING` −12

**Signal**: `BULLISH` ≥62, `BEARISH` ≤42, else `NEUTRAL`.

### 4. Risk Agent — `agents/risk.py`

**This is the one that makes personalization real.** It evaluates the stock against *this
specific investor's* profile and *current portfolio holdings* — not the stock in the
abstract. Starts at a baseline risk score of 30:

| Signal checked | Effect |
|---|---|
| Proposed position size vs profile's preferred max | up to +40, scaled by how far over |
| Sector concentration already in portfolio | +15 if >20%, +7 if >12% |
| Stock volatility vs profile's tolerance (LOW/MEDIUM/HIGH thresholds: 12% / 18% / 30%) | +15 if exceeded |
| Short investment horizon (1–3 yrs) + elevated volatility | +8 |

**Signal**: `CAUTION` ≥65, `MONITOR` ≥45, else `ACCEPTABLE`. Note this is a *risk* score —
higher means riskier, which is the opposite direction from the other agents' "higher is more
bullish" scoring, by design.

### 5. Governance Agent — `agents/governance.py`

Reviews the other four agents' outputs for:
- **Directional conflict** (e.g. Technical & Fundamental bullish, Sentiment bearish)
- Risk flags `CAUTION` while the market-facing agents are bullish — this specifically
  demonstrates *"market attractiveness ≠ portfolio suitability"*
- Any agent that came back `unavailable`, low-confidence, or with no evidence attached

It **never forces artificial agreement** — its job is to lower confidence and flag review,
not to make the agents agree. Signal: `CONFLICT_DETECTED`, `REVIEW_RECOMMENDED`, or
`CONSISTENT`.

### 6. Synthesis Agent — `agents/synthesis.py` + `core/scoring.py`

The final decision layer. Steps:

1. **Blend market signals**: `market_score = 0.35·technical + 0.35·fundamental + 0.30·sentiment`
2. **Map to a base call**: `ACCUMULATE` ≥65, `HOLD` ≥52, `WATCH` ≥40, `REDUCE` ≥28, else `AVOID`
3. **Apply the Risk downgrade**: if Risk signal is `CAUTION`, downgrade 1–2 rungs on the
   ladder above (2 if risk score ≥80); if `MONITOR`, downgrade 0–1 rungs
4. **Apply the Governance cap**: if a conflict was detected, the call is capped at `HOLD`
   regardless of how bullish the raw signals were — the system won't claim high confidence
   when its own agents disagree
5. **Blend confidence**: weighted average across all five agents
   (0.25 technical + 0.25 fundamental + 0.20 sentiment + 0.15 risk + 0.15 governance)

The natural-language summary is generated by an optional local LLM (Ollama) if available —
see [`core/llm.py`](core/llm.py) — but falls back to a deterministic template with
*identical substance* if it isn't. The signal, confidence, and evidence are never touched
by the LLM; it only phrases the sentence.

---

## Personalization

This is the mandatory demo scenario, and it's real, not scripted. Example from an actual
run (`api.py` investigate endpoint, RELIANCE, proposed allocation 15%):

| Profile | Max preferred position | Risk Agent signal | Final decision | Confidence |
|---|---|---|---|---|
| Conservative | 5% | `CAUTION` | **WATCH** | 80% |
| Moderate | 10% | `CAUTION` | **HOLD** | 78% |
| Aggressive | 20% | `MONITOR` | **ACCUMULATE** | 81% |

Same ticker. Same price. Same news. Same day. Three different calls, because the Risk
Agent is comparing the proposed 15% position against each profile's actual tolerance and
actual current holdings (`data/portfolio.json`).

---

## RAG — evidence retrieval

`core/rag.py` chunks five curated Q1 FY27 earnings-summary documents
(`data/filings/*.txt`, one per company) and retrieves the most relevant chunks for a given
ticker + question.

- **Primary mode — `VECTOR`**: TF-IDF vectorization + cosine similarity (scikit-learn).
  This is a genuine vector-space retrieval method. It was chosen over a downloaded
  sentence-transformer + FAISS index specifically so the app has **no large model
  download**, keeping cold-start reliable on free hosting.
- **Fallback mode — `KEYWORD_FALLBACK`**: plain keyword-overlap scoring, engaged
  automatically if scikit-learn is unavailable or vectorization fails for any reason.
- The active mode is always shown in the UI / API response (`rag_mode` field). Retrieval
  never crashes the app — it degrades to keyword search instead.

Every retrieved chunk carries `source`, `document`, `chunk`, and `relevance`, and is shown
in the Evidence panel. Query it directly on the Streamlit app's **Evidence & RAG** page.

---

## Where the data comes from

Toggle **"Use live market data"** in the Streamlit sidebar (on by default) to switch modes.
Every number is tagged `LIVE` or `DEMO (cached)` so you never have to guess.

| Data | Live mode | Demo / automatic fallback |
|---|---|---|
| Prices, volume, 52-week range, index levels | Real, via [`yfinance`](https://pypi.org/project/yfinance/) (Yahoo Finance), free, no API key, NSE tickers (`RELIANCE.NS`, etc.) | `data/market.json` |
| Technical indicators (DMA, RSI, volatility, momentum) | **Calculated by NEXUS** (`core/live_data.py`) from that real historical price series — never fetched pre-computed | Cached values in `data/market.json` |
| Fundamentals (growth, margins, debt/equity, P/E) | Real, from Yahoo's free `info` endpoint where available; the sector-average P/E always comes from the curated dataset since Yahoo's free tier has no clean field for it | `data/market.json` |
| News headlines | Real recent headlines from `yfinance`, tone-classified locally with a small keyword lexicon (Yahoo's free tier has no sentiment score) | `data/news.json` |
| Institutional flow | Marked `UNAVAILABLE` in live mode — no free source provides this, so it is never invented | `data/news.json` (labeled demo) |
| RAG filing documents | **Always** the curated `data/filings/*.txt` files — see note below | same |

**Why the filings aren't live:** India's exchange filings (NSE/BSE corporate announcements)
and MCA/SEBI documents don't have a simple free bulk API, and the US SEC EDGAR full-text
system doesn't cover Indian-listed companies. Rather than fake a live regulatory feed, the
filing documents are clearly labeled as curated text written to mirror the structure of a
real quarterly filing — real retrieval mechanics over honestly-labeled synthetic source
text.

**Live mode falls back to demo automatically** whenever a live fetch fails — blocked
network, Yahoo rate limit, missing field — and always relabels itself `DEMO (cached)`.
Nothing is ever silently presented as live when it isn't.

---

## Repository layout

```
NEXUS2/
├── app.py                       # Streamlit entry point (Home page)
├── pages/                       # Streamlit multipage app
│   ├── 1_Investigation.py         # the core 5-agent pipeline UI
│   ├── 2_Portfolio.py              # holdings, sector exposure, what-if simulator
│   ├── 3_Evidence_RAG.py            # browse filings, run retrieval queries directly
│   ├── 4_Decision_Trace.py           # audit trail + session history (SQLite)
│   └── 5_About.py                     # in-app explanation of data sources
│
├── api.py                       # FastAPI backend (serves the React frontend)
├── nexus-frontend/               # React + Vite + TypeScript frontend
│   ├── src/App.tsx                 # main dashboard
│   ├── src/StockChart.tsx           # price chart (yfinance → synthetic fallback)
│   └── vite.config.ts                # dev server + /api proxy to FastAPI on :8000
│
├── agents/                      # the five agents + base contract
│   ├── base.py                    # AgentResult / Evidence dataclasses
│   ├── technical.py
│   ├── fundamental.py
│   ├── sentiment.py
│   ├── risk.py
│   ├── governance.py
│   └── synthesis.py
│
├── core/
│   ├── orchestrator.py            # parallel execution + decision trace
│   ├── rag.py                       # TF-IDF retrieval engine + keyword fallback
│   ├── llm.py                        # optional local Ollama, deterministic fallback
│   ├── live_data.py                   # yfinance integration
│   ├── data_gateway.py                 # LIVE vs DEMO source-of-truth for every number
│   ├── profiler.py                      # loads investor profiles + portfolios
│   ├── scoring.py                        # the decision-matrix math for Synthesis
│   ├── simulator.py                       # what-if allocation counterfactual
│   ├── database.py                         # SQLite schema + writes
│   └── state.py                             # Streamlit session-state init
│
├── components/                  # shared Streamlit UI (styling, sidebar)
├── data/
│   ├── market.json                # 5 companies + NIFTY/SENSEX/BANKNIFTY, demo snapshot
│   ├── news.json                    # demo headlines + institutional flow per company
│   ├── portfolio.json                # 3 investor profiles + their demo holdings
│   └── filings/*.txt                  # curated RAG source documents, one per company
│
├── tests/test_nexus.py          # pytest suite (see Testing below)
├── utils/                        # metrics, formatting, degraded-mode helpers
├── database/                     # SQLite file lives here at runtime (gitignored)
├── start.sh                       # one-command dev startup for the FastAPI+React app
├── requirements.txt                # Python deps (Streamlit app)
└── .streamlit/config.toml           # Streamlit theme config
```

---

## Setup: Streamlit app

**Requirements:** Python 3.10+

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Opens automatically at `http://localhost:8501`. No `.env` file or API key is required —
live market data works out of the box via `yfinance`, and everything falls back to the
bundled demo dataset if it can't reach the network.

## Setup: FastAPI + React app

**Requirements:** Python 3.10+, Node.js 18+

**One command:**
```bash
chmod +x start.sh   # first time only
./start.sh
```
This creates a Python venv, installs backend dependencies, starts FastAPI on
`http://127.0.0.1:8000`, installs npm dependencies (first run only), and starts the Vite
dev server on `http://127.0.0.1:5173`. Open that URL in your browser. `Ctrl+C` stops both
servers.

**Manual (two terminals), if `start.sh` doesn't suit your platform:**

Terminal 1:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt fastapi "uvicorn[standard]"
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2:
```bash
cd nexus-frontend
npm install
npm run dev
```
Then open `http://127.0.0.1:5173`. The Vite dev server proxies `/api/*` requests to the
FastAPI backend on port 8000 (see `nexus-frontend/vite.config.ts`), so the frontend never
needs to know the backend's real address.

---

## API reference

Base URL in dev: `http://127.0.0.1:8000`

### `GET /`
Health check. Returns `{"system": "NEXUS", "status": "online", ...}`.

### `GET /api/health`
Simple liveness probe.

### `GET /api/market/{ticker}`
Returns current price/technical snapshot plus a `history` array for charting (real via
`yfinance` if reachable, otherwise a deterministic synthetic series anchored to the known
demo price — never depends on a flaky direct-from-browser Yahoo call).

Tickers accepted: `RELIANCE`, `TCS`, `INFY` (aliased to Infosys internally), `HDFCBANK`,
`ICICIBANK`, `SBIN`.

```json
{
  "success": true,
  "ticker": "RELIANCE",
  "company": "Reliance Industries",
  "current_price": 2945.6,
  "change_pct": 1.53,
  "data_source": "DEMO (simulated)",
  "demo": true,
  "history": [{"date": "2026-07-04", "close": 2806.96}, ...],
  "data": { "technical": {...}, "fundamental": {...} }
}
```

### `GET /api/news/{ticker}`
Returns headline counts, tone breakdown, and institutional flow for the ticker.

### `POST /api/investigate`
The core endpoint. Runs the full five-agent pipeline.

**Request body:**
```json
{
  "ticker": "RELIANCE",
  "question": "Should I increase my Reliance position?",
  "proposed_allocation_pct": 15,
  "profile": "moderate"
}
```
`profile` accepts `conservative`, `moderate`, or `aggressive` (defaults to `moderate` if
omitted or invalid).

**Response** (abridged):
```json
{
  "success": true,
  "ticker": "RELIANCE",
  "elapsed_ms": 1015.5,
  "agents": {
    "technical": { "signal": "BULLISH", "confidence": 0.92, "factors": [...], "summary": "...", "recommendation": "BULLISH" },
    "fundamental": { ... },
    "sentiment": { ... },
    "risk": { "signal": "CAUTION", "confidence": 0.89, "factors": [...] },
    "governance": { "signal": "CONSISTENT", ... }
  },
  "synthesis": {
    "final_signal": "WATCH",
    "decision": "WATCH",
    "confidence": 0.80,
    "summary": "...",
    "positive_factors": [...],
    "negative_factors": [...],
    "decision_trace": [...]
  },
  "profile": { "name": "Conservative", "max_preferred_position_pct": 5, ... }
}
```
Note: `synthesis.decision` and each agent's `summary` / `recommendation` are
display-friendly aliases added by `api.py` on top of the underlying structured fields
(`final_signal`, `factors`, `signal`) — both are present so you can consume whichever suits
your frontend.

---

## Testing

```bash
pip install pytest
pytest tests/ -q
```

`tests/test_nexus.py` covers, against the deterministic demo dataset (so it's reproducible
without live network access):

- Technical agent returns a properly structured result with evidence
- Risk agent correctly flags a concentration breach
- **Personalization actually differs** across the three investor profiles for the same
  stock (the core mandatory scenario)
- Conflict simulation reduces synthesis confidence
- Degraded-data mode reduces confidence and never crashes
- RAG retrieval returns evidence and reports its mode correctly
- All five agents execute and return valid statuses in a full investigation

---

## Failure handling & resilience

NEXUS is built to degrade, never crash:

- **RAG failure** → falls back from TF-IDF vector search to plain keyword matching
- **LLM unavailable** (no local Ollama running) → falls back to a deterministic summary
  template with identical substance; no API key is ever required to run the app
- **Live market data unreachable** → falls back to the cached demo dataset, and the
  Streamlit app has an explicit **"Simulate Data Failure"** control that engages this same
  path on demand and visibly drops confidence
- **Signal conflict** → the Streamlit app's **"Simulate Signal Conflict"** control forces a
  disagreement scenario so you can see the Governance agent catch it and cap confidence,
  without waiting for real market data to happen to disagree
- **Individual agent failure** → `agents/base.py`'s `BaseAgent._timed()` wraps every agent
  call; an exception inside any agent is caught and turned into a `status: "unavailable"`
  result rather than propagating and taking down the whole investigation

---

## Deployment

**Streamlit app → Streamlit Community Cloud** (free): point it at this repo, set the main
file to `app.py`, dependencies from `requirements.txt`. No Docker, no separate backend.

**FastAPI + React app** needs two services:
- **Backend**: Render, Railway, or Fly.io — run `uvicorn api:app --host 0.0.0.0 --port $PORT`
- **Frontend**: Vercel or Netlify — build command `npm run build` in `nexus-frontend/`,
  output directory `nexus-frontend/dist`; set the frontend's API base URL to your deployed
  backend's URL (currently the dev proxy in `vite.config.ts` only works for local
  development)

---

## Limitations

- Five NSE-listed companies only (Reliance, TCS, Infosys, HDFC Bank, ICICI Bank, plus SBIN
  in the React app), for hackathon/demo scope.
- RAG corpus is curated earnings-summary text, not a live regulatory filings feed (see
  [RAG section](#rag--evidence-retrieval) for why).
- "Institutional flow" is marked `UNAVAILABLE` in live mode since no free source provides
  it — never fabricated.
- Yahoo's free tier has gaps for some fundamentals fields on Indian large-caps; missing
  fields fall back to the cached reference value for that field only.
- The FastAPI+React app's Vite dev proxy is dev-only; a production deployment needs the
  frontend's API base URL pointed at the deployed backend explicitly.

## Roadmap

- Multi-stock comparison view
- Alert rules / watchlist notifications
- A production API base URL config for the React app (currently dev-proxy only)
- Swap TF-IDF for a downloaded embedding model, now that the interface in `core/rag.py` is
  already model-agnostic

---

## Disclaimer

NEXUS is an educational / research prototype demonstrating explainable, multi-agent
decision-support architecture. It is **not financial advice**, is **not a registered
investment advisor**, does **not execute trades**, and does **not guarantee returns**.
Market, news, and filing data are either clearly-labeled demo data or real data fetched
from free public sources with no warranty of accuracy or timeliness. Always do your own
research and consult a qualified financial advisor before making investment decisions.