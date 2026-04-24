from __future__ import annotations


def grade(score: float) -> str:
    if score >= 90:
        return 'S'
    if score >= 80:
        return 'A'
    if score >= 70:
        return 'B'
    if score >= 60:
        return 'C'
    return 'X'


def compute_score(parts: dict) -> float:
    score = (
        min(18, parts.get('proximity', 0))
        + min(15, parts.get('touch_pressure', 0))
        + min(20, parts.get('volume_heat', 0))
        + min(12, parts.get('minute_pressure', 0))
        + min(10, parts.get('pattern_333', 0))
        + min(10, parts.get('upside_rr', 0))
        + min(10, parts.get('theme_sync', 0))
        + min(5, parts.get('dart_stability', 0))
        + parts.get('risk_penalty', 0)
    )
    return max(0.0, min(100.0, round(score, 2)))
