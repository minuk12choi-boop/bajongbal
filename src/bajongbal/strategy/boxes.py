from __future__ import annotations


def detect_box(daily: list[dict]) -> dict:
    recent = daily[-20:] if len(daily) >= 20 else daily
    box_high = max(d['high'] for d in recent)
    box_low = min(d['low'] for d in recent)
    box_mid = (box_high + box_low) / 2
    box_width_pct = (box_high - box_low) / box_mid * 100 if box_mid else 0
    return {
        'box_high': box_high,
        'box_low': box_low,
        'box_mid': box_mid,
        'box_width_pct': box_width_pct,
    }
