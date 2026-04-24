from __future__ import annotations

import re
from dataclasses import dataclass

from bajongbal.kis.client import KISClient, KISStatus
from bajongbal.web.utils import format_number, format_to_10k, map_market


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


def normalize_code(code: str | None) -> str:
    c = (code or '').strip()
    if c.isdigit() and len(c) < 6:
        c = c.zfill(6)
    return c


def code_valid(code: str | None) -> bool:
    return bool(re.fullmatch(r'\d{6}', normalize_code(code)))


def fetch_quote_for_code(kis: KISClient, code: str, context: str = 'default') -> QuoteResult:
    ncode = normalize_code(code)
    if not ncode:
        return QuoteResult(ncode, 'CODE_MISSING', 'UNKNOWN', '조회 실패', '조회 실패', '조회 실패', '계산 불가', '계산 불가', '종목코드가 없습니다.', {'quote_context': context})
    if not code_valid(ncode):
        return QuoteResult(ncode, 'INVALID_CODE', 'UNKNOWN', '조회 실패', '조회 실패', '조회 실패', '계산 불가', '계산 불가', '유효하지 않은 종목코드(6자리 숫자 아님)', {'quote_context': context})
    r = kis.get_current_price(ncode)
    if r.status != KISStatus.OK:
        reason = 'PARSE_FAILED' if r.status == KISStatus.PARSE_FAILED else 'API_FAILED'
        return QuoteResult(ncode, reason, 'UNKNOWN', '조회 실패', '조회 실패', '조회 실패', '계산 불가', '계산 불가', 'KIS 호출 또는 파싱 실패', {'quote_context': context, **(r.diagnostics or {})})
    d = r.data
    return QuoteResult(
        ncode,
        'OK',
        map_market(d.get('market')),
        format_number(d.get('price')),
        format_number(d.get('change_rate'), 2),
        format_number(d.get('volume')),
        format_to_10k(d.get('trading_value')),
        format_to_10k(d.get('market_cap')) if d.get('market_cap', -1) >= 0 else '계산 불가',
        '-',
        {'quote_context': context},
    )


def diagnose_quote(kis: KISClient, code: str) -> dict:
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
        'contexts_checked': ['watchlist', 'theme_stocks', 'scan'],
    }
