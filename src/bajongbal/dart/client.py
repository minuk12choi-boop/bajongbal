from __future__ import annotations

from datetime import date
from typing import Any

import requests

from bajongbal.config import settings
from bajongbal.dart.corp_codes import download_corp_codes, stock_to_corp_code


class DartClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.dart_api_key

    def health(self) -> bool:
        return bool(self.api_key)

    def ensure_corp_codes(self) -> dict[str, str]:
        return download_corp_codes(self.api_key)

    def get_corp_code(self, stock_code: str) -> str | None:
        corp_code = stock_to_corp_code(stock_code)
        if corp_code:
            return corp_code
        self.ensure_corp_codes()
        return stock_to_corp_code(stock_code)

    def get_recent_filings(self, stock_code: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self.api_key:
            return []
        corp_code = self.get_corp_code(stock_code)
        if not corp_code:
            return []
        today = date.today().strftime('%Y%m%d')
        begin = date.today().replace(month=1, day=1).strftime('%Y%m%d')
        try:
            res = requests.get(
                'https://opendart.fss.or.kr/api/list.json',
                params={
                    'crtfc_key': self.api_key,
                    'corp_code': corp_code,
                    'bgn_de': begin,
                    'end_de': today,
                    'page_count': min(100, max(1, limit)),
                },
                timeout=12,
            )
            res.raise_for_status()
            data = res.json()
            items = data.get('list', []) if isinstance(data, dict) else []
            return [
                {
                    'code': stock_code,
                    'corp_code': corp_code,
                    'rcept_dt': x.get('rcept_dt'),
                    'report_nm': x.get('report_nm', ''),
                }
                for x in items[:limit]
            ]
        except Exception:
            return []

    def get_company_overview(self, corp_code: str) -> dict[str, Any]:
        if not self.api_key:
            return {}
        try:
            res = requests.get(
                'https://opendart.fss.or.kr/api/company.json',
                params={'crtfc_key': self.api_key, 'corp_code': corp_code},
                timeout=12,
            )
            res.raise_for_status()
            data = res.json()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
