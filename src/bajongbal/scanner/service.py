from __future__ import annotations

import json

from bajongbal.dart.client import DartClient
from bajongbal.dart.filings import tag_filings
from bajongbal.kis.client import KISClient
from bajongbal.market.theme_strength import calculate_theme_strength
from bajongbal.strategy.boxes import detect_box
from bajongbal.strategy.intraday import analyze_intraday
from bajongbal.strategy.levels import detect_levels
from bajongbal.strategy.pattern_333 import build_333_trade_plan, detect_333_pattern, score_333_pattern, summarize_333_pattern
from bajongbal.strategy.risk import risk_penalty
from bajongbal.strategy.scoring import compute_score, grade
from bajongbal.strategy.signal_types import LONG_BOX_TRIGGER
from bajongbal.strategy.trade_plan import build_trade_plan
from bajongbal.storage.db import get_conn, now_iso


def _load_watchlist(path: str) -> list[dict]:
    import csv
    rows = []
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def run_scan(kis: KISClient, dart: DartClient, watchlist_path: str, score_threshold: float = 60, use_dart: bool = True, max_symbols: int = 50) -> dict:
    watchlist = _load_watchlist(watchlist_path)[:max_symbols]
    signals = []
    theme_rows = []
    for w in watchlist:
        code, name = w['code'], w['name']
        cur = kis.get_current_price(code)
        daily = kis.get_period_ohlcv(code, 'D', 120)
        minutes = kis.get_intraday_minutes(code, 5, 60)

        levels = detect_levels(daily, cur['price'])
        box = detect_box(daily)
        intra = analyze_intraday(minutes, 5)

        candles = daily[-25:]
        p333 = detect_333_pattern(candles)
        score333 = score_333_pattern(p333)

        dart_delta = 0.0
        if use_dart:
            filings = tag_filings(dart.get_recent_filings(code, 10))
            dart_delta = sum(f['score_delta'] for f in filings)
        parts = {
            'proximity': 18 if abs(cur['price'] - levels['trigger_price']) / max(levels['trigger_price'], 1) <= 0.03 else 8,
            'touch_pressure': min(15, intra['touch_count'] * 3),
            'volume_heat': 14,
            'minute_pressure': 10 if intra['minute_trend'] == 'UP' else 4,
            'pattern_333': score333,
            'upside_rr': 8,
            'theme_sync': 6,
            'dart_stability': min(5, max(0, 3 + dart_delta)),
            'risk_penalty': risk_penalty(cur['change_rate'], dart_delta),
        }
        s = compute_score(parts)
        if s < score_threshold:
            continue

        plan = build_trade_plan(name, cur['price'], levels, intra, 1.5, 1.2, dart_delta >= -1)
        g = grade(s)
        signal = {
            'detected_at': now_iso(),
            'code': code,
            'name': name,
            'theme_names': '미분류',
            'signal_type': LONG_BOX_TRIGGER,
            'signal_grade': g,
            'score': s,
            'current_price': cur['price'],
            'trigger_price': levels['trigger_price'],
            'nearest_support': levels['nearest_support'],
            'nearest_resistance': levels['nearest_resistance'],
            'next_resistance': levels['next_resistance'],
            'stop_price': levels['stop_price'],
            'volume_ratio': 1.5,
            'trading_value_ratio': 1.2,
            'time_adjusted_volume_ratio': 1.1,
            'touch_count': intra['touch_count'],
            'minute_interval': intra['minute_interval'],
            'minute_window_start': intra['minute_window_start'],
            'minute_window_end': intra['minute_window_end'],
            'minute_lows_json': json.dumps(intra['minute_lows_json'], ensure_ascii=False),
            'minute_highs_json': json.dumps(intra['minute_highs_json'], ensure_ascii=False),
            'minute_trend': intra['minute_trend'],
            'vwap': intra['vwap'],
            'is_above_vwap': int(bool(intra['is_above_vwap'])),
            'theme_score': 50.0,
            'dart_score': dart_delta,
            'risk_score': parts['risk_penalty'],
            'has_333_pattern': int(p333['detected']),
            'pattern_333_timeframe': '일봉',
            'pattern_333_grade': p333['grade'],
            'score_333': score333,
            'reason_json': json.dumps(parts, ensure_ascii=False),
            'trade_plan_json': json.dumps({**plan, 'pattern_333_summary': summarize_333_pattern(p333)}, ensure_ascii=False),
            'card_summary': plan['summary'],
            'box_high': box['box_high'],
            'box_low': box['box_low'],
            'box_mid': box['box_mid'],
            'box_width_pct': box['box_width_pct'],
        }
        signals.append(signal)
        theme_rows.append({'theme_name': '미분류', 'name': name, 'score': s, 'change_rate': cur['change_rate'], 'trading_value': cur['trading_value'], 'trading_value_ratio_20': 1.2})

    with get_conn() as conn:
        for s in signals:
            keys = [k for k in s.keys() if k in {
                'detected_at','code','name','theme_names','signal_type','signal_grade','score','current_price','trigger_price','nearest_support','nearest_resistance','next_resistance','stop_price','volume_ratio','trading_value_ratio','time_adjusted_volume_ratio','touch_count','minute_interval','minute_window_start','minute_window_end','minute_lows_json','minute_highs_json','minute_trend','vwap','is_above_vwap','theme_score','dart_score','risk_score','has_333_pattern','pattern_333_timeframe','pattern_333_grade','score_333','reason_json','trade_plan_json'}]
            vals = [s[k] for k in keys]
            conn.execute(f"INSERT INTO signals({','.join(keys)}) VALUES ({','.join(['?']*len(keys))})", vals)
        conn.commit()

    return {'signals': signals, 'theme_strengths': calculate_theme_strength(theme_rows)}
