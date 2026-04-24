from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import requests

from bajongbal.config import settings
from bajongbal.kis.auth import build_auth_headers, get_access_token
from bajongbal.kis.parsers import safe_float, safe_int

TR_CURRENT = 'FHKST01010100'
TR_DAILY = 'FHKST01010400'
TR_INTRADAY = 'FHKST03010200'
TR_INTRADAY_DAILY = 'FHKST03010100'


class KISStatus(str, Enum):
    CONFIG_MISSING = 'CONFIG_MISSING'
    AUTH_FAILED = 'AUTH_FAILED'
    API_FAILED = 'API_FAILED'
    PARSE_FAILED = 'PARSE_FAILED'
    OK = 'OK'


STATUS_MESSAGE = {
    KISStatus.CONFIG_MISSING: 'KIS 환경변수가 누락되었습니다.',
    KISStatus.AUTH_FAILED: 'KIS 인증 토큰 발급에 실패했습니다.',
    KISStatus.API_FAILED: 'KIS API 호출에 실패했습니다.',
    KISStatus.PARSE_FAILED: 'KIS 응답 파싱에 실패했습니다.',
    KISStatus.OK: '정상',
}


@dataclass
class KISResult:
    status: KISStatus
    message: str
    data: Any = None
    diagnostics: dict[str, Any] | None = None


class KISClient:
    def __init__(self, base_url: str):
        self.base_url = (base_url or '').rstrip('/')

    def config_ok(self) -> bool:
        return bool(settings.has_kis_app_key and settings.has_kis_app_secret and self.base_url)

    def health_detail(self) -> KISResult:
        if not self.config_ok():
            return KISResult(KISStatus.CONFIG_MISSING, STATUS_MESSAGE[KISStatus.CONFIG_MISSING])
        token = get_access_token()
        if not token:
            return KISResult(KISStatus.AUTH_FAILED, STATUS_MESSAGE[KISStatus.AUTH_FAILED])
        return KISResult(KISStatus.OK, STATUS_MESSAGE[KISStatus.OK])

    def health(self) -> bool:
        return self.health_detail().status == KISStatus.OK

    def _pick_rows(self, data: dict | None) -> list[dict]:
        d = data or {}
        for k in ('output2', 'output1', 'output'):
            v = d.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
        return []

    def _pick_obj(self, data: dict | None) -> dict:
        d = data or {}
        for k in ('output', 'output1'):
            v = d.get(k)
            if isinstance(v, dict):
                return v
        return {}

    def _diag(self, payload: Any, missing: list[str] | None = None) -> dict[str, Any]:
        keys = list(payload.keys()) if isinstance(payload, dict) else []
        output = payload.get('output') if isinstance(payload, dict) else None
        return {
            'response_keys': keys[:20],
            'output_type': type(output).__name__,
            'output_length': len(output) if isinstance(output, list) else (len(output.keys()) if isinstance(output, dict) else 0),
            'missing_required_fields': missing or [],
        }

    def _get(self, path: str, params: dict[str, Any], tr_id: str) -> KISResult:
        health = self.health_detail()
        if health.status != KISStatus.OK:
            return KISResult(health.status, health.message)
        try:
            res = requests.get(f'{self.base_url}{path}', headers=build_auth_headers(tr_id), params=params, timeout=10)
            res.raise_for_status()
            return KISResult(KISStatus.OK, STATUS_MESSAGE[KISStatus.OK], res.json())
        except Exception:
            return KISResult(KISStatus.API_FAILED, STATUS_MESSAGE[KISStatus.API_FAILED])

    def get_current_price(self, code: str) -> KISResult:
        res = self._get('/uapi/domestic-stock/v1/quotations/inquire-price', {'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': code}, TR_CURRENT)
        if res.status != KISStatus.OK:
            return res
        out = self._pick_obj(res.data)
        price = safe_float(out.get('stck_prpr') or out.get('stck_clpr') or out.get('cur_prc') or out.get('close'))
        if price <= 0:
            return KISResult(KISStatus.PARSE_FAILED, STATUS_MESSAGE[KISStatus.PARSE_FAILED], diagnostics=self._diag(res.data, ['price']))
        return KISResult(
            KISStatus.OK,
            STATUS_MESSAGE[KISStatus.OK],
            {
                'code': code,
                'price': price,
                'change_rate': safe_float(out.get('prdy_ctrt') or out.get('flu_rt') or out.get('change_rate')),
                'volume': safe_int(out.get('acml_vol') or out.get('cntg_vol') or out.get('volume')),
                'trading_value': safe_float(out.get('acml_tr_pbmn') or out.get('acml_tr_pbmn1') or out.get('trading_value')),
                'market_cap': safe_float(out.get('hts_avls') or out.get('market_cap'), default=-1),
                'market': (out.get('mksc_shrn_iscd') or out.get('market') or '').strip() or 'UNKNOWN',
            },
        )

    def get_period_ohlcv(self, code: str, timeframe: str = 'D', count: int = 120) -> KISResult:
        period_code_map = {'D': 'D', 'W': 'W', 'M': 'M', 'Y': 'Y'}
        res = self._get('/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice', {'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': code, 'FID_INPUT_DATE_1': '20200101', 'FID_INPUT_DATE_2': '20991231', 'FID_PERIOD_DIV_CODE': period_code_map.get(timeframe, 'D'), 'FID_ORG_ADJ_PRC': '1'}, TR_DAILY)
        if res.status != KISStatus.OK:
            return res
        rows = self._pick_rows(res.data)
        parsed = []
        for r in rows[:count]:
            parsed.append({'date': r.get('stck_bsop_date') or r.get('xymd') or r.get('date'), 'open': safe_float(r.get('stck_oprc') or r.get('open')), 'high': safe_float(r.get('stck_hgpr') or r.get('high')), 'low': safe_float(r.get('stck_lwpr') or r.get('low')), 'close': safe_float(r.get('stck_clpr') or r.get('close')), 'volume': safe_int(r.get('acml_vol') or r.get('volume')), 'trading_value': safe_float(r.get('acml_tr_pbmn') or r.get('trading_value')), 'timeframe': timeframe})
        if not parsed:
            return KISResult(KISStatus.PARSE_FAILED, STATUS_MESSAGE[KISStatus.PARSE_FAILED], diagnostics=self._diag(res.data, ['ohlcv_rows']))
        return KISResult(KISStatus.OK, STATUS_MESSAGE[KISStatus.OK], parsed)

    def get_intraday_minutes(self, code: str, interval_min: int = 5, points: int = 120) -> KISResult:
        res = self._get('/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice', {'FID_ETC_CLS_CODE': '', 'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': code, 'FID_INPUT_HOUR_1': '', 'FID_PW_DATA_INCU_YN': 'Y'}, TR_INTRADAY)
        if res.status != KISStatus.OK:
            return res
        rows = self._pick_rows(res.data)
        parsed = []
        for r in rows[:points]:
            parsed.append({'dt': str(r.get('stck_cntg_hour') or r.get('xymd') or r.get('dt') or ''), 'open': safe_float(r.get('stck_oprc') or r.get('open')), 'high': safe_float(r.get('stck_hgpr') or r.get('high')), 'low': safe_float(r.get('stck_lwpr') or r.get('low')), 'close': safe_float(r.get('stck_prpr') or r.get('stck_clpr') or r.get('close')), 'volume': safe_int(r.get('cntg_vol') or r.get('acml_vol') or r.get('volume')), 'trading_value': safe_float(r.get('acml_tr_pbmn') or r.get('trading_value'))})
        if not parsed:
            return KISResult(KISStatus.PARSE_FAILED, STATUS_MESSAGE[KISStatus.PARSE_FAILED], diagnostics=self._diag(res.data, ['intraday_rows']))
        return KISResult(KISStatus.OK, STATUS_MESSAGE[KISStatus.OK], parsed)

    def get_daily_minutes(self, code: str, day: str) -> KISResult:
        res = self._get('/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice', {'FID_ETC_CLS_CODE': '', 'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': code, 'FID_INPUT_DATE_1': day, 'FID_PW_DATA_INCU_YN': 'Y'}, TR_INTRADAY_DAILY)
        if res.status != KISStatus.OK:
            return res
        rows = self._pick_rows(res.data)
        parsed = [{'dt': str(r.get('stck_cntg_hour') or r.get('dt') or ''), 'open': safe_float(r.get('stck_oprc') or r.get('open')), 'high': safe_float(r.get('stck_hgpr') or r.get('high')), 'low': safe_float(r.get('stck_lwpr') or r.get('low')), 'close': safe_float(r.get('stck_prpr') or r.get('stck_clpr') or r.get('close')), 'volume': safe_int(r.get('cntg_vol') or r.get('acml_vol') or r.get('volume')), 'trading_value': safe_float(r.get('acml_tr_pbmn') or r.get('trading_value'))} for r in rows]
        if not parsed:
            return KISResult(KISStatus.PARSE_FAILED, STATUS_MESSAGE[KISStatus.PARSE_FAILED], diagnostics=self._diag(res.data, ['daily_minutes_rows']))
        return KISResult(KISStatus.OK, STATUS_MESSAGE[KISStatus.OK], parsed)
