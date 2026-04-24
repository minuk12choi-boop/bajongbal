from __future__ import annotations

import json
from collections import defaultdict

from bajongbal.dart.client import DartClient
from bajongbal.dart.filings import tag_filings
from bajongbal.kis.client import KISClient, KISStatus
from bajongbal.market.theme_strength import calculate_theme_strength
from bajongbal.quote_service import fetch_quote_for_code, normalize_code
from bajongbal.storage.db import get_conn, list_theme_stocks, now_iso
from bajongbal.strategy.boxes import detect_box
from bajongbal.strategy.intraday import analyze_intraday
from bajongbal.strategy.levels import detect_levels
from bajongbal.strategy.pattern_333 import detect_333_pattern, score_333_pattern, summarize_333_pattern
from bajongbal.strategy.risk import risk_penalty
from bajongbal.strategy.scoring import compute_score, grade
from bajongbal.strategy.signal_types import LONG_BOX_TRIGGER
from bajongbal.strategy.trade_plan import build_trade_plan


def _load_watchlist(path: str) -> list[dict]:
    import csv
    rows = []
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def _theme_symbols(theme_id: str | None = None, theme_name: str | None = None) -> list[dict]:
    rows = list_theme_stocks(theme_id=theme_id, theme_name=theme_name)
    return [{'code': r['code'], 'name': r['name'] or r['code'], 'market': 'UNKNOWN'} for r in rows]


def _watchlist_group(group_id: int) -> tuple[str | None, list[dict]]:
    with get_conn() as conn:
        g = conn.execute('SELECT id,name FROM watchlist_groups WHERE id=? AND COALESCE(is_active,1)=1', (group_id,)).fetchone()
        if not g:
            return None, []
        rows = conn.execute('SELECT code,COALESCE(name,code) name,COALESCE(market,\'UNKNOWN\') market FROM watchlist_items WHERE group_id=? AND COALESCE(is_active,1)=1 ORDER BY id', (group_id,)).fetchall()
    return g['name'], [dict(r) for r in rows]


def _theme_names() -> dict[str, list[str]]:
    with get_conn() as conn:
        rows = conn.execute('SELECT code,theme_name FROM stock_theme_map').fetchall()
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
    watchlist_group_id: int | None = None,
    theme_id: str | None = None,
    theme_name: str | None = None,
    scope_mode: str | None = None,
    filter_code: str | None = None,
    filter_name: str | None = None,
) -> dict:
    warnings: list[str] = []
    errors: list[str] = []
    scope_mode = scope_mode or {'관심종목': 'watchlist_group', '테마 전체': 'all_theme_stocks'}.get(target_mode, 'watchlist_group')
    if target_mode == '테마 전체' and (theme_id or theme_name):
        scope_mode = 'selected_theme'
    scope_label = {'watchlist_group': '관심그룹에서 조회', 'all_theme_stocks': '전체 테마 종목 조회', 'selected_theme': '선택 테마 종목 조회'}.get(scope_mode, scope_mode)

    diagnostics = {
        'scope_mode': scope_mode,
        'scope_label': scope_label,
        'target_mode': target_mode,
        'selected_watchlist_group_id': watchlist_group_id,
        'selected_watchlist_group_name': None,
        'watchlist_group_count': 0,
        'watchlist_item_count': 0,
        'theme_cache_stock_count': 0,
        'selected_theme_id': theme_id,
        'selected_theme_name': theme_name,
        'selected_theme_stock_count': 0,
        'requested_max_symbols': max_symbols,
        'scan_target_count_before_limit': 0,
        'scan_target_count': 0,
        'kis_current_price_success_count': 0,
        'kis_current_price_fail_count': 0,
        'daily_chart_success_count': 0,
        'daily_chart_fail_count': 0,
        'weekly_chart_success_count': 0,
        'monthly_chart_success_count': 0,
        'minute_chart_success_count': 0,
        'score_calculated_count': 0,
        'score_below_threshold_count': 0,
        'final_signal_count': 0,
        'errors': [],
        'warnings': [],
        'invalid_code_count': 0,
        'filter_code': filter_code,
        'filter_name': filter_name,
        'filtered_target_count': 0,
        'display_limit': max_symbols,
    }

    with get_conn() as conn:
        diagnostics['watchlist_group_count'] = conn.execute('SELECT COUNT(*) FROM watchlist_groups WHERE COALESCE(is_active,1)=1').fetchone()[0]
        diagnostics['theme_cache_stock_count'] = conn.execute('SELECT COUNT(DISTINCT code) FROM stock_theme_map').fetchone()[0]

    if scope_mode == 'watchlist_group':
        if watchlist_group_id:
            if diagnostics['watchlist_group_count'] == 0:
                warnings.append('관심종목 그룹이 없습니다. 먼저 그룹을 생성하세요.')
                return {'signals': [], 'theme_strengths': [], 'warnings': warnings, 'errors': [], 'scan_target_count': 0, 'scan_success_count': 0, 'scan_fail_count': 0, 'is_demo': demo_mode, 'diagnostics': {**diagnostics, 'warnings': warnings[:10]}}
            group_name, all_targets = _watchlist_group(int(watchlist_group_id))
            diagnostics['selected_watchlist_group_name'] = group_name
            diagnostics['watchlist_item_count'] = len(all_targets)
            if not all_targets:
                warnings.append('선택한 관심그룹에 종목이 없습니다.')
                return {'signals': [], 'theme_strengths': [], 'warnings': warnings, 'errors': [], 'scan_target_count': 0, 'scan_success_count': 0, 'scan_fail_count': 0, 'is_demo': demo_mode, 'diagnostics': {**diagnostics, 'warnings': warnings[:10]}}
        elif diagnostics['watchlist_group_count'] > 0:
            with get_conn() as conn:
                row = conn.execute('SELECT id FROM watchlist_groups WHERE COALESCE(is_active,1)=1 ORDER BY id LIMIT 1').fetchone()
            group_name, all_targets = _watchlist_group(int(row['id'])) if row else (None, [])
            diagnostics['selected_watchlist_group_name'] = group_name
            diagnostics['watchlist_item_count'] = len(all_targets)
        else:
            all_targets = _load_watchlist(watchlist_path)
    elif scope_mode == 'all_theme_stocks':
        all_targets = _theme_symbols()
        diagnostics['selected_theme_stock_count'] = len(all_targets)
        if not all_targets:
            warnings.append('테마 캐시가 없습니다. 테마 캐시가 없어 테마 전체 스캔을 수행하지 않았습니다.')
            return {'signals': [], 'theme_strengths': [], 'warnings': warnings, 'errors': [], 'scan_target_count': 0, 'scan_success_count': 0, 'scan_fail_count': 0, 'is_demo': demo_mode, 'diagnostics': {**diagnostics, 'warnings': warnings[:10]}}
    elif scope_mode == 'selected_theme':
        if not theme_id and not theme_name:
            warnings.append('특정 테마 조회를 선택했지만 테마가 선택되지 않았습니다.')
            return {'signals': [], 'theme_strengths': [], 'warnings': warnings, 'errors': [], 'scan_target_count': 0, 'scan_success_count': 0, 'scan_fail_count': 0, 'is_demo': demo_mode, 'diagnostics': {**diagnostics, 'warnings': warnings[:10]}}
        all_targets = _theme_symbols(theme_id=theme_id)
        if not all_targets and theme_name:
            all_targets = _theme_symbols(theme_name=theme_name)
        diagnostics['selected_theme_stock_count'] = len(all_targets)
        if not all_targets:
            warnings.append('선택한 테마의 구성 종목을 찾을 수 없습니다.')
            return {'signals': [], 'theme_strengths': [], 'warnings': warnings, 'errors': [], 'scan_target_count': 0, 'scan_success_count': 0, 'scan_fail_count': 0, 'is_demo': demo_mode, 'diagnostics': {**diagnostics, 'warnings': warnings[:10]}}
    else:
        all_targets = _load_watchlist(watchlist_path)

    if filter_code:
        all_targets = [x for x in all_targets if filter_code in str(x.get('code',''))]
    if filter_name:
        all_targets = [x for x in all_targets if filter_name.lower() in str(x.get('name','')).lower()]
    diagnostics['filtered_target_count'] = len(all_targets)
    diagnostics['scan_target_count_before_limit'] = len(all_targets)
    watchlist = all_targets
    diagnostics['scan_target_count'] = len(watchlist)

    health = kis.health_detail()
    if health.status != KISStatus.OK and not demo_mode:
        errors.append(health.message)
        warnings.append('KIS 연결 실패로 실시간 시세 조회 불가')
        diagnostics['kis_current_price_fail_count'] = len(watchlist)
        diagnostics['errors'] = errors[:10]
        diagnostics['warnings'] = warnings[:10]
        return {'signals': [], 'theme_strengths': [], 'warnings': warnings, 'errors': errors, 'scan_target_count': len(watchlist), 'scan_success_count': 0, 'scan_fail_count': len(watchlist), 'is_demo': False, 'diagnostics': diagnostics}

    theme_map = _theme_names()
    signals, theme_rows = [], []
    success = 0

    for w in watchlist:
        code, name = normalize_code(str(w.get('code'))), w['name']
        if not __import__('re').fullmatch(r'\d{6}', str(code)):
            diagnostics['invalid_code_count'] += 1
            errors.append(f'{code}: INVALID_CODE')
            diagnostics['kis_current_price_fail_count'] += 1
            continue
        if demo_mode:
            cur = {'code': code, 'price': 10000.0, 'change_rate': 0.5, 'volume': 100000, 'trading_value': 1000000000}
            daily = [{'date': f'2026-01-{i:02d}', 'open': 9900 + i, 'high': 10100 + i, 'low': 9800 + i, 'close': 10000 + i, 'volume': 10000 + i, 'trading_value': 100000000 + i, 'timeframe': 'D'} for i in range(1, 121)]
            minutes = [{'dt': f'09:{i:02d}', 'open': 10000 + i, 'high': 10005 + i, 'low': 9995 + i, 'close': 10001 + i, 'volume': 100 + i, 'trading_value': 100000 + i} for i in range(1, 61)]
        else:
            quote = fetch_quote_for_code(kis, code, context='scan')
            diagnostics['kis_current_price_success_count'] += int(quote.status == KISStatus.OK)
            diagnostics['kis_current_price_fail_count'] += int(quote.status != KISStatus.OK)
            daily_r = kis.get_period_ohlcv(code, 'D', 120)
            diagnostics['daily_chart_success_count'] += int(daily_r.status == KISStatus.OK)
            diagnostics['daily_chart_fail_count'] += int(daily_r.status != KISStatus.OK)
            weekly_r = kis.get_period_ohlcv(code, 'W', 60)
            diagnostics['weekly_chart_success_count'] += int(weekly_r.status == KISStatus.OK)
            monthly_r = kis.get_period_ohlcv(code, 'M', 36)
            diagnostics['monthly_chart_success_count'] += int(monthly_r.status == KISStatus.OK)
            minutes_r = kis.get_intraday_minutes(code, 5, 60)
            diagnostics['minute_chart_success_count'] += int(minutes_r.status == KISStatus.OK)
            if quote.status != KISStatus.OK or daily_r.status != KISStatus.OK or minutes_r.status != KISStatus.OK:
                reason = quote.status if quote.status != KISStatus.OK else ('API_FAILED' if any(x.status == KISStatus.API_FAILED for x in (daily_r, minutes_r)) else 'PARSE_FAILED')
                summary = quote.diagnostics or daily_r.diagnostics or minutes_r.diagnostics or {}
                errors.append(f'{code}: {reason} / {summary}')
                continue
            cur, daily, minutes = quote.raw_data, daily_r.data, minutes_r.data

        levels = detect_levels(daily, cur['price'])
        box = detect_box(daily)
        intra = analyze_intraday(minutes, 5)
        p333 = detect_333_pattern(daily[-25:])
        score333 = score_333_pattern(p333)
        dart_delta = 0.0
        dart_status = '공시없음'
        if use_dart and not demo_mode:
            try:
                filings = tag_filings(dart.get_recent_filings(code, 10))
                dart_delta = sum(f['score_delta'] for f in filings)
                dart_status = '공시있음' if filings else '공시없음'
            except Exception:
                dart_status = 'API실패'
        parts = {
            'proximity': 18 if abs(cur['price'] - levels['trigger_price']) / max(levels['trigger_price'], 1) <= 0.03 else 8,
            'touch_pressure': min(15, intra['touch_count'] * 3), 'volume_heat': 14,
            'minute_pressure': 10 if intra['minute_trend'] == 'UP' else 4, 'pattern_333': score333,
            'upside_rr': 8, 'theme_sync': 6, 'dart_stability': min(5, max(0, 3 + dart_delta)),
            'risk_penalty': risk_penalty(cur['change_rate'], dart_delta),
        }
        s = compute_score(parts)
        diagnostics['score_calculated_count'] += 1
        if s < score_threshold:
            diagnostics['score_below_threshold_count'] += 1
            continue

        plan = build_trade_plan(name, cur['price'], levels, intra, 1.5, 1.2, dart_delta >= -1)
        signal = {
            'detected_at': now_iso(), 'code': code, 'name': name, 'theme_names': ', '.join(theme_map.get(code, ['미분류'])),
            'signal_type': LONG_BOX_TRIGGER, 'signal_grade': grade(s), 'score': s, 'current_price': cur['price'],
            'trigger_price': levels['trigger_price'], 'nearest_support': levels['nearest_support'], 'nearest_resistance': levels['nearest_resistance'],
            'next_resistance': levels['next_resistance'], 'stop_price': levels['stop_price'], 'volume_ratio': 1.5, 'trading_value_ratio': 1.2,
            'time_adjusted_volume_ratio': 1.1, 'touch_count': intra['touch_count'], 'minute_interval': intra['minute_interval'],
            'minute_window_start': intra['minute_window_start'], 'minute_window_end': intra['minute_window_end'], 'minute_lows_json': json.dumps(intra['minute_lows_json'], ensure_ascii=False),
            'minute_highs_json': json.dumps(intra['minute_highs_json'], ensure_ascii=False), 'minute_trend': intra['minute_trend'], 'vwap': intra['vwap'],
            'is_above_vwap': int(bool(intra['is_above_vwap'])), 'theme_score': 50.0, 'dart_score': dart_delta, 'risk_score': parts['risk_penalty'],
            'has_333_pattern': int(p333['detected']), 'pattern_333_timeframe': '일봉', 'pattern_333_grade': p333['grade'], 'score_333': score333,
            'reason_json': json.dumps(parts, ensure_ascii=False), 'trade_plan_json': json.dumps({**plan, 'pattern_333_summary': summarize_333_pattern(p333)}, ensure_ascii=False),
            'card_summary': plan['summary'], 'box_high': box['box_high'], 'box_low': box['box_low'], 'box_mid': box['box_mid'], 'box_width_pct': box['box_width_pct'], 'is_demo': int(demo_mode),
            'signal_subtype_main': '박스권 돌파',
            'signal_tags': '눌림목,거래량,분봉추세',
            'dart_status': dart_status,
        }
        signals.append(signal)
        theme_rows.append({'theme_name': signal['theme_names'].split(',')[0], 'name': name, 'score': s, 'change_rate': cur['change_rate'], 'trading_value': cur['trading_value'], 'trading_value_ratio_20': 1.2})
        success += 1

    if demo_mode:
        warnings.append('데모 데이터 모드로 실행되었습니다.')
    if not signals:
        if diagnostics['kis_current_price_fail_count'] == len(watchlist) and len(watchlist) > 0:
            warnings.append(f'조회 대상 {len(watchlist)}개 중 {len(watchlist)}개가 KIS 호출 또는 파싱에 실패했습니다.')
        elif diagnostics['score_below_threshold_count'] > 0:
            warnings.append(f'점수 기준 {int(score_threshold)}점 이상을 만족한 종목이 없습니다.')
        else:
            warnings.append('조건을 만족한 후보가 없습니다.')

    if not demo_mode:
        with get_conn() as conn:
            for s in signals:
                keys = [k for k in s.keys() if k in {'detected_at','code','name','theme_names','signal_type','signal_grade','score','current_price','trigger_price','nearest_support','nearest_resistance','next_resistance','stop_price','volume_ratio','trading_value_ratio','time_adjusted_volume_ratio','touch_count','minute_interval','minute_window_start','minute_window_end','minute_lows_json','minute_highs_json','minute_trend','vwap','is_above_vwap','theme_score','dart_score','risk_score','has_333_pattern','pattern_333_timeframe','pattern_333_grade','score_333','reason_json','trade_plan_json','is_demo'}]
                conn.execute(f"INSERT INTO signals({','.join(keys)}) VALUES ({','.join(['?']*len(keys))})", [s[k] for k in keys])
            conn.commit()

    signals.sort(key=lambda x: float(x.get('score', 0)), reverse=True)
    displayed_signals = signals[:max_symbols]
    diagnostics['final_signal_count'] = len(displayed_signals)
    diagnostics['raw_signal_count'] = len(signals)
    diagnostics['errors'] = errors[:10]
    diagnostics['warnings'] = warnings[:10]
    return {'signals': displayed_signals, 'theme_strengths': calculate_theme_strength(theme_rows), 'warnings': warnings, 'errors': errors, 'scan_target_count': len(watchlist), 'scan_success_count': success, 'scan_fail_count': len(watchlist)-success, 'is_demo': demo_mode, 'diagnostics': diagnostics}
