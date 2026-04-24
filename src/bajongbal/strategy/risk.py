from __future__ import annotations


def risk_penalty(change_rate: float, dart_delta: float) -> float:
    penalty = 0.0
    if change_rate > 20:
        penalty -= 10
    if dart_delta < -3:
        penalty -= 15
    return max(-30.0, penalty)
