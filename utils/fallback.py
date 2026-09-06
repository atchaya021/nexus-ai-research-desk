"""
Degraded-data simulation helpers.

When "Simulate Data Failure" is triggered in the UI, the app does not fetch
different numbers — it marks the live source unavailable, falls back to the
last verified cached snapshot (the same local dataset, explicitly relabeled),
and reduces confidence. Nothing is silently swapped without a visible label.
"""
from __future__ import annotations


def apply_degradation(confidence: float, degraded: bool) -> float:
    if not degraded:
        return confidence
    return round(max(0.05, confidence * 0.76), 2)


DEGRADED_BANNER = (
    "DATA SOURCE DEGRADED — Live market feed unavailable. "
    "Falling back to last verified cached market state. Confidence reduced."
)
