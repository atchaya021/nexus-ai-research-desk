"""
LLM abstraction layer.

Primary: a local Ollama model, if reachable.
Fallback: deterministic, template-based natural-language generation.

The rest of the application NEVER depends on the LLM for numbers, signals, or
citations — only for turning already-computed structured facts into readable
prose. If Ollama is unreachable, the demo must still work identically in
substance, just with template phrasing instead of generated phrasing.
"""
from __future__ import annotations

import os
import json
import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")


def _ollama_available() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=1.0)
        return resp.status_code == 200
    except Exception:
        return False


class LLMEngine:
    def __init__(self):
        self.available = _ollama_available()
        self.mode = "OLLAMA" if self.available else "DETERMINISTIC"

    def generate(self, prompt: str, max_tokens: int = 200) -> str | None:
        """Returns generated text, or None if the LLM is unavailable.
        Callers MUST handle None by using their own deterministic template —
        this method never raises."""
        if not self.available:
            return None
        try:
            resp = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=8.0,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data.get("response", "").strip() or None
        except Exception:
            return None


_engine: LLMEngine | None = None


def get_engine() -> LLMEngine:
    global _engine
    if _engine is None:
        _engine = LLMEngine()
    return _engine
