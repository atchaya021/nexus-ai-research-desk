"""
Local RAG over data/filings/*.txt

Primary mode: TF-IDF vector retrieval (scikit-learn) — a genuine vector-space
retrieval method that requires no model downloads, which keeps the app
reliable on free-tier deployment (Streamlit Community Cloud) and immune to
network/model-hub outages during a live demo.

Fallback mode: pure keyword substring scoring, used only if scikit-learn is
unavailable or vectorization fails for any reason. The app must never crash
because retrieval failed.

RAG_MODE is exposed so the UI can show which mode is active, per the
requirement that the system never silently pretends a fallback is the primary
path.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

FILINGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "filings")

DOC_LABELS = {
    "reliance.txt": "Reliance Industries Q1 FY27 Filing",
    "tcs.txt": "TCS Q1 FY27 Filing",
    "infosys.txt": "Infosys Q1 FY27 Filing",
    "hdfcbank.txt": "HDFC Bank Q1 FY27 Filing",
    "icicibank.txt": "ICICI Bank Q1 FY27 Filing",
}

TICKER_TO_FILE = {
    "RELIANCE": "reliance.txt",
    "TCS": "tcs.txt",
    "INFOSYS": "infosys.txt",
    "HDFCBANK": "hdfcbank.txt",
    "ICICIBANK": "icicibank.txt",
}


@dataclass
class Chunk:
    doc_file: str
    doc_label: str
    text: str


def _load_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    if not os.path.isdir(FILINGS_DIR):
        return chunks
    for fname in sorted(os.listdir(FILINGS_DIR)):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(FILINGS_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        # Chunk by blank-line-separated paragraphs, dropping tiny fragments.
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 40]
        label = DOC_LABELS.get(fname, fname)
        for p in paras:
            chunks.append(Chunk(doc_file=fname, doc_label=label, text=p))
    return chunks


class RAGEngine:
    """Retrieval engine with automatic TF-IDF -> keyword fallback."""

    def __init__(self):
        self.chunks = _load_chunks()
        self.mode = "UNAVAILABLE"
        self._vectorizer = None
        self._matrix = None
        self._init_vector_index()

    def _init_vector_index(self):
        if not self.chunks:
            self.mode = "UNAVAILABLE"
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self._vectorizer = TfidfVectorizer(stop_words="english")
            self._matrix = self._vectorizer.fit_transform([c.text for c in self.chunks])
            self.mode = "VECTOR"
        except Exception:
            self._vectorizer = None
            self._matrix = None
            self.mode = "KEYWORD_FALLBACK"

    def retrieve(self, ticker: str, query: str, top_k: int = 3) -> list[dict]:
        """Return top_k evidence dicts for the given ticker + query."""
        target_file = TICKER_TO_FILE.get(ticker)
        pool = [c for c in self.chunks if c.doc_file == target_file] if target_file else self.chunks
        if not pool:
            return []

        if self.mode == "VECTOR" and self._vectorizer is not None:
            try:
                return self._retrieve_vector(pool, query, top_k)
            except Exception:
                self.mode = "KEYWORD_FALLBACK"
                return self._retrieve_keyword(pool, query, top_k)
        return self._retrieve_keyword(pool, query, top_k)

    def _retrieve_vector(self, pool: list[Chunk], query: str, top_k: int) -> list[dict]:
        from sklearn.metrics.pairwise import cosine_similarity

        pool_texts = [c.text for c in pool]
        local_vectorizer = self._vectorizer
        pool_matrix = local_vectorizer.transform(pool_texts)
        q_vec = local_vectorizer.transform([query])
        sims = cosine_similarity(q_vec, pool_matrix)[0]
        ranked = sorted(zip(pool, sims), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for chunk, score in ranked:
            if score <= 0:
                continue
            results.append(
                {
                    "source": chunk.doc_label,
                    "document": chunk.doc_file,
                    "chunk": chunk.text,
                    "relevance": round(float(score), 2),
                    "kind": "document",
                }
            )
        return results

    def _retrieve_keyword(self, pool: list[Chunk], query: str, top_k: int) -> list[dict]:
        terms = [t.lower() for t in re.findall(r"[a-zA-Z]{3,}", query)]
        scored = []
        for chunk in pool:
            text_lower = chunk.text.lower()
            hits = sum(text_lower.count(term) for term in terms)
            if hits > 0:
                scored.append((chunk, hits))
        scored.sort(key=lambda x: x[1], reverse=True)
        max_hits = scored[0][1] if scored else 1
        results = []
        for chunk, hits in scored[:top_k]:
            results.append(
                {
                    "source": chunk.doc_label,
                    "document": chunk.doc_file,
                    "chunk": chunk.text,
                    "relevance": round(min(hits / max_hits, 1.0), 2),
                    "kind": "document",
                }
            )
        return results


_engine: RAGEngine | None = None


def get_engine() -> RAGEngine:
    global _engine
    if _engine is None:
        _engine = RAGEngine()
    return _engine
