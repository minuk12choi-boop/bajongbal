from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass

from bajongbal.kis.client import KISClient, KISStatus
from bajongbal.storage.db import get_conn
from bajongbal.web.utils import format_number, format_to_10k, map_market

_LOCK = threading.Lock()
_LAST_CALL_TS = 0.0


@dataclass
class QuoteResult:
    code: str
    status: str
    market: str
    price: str
    change_rate: str
    volume: str
    trading_value_10k: str
    market_cap_10k: str
    failure_reason: str
    diagnostics: dict
    raw_data: dict | None = None


def normalize_code(code: str | None) -> str:
    c = (code or '').strip()
    if c.isdigit() and len(c) < 6:
        c = c.zfill(6)
    return c


def code_valid(code: str | None) -> bool:
    return bool(re.fullmatch(r'\d{6}', normalize_code(code)))


def _throttle_wait() -> float:
    global _LAST_CALL_TS
    interval = float(os.getenv('KIS_REQUEST_INTERVAL_SECONDS', '0.25') or '0.25')
    with _LOCK:
        now = time.monotonic()
        wait = max(0.0, interval - (now - _LAST_CALL_TS))
        if wait > 0:
            time.sleep(wait)
        _LAST_CALL_TS = time.monotonic()
    return wait


def _fallback_market(code: str) -> str:
    try:
        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(MAX(s.market), MAX(w.market), MAX(CASE
                    WHEN stm.theme_name LIKE '%ETF%' THEN 'ETF'
                    WHEN stm.theme_name LIKE '%ETN%' THEN 'ETN'
                    ELSE NULL
                END)) AS market
                FROM (SELECT ? AS code) x
                LEFT JOIN stocks s ON s.code = x.code
                LEFT JOIN watchlist_items w ON w.code = x.code AND COALESCE(w.is_active,1)=1
                LEFT JOIN stock_theme_map stm ON stm.code = x.code
                """,
                (code,),
            ).fetchone()
        guessed = (row['market'] if row else None) or ''
        mapped = map_market(guessed)
        return mapped if mapped != 'UNKNOWN' else 'UNKNOWN'
    except Exception:
        return 'UNKNOWN'


def _classify_failure(status: str, diagnostics: dict) -> tuple[str, str]:
    s = getattr(status, 'value', str(status))
    if s == KISStatus.AUTH_FAILED.value:
        return 'AUTH_FAILED', '인증/토큰 실패'
    msg_cd = str(diagnostics.get('msg_cd') or '').lower()
    msg1 = str(diagnostics.get('msg1') or '').lower()
    joined = f'{msg_cd} {msg1}'
    if any(k in joined for k in ['rate', 'limit', 'exceed', '초당', '호출', '과다']):
        return 'RATE_LIMITED', 'KIS 호출 제한 가능성'
    if s == KISStatus.PARSE_FAILED.value:
        return 'PARSE_FAILED', 'KIS 응답 파싱 실패'
    return 'API_FAILED', 'KIS 호출 실패 또는 응답 누락'


def fetch_quote_for_code(kis: KISClient, code: str, context: str = 'default') -> QuoteResult:
    ncode = normalize_code(code)
    if not ncode:
        return QuoteResult(ncode, 'CODE_MISSING', 'UNKNOWN', '조회 실패', '조회 실패', '조회 실패', '계산 불가', '계산 불가', '종목코드가 없습니다.', {'quote_context': context}, raw_data=None)
    if not code_valid(ncode):
        return QuoteResult(ncode, 'INVALID_CODE', 'UNKNOWN', '조회 실패', '조회 실패', '조회 실패', '계산 불가', '계산 불가', '유효하지 않은 종목코드(6자리 숫자 아님)', {'quote_context': context}, raw_data=None)

    waited = _throttle_wait()
    r = kis.get_current_price(ncode)
    diagnostics = {'quote_context': context, 'throttle_wait_seconds': round(waited, 3), **(getattr(r, 'diagnostics', None) or {})}

    if getattr(r.status, 'value', r.status) != KISStatus.OK.value:
        status, reason = _classify_failure(r.status, diagnostics)
        return QuoteResult(ncode, status, 'UNKNOWN', '조회 실패', '조회 실패', '조회 실패', '계산 불가', '계산 불가', reason, diagnostics, raw_data=None)

    d = r.data or {}
    if not d.get('price'):
        return QuoteResult(ncode, 'NO_DATA', 'UNKNOWN', '조회 실패', '조회 실패', '조회 실패', '계산 불가', '계산 불가', 'KIS 응답에 현재가 필드 없음', diagnostics, raw_data=d)

    market = map_market(d.get('market'))
    if market == 'UNKNOWN':
        market = _fallback_market(ncode)
        if market == 'UNKNOWN':
            return QuoteResult(
                ncode,
                'MARKET_MAPPING_FAILED',
                'UNKNOWN',
                format_number(d.get('price')),
                format_number(d.get('change_rate'), 2),
                format_number(d.get('volume')),
                format_to_10k(d.get('trading_value')),
                format_to_10k(d.get('market_cap')) if d.get('market_cap', -1) >= 0 else '계산 불가',
                '시장구분 원천 없음',
                diagnostics,
                raw_data=d,
            )

    return QuoteResult(
        ncode,
        'OK',
        market,
        format_number(d.get('price')),
        format_number(d.get('change_rate'), 2),
        format_number(d.get('volume')),
        format_to_10k(d.get('trading_value')),
        format_to_10k(d.get('market_cap')) if d.get('market_cap', -1) >= 0 else '계산 불가',
        '-',
        diagnostics,
        raw_data=d,
    )


def diagnose_quote(kis: KISClient, code: str) -> dict:
    contexts = ['theme_stocks', 'watchlist', 'scan']
    context_results = {}
    statuses = []
    for ctx in contexts:
        q = fetch_quote_for_code(kis, code, context=ctx)
        statuses.append(q.status)
        context_results[ctx] = {
            'quote_status': q.status,
            'normalized_code': q.code,
            'market': q.market,
            'failure_reason': q.failure_reason,
            'parser_used': 'KISClient.get_current_price',
        }

    q = fetch_quote_for_code(kis, code, context='diagnose')
    return {
        'input_code': code,
        'normalized_code': q.code,
        'code_valid': code_valid(code),
        'market': q.market,
        'quote_status': q.status,
        'failure_reason': q.failure_reason,
        'response_keys': q.diagnostics.get('response_keys', []),
        'parser_used': 'KISClient.get_current_price',
        'used_cache': False,
        'contexts_checked': contexts,
        'context_results': context_results,
        'mismatch': len(set(statuses)) > 1,
    }
