from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import requests

from bajongbal.config import settings
from bajongbal.kis.auth import build_auth_headers, get_access_token
from bajongbal.kis.parsers import safe_float, safe_int


# TODO(사용자확인필요): TR_ID/엔드포인트는 실전/모의 계정별로 상이할 수 있으므로 운영 전 최종 확인 필요
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
        out = (res.data or {}).get('output', {})
        price = safe_float(out.get('stck_prpr') or out.get('stck_clpr'))
        if price <= 0:
            return KISResult(KISStatus.PARSE_FAILED, STATUS_MESSAGE[KISStatus.PARSE_FAILED])
        return KISResult(KISStatus.OK, STATUS_MESSAGE[KISStatus.OK], {'code': code, 'price': price, 'change_rate': safe_float(out.get('prdy_ctrt')), 'volume': safe_int(out.get('acml_vol')), 'trading_value': safe_float(out.get('acml_tr_pbmn') or out.get('acml_tr_pbmn1'))})

    def get_period_ohlcv(self, code: str, timeframe: str = 'D', count: int = 120) -> KISResult:
        period_code_map = {'D': 'D', 'W': 'W', 'M': 'M', 'Y': 'Y'}
        res = self._get('/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice', {'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': code, 'FID_INPUT_DATE_1': '20200101', 'FID_INPUT_DATE_2': '20991231', 'FID_PERIOD_DIV_CODE': period_code_map.get(timeframe, 'D'), 'FID_ORG_ADJ_PRC': '1'}, TR_DAILY)
        if res.status != KISStatus.OK:
            return res
        rows = (res.data or {}).get('output2', [])
        parsed = []
        for r in rows[:count]:
            parsed.append({'date': r.get('stck_bsop_date') or r.get('xymd'), 'open': safe_float(r.get('stck_oprc') or r.get('open')), 'high': safe_float(r.get('stck_hgpr') or r.get('high')), 'low': safe_float(r.get('stck_lwpr') or r.get('low')), 'close': safe_float(r.get('stck_clpr') or r.get('close')), 'volume': safe_int(r.get('acml_vol') or r.get('volume')), 'trading_value': safe_float(r.get('acml_tr_pbmn') or r.get('trading_value')), 'timeframe': timeframe})
        if not parsed:
            return KISResult(KISStatus.PARSE_FAILED, STATUS_MESSAGE[KISStatus.PARSE_FAILED])
        return KISResult(KISStatus.OK, STATUS_MESSAGE[KISStatus.OK], parsed)

    def get_intraday_minutes(self, code: str, interval_min: int = 5, points: int = 120) -> KISResult:
        res = self._get('/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice', {'FID_ETC_CLS_CODE': '', 'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': code, 'FID_INPUT_HOUR_1': '', 'FID_PW_DATA_INCU_YN': 'Y'}, TR_INTRADAY)
        if res.status != KISStatus.OK:
            return res
        rows = (res.data or {}).get('output2', [])
        parsed = []
        for r in rows[:points]:
            parsed.append({'dt': str(r.get('stck_cntg_hour') or r.get('xymd') or ''), 'open': safe_float(r.get('stck_oprc') or r.get('open')), 'high': safe_float(r.get('stck_hgpr') or r.get('high')), 'low': safe_float(r.get('stck_lwpr') or r.get('low')), 'close': safe_float(r.get('stck_prpr') or r.get('stck_clpr') or r.get('close')), 'volume': safe_int(r.get('cntg_vol') or r.get('acml_vol') or r.get('volume')), 'trading_value': safe_float(r.get('acml_tr_pbmn') or r.get('trading_value'))})
        if not parsed:
            return KISResult(KISStatus.PARSE_FAILED, STATUS_MESSAGE[KISStatus.PARSE_FAILED])
        return KISResult(KISStatus.OK, STATUS_MESSAGE[KISStatus.OK], parsed)

    def get_daily_minutes(self, code: str, day: str) -> KISResult:
        res = self._get('/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice', {'FID_ETC_CLS_CODE': '', 'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': code, 'FID_INPUT_DATE_1': day, 'FID_PW_DATA_INCU_YN': 'Y'}, TR_INTRADAY_DAILY)
        if res.status != KISStatus.OK:
            return res
        rows = (res.data or {}).get('output2', [])
        parsed = [{'dt': str(r.get('stck_cntg_hour') or ''), 'open': safe_float(r.get('stck_oprc')), 'high': safe_float(r.get('stck_hgpr')), 'low': safe_float(r.get('stck_lwpr')), 'close': safe_float(r.get('stck_prpr') or r.get('stck_clpr')), 'volume': safe_int(r.get('cntg_vol') or r.get('acml_vol')), 'trading_value': safe_float(r.get('acml_tr_pbmn'))} for r in rows]
        if not parsed:
            return KISResult(KISStatus.PARSE_FAILED, STATUS_MESSAGE[KISStatus.PARSE_FAILED])
        return KISResult(KISStatus.OK, STATUS_MESSAGE[KISStatus.OK], parsed)
