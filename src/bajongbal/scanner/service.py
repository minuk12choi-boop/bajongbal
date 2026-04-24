from __future__ import annotations

import json
from collections import defaultdict

from bajongbal.dart.client import DartClient
from bajongbal.dart.filings import tag_filings
from bajongbal.kis.client import KISClient, KISStatus
from bajongbal.market.theme_strength import calculate_theme_strength
from bajongbal.strategy.boxes import detect_box
from bajongbal.strategy.intraday import analyze_intraday
from bajongbal.strategy.levels import detect_levels
from bajongbal.strategy.pattern_333 import detect_333_pattern, score_333_pattern, summarize_333_pattern
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


def _load_theme_symbols(limit: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute('SELECT DISTINCT code, name FROM stock_theme_map WHERE code IS NOT NULL AND code != "" LIMIT ?', (limit,)).fetchall()
    return [{'code': r['code'], 'name': r['name'] or r['code'], 'market': 'UNKNOWN'} for r in rows]


def _load_theme_names() -> dict[str, list[str]]:
    with get_conn() as conn:
        rows = conn.execute('SELECT code, theme_name FROM stock_theme_map').fetchall()
    out: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        out[r['code']].append(r['theme_name'])
    return out


def run_scan(
    kis: KISClient,
    dart: DartClient,
    watchlist_path: str,
    score_threshold: float = 60,
    use_dart: bool = True,
    max_symbols: int = 50,
    target_mode: str = '관심종목',
    demo_mode: bool = False,
) -> dict:
    warnings: list[str] = []
    errors: list[str] = []

    if target_mode == '테마 전체':
        watchlist = _load_theme_symbols(max_symbols)
        if not watchlist:
            return {
                'signals': [],
                'theme_strengths': [],
                'warnings': ['테마 캐시가 없습니다. 먼저 [테마 갱신]을 실행하세요.'],
                'errors': [],
                'scan_target_count': 0,
                'scan_success_count': 0,
                'scan_fail_count': 0,
                'is_demo': demo_mode,
            }
    else:
        watchlist = _load_watchlist(watchlist_path)[:max_symbols]

    if not watchlist:
        return {
            'signals': [],
            'theme_strengths': [],
            'warnings': ['스캔 대상 종목이 없습니다.'],
            'errors': [],
            'scan_target_count': 0,
            'scan_success_count': 0,
            'scan_fail_count': 0,
            'is_demo': demo_mode,
        }

    health = kis.health_detail()
    if health.status != KISStatus.OK and not demo_mode:
        return {
            'signals': [],
            'theme_strengths': [],
            'warnings': ['KIS 연결 실패로 실시간 시세 조회 불가'],
            'errors': [health.message],
            'scan_target_count': len(watchlist),
            'scan_success_count': 0,
            'scan_fail_count': len(watchlist),
            'is_demo': False,
        }

    theme_names_map = _load_theme_names()
    signals = []
    theme_rows = []
    success_count = 0
    fail_count = 0

    for w in watchlist:
        code, name = w['code'], w['name']

        if demo_mode:
            cur = {'code': code, 'price': 10000.0, 'change_rate': 0.5, 'volume': 100000, 'trading_value': 1000000000}
            daily = [{'date': f'2026-01-{i:02d}', 'open': 9900 + i, 'high': 10100 + i, 'low': 9800 + i, 'close': 10000 + i, 'volume': 10000 + i, 'trading_value': 100000000 + i, 'timeframe': 'D'} for i in range(1, 121)]
            minutes = [{'dt': f'09:{i:02d}', 'open': 10000 + i, 'high': 10005 + i, 'low': 9995 + i, 'close': 10001 + i, 'volume': 100 + i, 'trading_value': 100000 + i} for i in range(1, 61)]
        else:
            cur_r = kis.get_current_price(code)
            daily_r = kis.get_period_ohlcv(code, 'D', 120)
            minutes_r = kis.get_intraday_minutes(code, 5, 60)
            if cur_r.status != KISStatus.OK or daily_r.status != KISStatus.OK or minutes_r.status != KISStatus.OK:
                fail_count += 1
                errors.append(f'{code}: {cur_r.message if cur_r.status != KISStatus.OK else daily_r.message if daily_r.status != KISStatus.OK else minutes_r.message}')
                continue
            cur, daily, minutes = cur_r.data, daily_r.data, minutes_r.data

        try:
            levels = detect_levels(daily, cur['price'])
            box = detect_box(daily)
            intra = analyze_intraday(minutes, 5)
            candles = daily[-25:]
            p333 = detect_333_pattern(candles)
            score333 = score_333_pattern(p333)

            dart_delta = 0.0
            if use_dart and not demo_mode:
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
                'theme_names': ', '.join(theme_names_map.get(code, ['미분류'])),
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
                'is_demo': int(demo_mode),
            }
            signals.append(signal)
            theme_rows.append({'theme_name': signal['theme_names'].split(',')[0], 'name': name, 'score': s, 'change_rate': cur['change_rate'], 'trading_value': cur['trading_value'], 'trading_value_ratio_20': 1.2})
            success_count += 1
        except Exception as exc:
            fail_count += 1
            errors.append(f'{code}: {exc}')

    if demo_mode:
        warnings.append('데모 데이터 모드로 실행되었습니다.')

    if not signals:
        warnings.append('조건을 만족한 후보가 없습니다.')

    if not demo_mode:
        with get_conn() as conn:
            for s in signals:
                keys = [k for k in s.keys() if k in {
                    'detected_at', 'code', 'name', 'theme_names', 'signal_type', 'signal_grade', 'score', 'current_price', 'trigger_price', 'nearest_support', 'nearest_resistance', 'next_resistance', 'stop_price', 'volume_ratio', 'trading_value_ratio', 'time_adjusted_volume_ratio', 'touch_count', 'minute_interval', 'minute_window_start', 'minute_window_end', 'minute_lows_json', 'minute_highs_json', 'minute_trend', 'vwap', 'is_above_vwap', 'theme_score', 'dart_score', 'risk_score', 'has_333_pattern', 'pattern_333_timeframe', 'pattern_333_grade', 'score_333', 'reason_json', 'trade_plan_json', 'is_demo'}]
                vals = [s[k] for k in keys]
                conn.execute(f"INSERT INTO signals({','.join(keys)}) VALUES ({','.join(['?']*len(keys))})", vals)
            conn.commit()

    return {
        'signals': signals,
        'theme_strengths': calculate_theme_strength(theme_rows),
        'warnings': warnings,
        'errors': errors,
        'scan_target_count': len(watchlist),
        'scan_success_count': success_count,
        'scan_fail_count': len(watchlist) - success_count,
        'is_demo': demo_mode,
    }
