from __future__ import annotations

from datetime import date

from bajongbal.config import settings


class DartClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.dart_api_key

    def health(self) -> bool:
        return bool(self.api_key)

    def get_recent_filings(self, code: str, limit: int = 20) -> list[dict]:
        # TODO: DART 엔드포인트 스펙 확정 시 실제 호출 구현
        return [
            {'code': code, 'rcept_dt': date.today().isoformat(), 'report_nm': '단일판매ㆍ공급계약 체결'},
            {'code': code, 'rcept_dt': date.today().isoformat(), 'report_nm': '감사의견 관련 안내'},
        ][:limit]

    def get_company_overview(self, corp_code: str) -> dict:
        return {'corp_code': corp_code, 'status': 'mock'}
