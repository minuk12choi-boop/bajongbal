from __future__ import annotations


def classify_candle_color(c: dict) -> str:
    o, cl = c['open'], c['close']
    if cl > o:
        return 'U'
    if cl < o:
        return 'D'
    return 'DOJI'


def compress_candle_groups(candles: list[dict]) -> list[dict]:
    groups = []
    for c in candles:
        color = classify_candle_color(c)
        if color == 'DOJI' and groups:
            color = groups[-1]['color']
        if not groups or groups[-1]['color'] != color:
            groups.append({'color': color, 'candles': [c]})
        else:
            groups[-1]['candles'].append(c)
    return groups


def detect_333_pattern(candles: list[dict]) -> dict:
    groups = compress_candle_groups(candles)
    seq = '-'.join(g['color'] for g in groups)
    target = ['U', 'D', 'U', 'D', 'U', 'D', 'U']
    if len(groups) >= 7 and [g['color'] for g in groups[-7:]] == target:
        picked = groups[-7:]
        high = max(max(c['high'] for c in g['candles']) for g in picked)
        low = min(min(c['low'] for c in g['candles']) for g in picked)
        correction = (high - low) / high * 100 if high else 0
        last_up = picked[-1]['candles'][-1]
        grade = 'NORMAL_333'
        if correction >= 15 and last_up['close'] > last_up['open'] * 1.01:
            grade = 'STRONG_333'
        elif correction < 5:
            grade = 'WEAK_333'
        return {'detected': True, 'sequence': 'U-D-U-D-U-D-U', 'grade': grade, 'correction_pct': correction, 'last_up_date': last_up.get('date')}
    return {'detected': False, 'sequence': seq, 'grade': 'NO_333', 'correction_pct': 0, 'last_up_date': None}


def score_333_pattern(result: dict) -> float:
    return {'STRONG_333': 10.0, 'NORMAL_333': 7.0, 'WEAK_333': 3.0}.get(result.get('grade'), 0.0)


def summarize_333_pattern(result: dict, timeframe: str = '일봉') -> str:
    if not result.get('detected'):
        return f"{timeframe} 기준 333 패턴은 감지되지 않았습니다."
    return f"{timeframe} 기준 {result['grade']} 333 패턴이 감지되었습니다."


def build_333_trade_plan(result: dict, current_price: float, next_resistance: float) -> dict:
    score = score_333_pattern(result)
    return {'score_333': score, 'next_resistance': next_resistance, 'upside_room_pct': (next_resistance - current_price) / current_price * 100 if current_price else 0}
