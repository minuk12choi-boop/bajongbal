from __future__ import annotations


def detect_levels(daily: list[dict], current_price: float) -> dict:
    highs = sorted({d['high'] for d in daily})
    lows = sorted({d['low'] for d in daily})
    support = max([x for x in lows if x <= current_price], default=current_price * 0.95)
    res = min([x for x in highs if x >= current_price], default=current_price * 1.05)
    next_res = min([x for x in highs if x > res], default=res * 1.03)
    return {
        'nearest_support': support,
        'nearest_resistance': res,
        'next_resistance': next_res,
        'trigger_price': res,
        'stop_price': support * 0.995,
        'level_source': 'daily_swing',
    }
