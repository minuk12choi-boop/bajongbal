from __future__ import annotations


def analyze_intraday(minutes: list[dict], interval: int = 5) -> dict:
    lows = [m['low'] for m in minutes[-12:]]
    highs = [m['high'] for m in minutes[-12:]]
    touch_price = max(highs) * 0.995 if highs else 0
    touch_count = sum(1 for h in highs if h >= touch_price)
    trend = 'UP' if len(lows) >= 3 and lows[-3] <= lows[-2] <= lows[-1] else 'MIXED'
    vol = sum(m['volume'] for m in minutes)
    vwap = sum(m['close'] * m['volume'] for m in minutes) / max(1, vol)
    last = minutes[-1]['close'] if minutes else 0
    ma20_5 = sum(m['close'] for m in minutes[-20:]) / max(1, len(minutes[-20:]))
    return {
        'touch_count': touch_count,
        'minute_interval': interval,
        'minute_window_start': minutes[-12]['dt'] if len(minutes) >= 12 else None,
        'minute_window_end': minutes[-1]['dt'] if minutes else None,
        'minute_lows_json': lows,
        'minute_highs_json': highs,
        'minute_trend': trend,
        'vwap': vwap,
        'is_above_vwap': last >= vwap,
        'is_above_5min_ma20': last >= ma20_5,
    }
