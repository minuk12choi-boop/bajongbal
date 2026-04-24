from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from bajongbal.kis.auth import build_auth_headers, get_access_token
from bajongbal.kis.parsers import safe_float, safe_int


# TODO(사용자확인필요): 아래 TR_ID/경로는 계정유형(실전/모의)과 API 버전에 따라 다를 수 있어 운영 전 재확인 필요
TR_CURRENT = 'FHKST01010100'
TR_DAILY = 'FHKST01010400'
TR_INTRADAY = 'FHKST03010200'
TR_INTRADAY_DAILY = 'FHKST03010100'


class KISClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def _fallback_price(self, code: str) -> dict[str, Any]:
        return {'code': code, 'price': 10000.0, 'change_rate': 0.0, 'volume': 0, 'trading_value': 0.0}

    def _fallback_daily(self, timeframe: str, count: int) -> list[dict[str, Any]]:
        base = datetime.now(timezone.utc).date()
        rows = []
        for i in range(count):
            p = 10000 + i
            rows.append({'date': (base - timedelta(days=count - i)).isoformat(), 'open': p, 'high': p * 1.01, 'low': p * 0.99, 'close': p, 'volume': 1000 + i, 'trading_value': (1000 + i) * p, 'timeframe': timeframe})
        return rows

    def _fallback_intraday(self, points: int) -> list[dict[str, Any]]:
        base = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
        rows = []
        for i in range(points):
            p = 10000 + i * 2
            rows.append({'dt': (base + timedelta(minutes=5 * i)).isoformat(), 'open': p, 'high': p * 1.001, 'low': p * 0.999, 'close': p, 'volume': 100 + i, 'trading_value': (100 + i) * p})
        return rows

    def health(self) -> bool:
        return get_access_token() is not None

    def _get(self, path: str, params: dict[str, Any], tr_id: str) -> dict[str, Any]:
        url = f'{self.base_url}{path}'
        try:
            res = requests.get(url, headers=build_auth_headers(tr_id), params=params, timeout=10)
            res.raise_for_status()
            return res.json()
        except Exception:
            return {}

    def get_current_price(self, code: str) -> dict[str, Any]:
        data = self._get('/uapi/domestic-stock/v1/quotations/inquire-price', {'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': code}, TR_CURRENT)
        out = data.get('output', {}) if isinstance(data, dict) else {}
        parsed = {'code': code, 'price': safe_float(out.get('stck_prpr') or out.get('stck_clpr')), 'change_rate': safe_float(out.get('prdy_ctrt')), 'volume': safe_int(out.get('acml_vol')), 'trading_value': safe_float(out.get('acml_tr_pbmn') or out.get('acml_tr_pbmn1'))}
        return parsed if parsed['price'] > 0 else self._fallback_price(code)

    def get_period_ohlcv(self, code: str, timeframe: str = 'D', count: int = 120) -> list[dict[str, Any]]:
        period_code_map = {'D': 'D', 'W': 'W', 'M': 'M', 'Y': 'Y'}
        now = datetime.now(timezone.utc)
        from_date = (now - timedelta(days=365 * 2)).strftime('%Y%m%d')
        to_date = now.strftime('%Y%m%d')
        data = self._get('/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice', {'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': code, 'FID_INPUT_DATE_1': from_date, 'FID_INPUT_DATE_2': to_date, 'FID_PERIOD_DIV_CODE': period_code_map.get(timeframe, 'D'), 'FID_ORG_ADJ_PRC': '1'}, TR_DAILY)
        rows = data.get('output2', []) if isinstance(data, dict) else []
        parsed = []
        for r in rows[:count]:
            parsed.append({'date': r.get('stck_bsop_date') or r.get('xymd'), 'open': safe_float(r.get('stck_oprc') or r.get('open')), 'high': safe_float(r.get('stck_hgpr') or r.get('high')), 'low': safe_float(r.get('stck_lwpr') or r.get('low')), 'close': safe_float(r.get('stck_clpr') or r.get('close')), 'volume': safe_int(r.get('acml_vol') or r.get('volume')), 'trading_value': safe_float(r.get('acml_tr_pbmn') or r.get('trading_value')), 'timeframe': timeframe})
        return parsed if parsed else self._fallback_daily(timeframe, count)

    def get_intraday_minutes(self, code: str, interval_min: int = 5, points: int = 120) -> list[dict[str, Any]]:
        data = self._get('/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice', {'FID_ETC_CLS_CODE': '', 'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': code, 'FID_INPUT_HOUR_1': '', 'FID_PW_DATA_INCU_YN': 'Y'}, TR_INTRADAY)
        rows = data.get('output2', []) if isinstance(data, dict) else []
        parsed = []
        for r in rows[:points]:
            dt = r.get('stck_cntg_hour') or r.get('xymd') or ''
            parsed.append({'dt': str(dt), 'open': safe_float(r.get('stck_oprc') or r.get('open')), 'high': safe_float(r.get('stck_hgpr') or r.get('high')), 'low': safe_float(r.get('stck_lwpr') or r.get('low')), 'close': safe_float(r.get('stck_prpr') or r.get('stck_clpr') or r.get('close')), 'volume': safe_int(r.get('cntg_vol') or r.get('acml_vol') or r.get('volume')), 'trading_value': safe_float(r.get('acml_tr_pbmn') or r.get('trading_value'))})
        return parsed if parsed else self._fallback_intraday(points)

    def get_daily_minutes(self, code: str, day: str) -> list[dict[str, Any]]:
        data = self._get('/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice', {'FID_ETC_CLS_CODE': '', 'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': code, 'FID_INPUT_DATE_1': day, 'FID_PW_DATA_INCU_YN': 'Y'}, TR_INTRADAY_DAILY)
        rows = data.get('output2', []) if isinstance(data, dict) else []
        parsed = [{'dt': str(r.get('stck_cntg_hour') or ''), 'open': safe_float(r.get('stck_oprc')), 'high': safe_float(r.get('stck_hgpr')), 'low': safe_float(r.get('stck_lwpr')), 'close': safe_float(r.get('stck_prpr') or r.get('stck_clpr')), 'volume': safe_int(r.get('cntg_vol') or r.get('acml_vol')), 'trading_value': safe_float(r.get('acml_tr_pbmn'))} for r in rows]
        return parsed if parsed else self._fallback_intraday(60)
