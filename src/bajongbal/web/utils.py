from __future__ import annotations


def format_number(value: float | int | str | None, digits: int = 0) -> str:
    if value is None or value == '':
        return '-'
    try:
        n = float(str(value).replace(',', ''))
    except Exception:
        return str(value)
    if digits <= 0:
        return f'{int(round(n)):,}'
    return f'{n:,.{digits}f}'


def format_to_10k(value: float | int | str | None, digits: int = 2) -> str:
    if value is None or value == '':
        return '계산 불가'
    try:
        n = float(str(value).replace(',', '')) / 10000.0
    except Exception:
        return '계산 불가'
    return f'{n:,.{digits}f}'


def map_market(raw: str | None) -> str:
    v = (raw or '').upper().strip()
    if v in {'J', 'KOSPI', '1'}:
        return 'KOSPI'
    if v in {'Q', 'KOSDAQ', '2'}:
        return 'KOSDAQ'
    if v in {'KONEX', '3'}:
        return 'KONEX'
    if 'ETF' in v:
        return 'ETF'
    if 'ETN' in v:
        return 'ETN'
    if v in {'UNKNOWN', ''}:
        return 'UNKNOWN'
    return '기타'
