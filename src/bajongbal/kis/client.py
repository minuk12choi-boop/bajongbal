from __future__ import annotations

from datetime import datetime, timedelta
import random

import requests

from bajongbal.kis.auth import get_access_token
from bajongbal.kis.parsers import safe_float


class KISClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def _headers(self) -> dict[str, str]:
        token = get_access_token()
        h = {'content-type': 'application/json'}
        if token:
            h['authorization'] = f'Bearer {token}'
        return h

    def health(self) -> bool:
        return get_access_token() is not None

    def get_current_price(self, code: str) -> dict:
        # TODO: 실 API path/tr_id 확정 시 교체
        return {
            'code': code,
            'price': round(10000 + random.random() * 50000, 2),
            'change_rate': round(random.uniform(-4, 6), 2),
            'volume': random.randint(10000, 1000000),
            'trading_value': random.randint(1_000_000_000, 80_000_000_000),
        }

    def get_period_ohlcv(self, code: str, timeframe: str = 'D', count: int = 120) -> list[dict]:
        today = datetime.utcnow().date()
        rows = []
        p = 10000 + random.random() * 30000
        for i in range(count):
            d = today - timedelta(days=(count - i))
            o = p * random.uniform(0.97, 1.03)
            c = o * random.uniform(0.96, 1.04)
            h = max(o, c) * random.uniform(1.0, 1.03)
            l = min(o, c) * random.uniform(0.97, 1.0)
            v = random.randint(10000, 1000000)
            tv = v * c
            rows.append({'date': d.isoformat(), 'open': o, 'high': h, 'low': l, 'close': c, 'volume': v, 'trading_value': tv, 'timeframe': timeframe})
            p = c
        return rows

    def get_intraday_minutes(self, code: str, interval_min: int = 5, points: int = 60) -> list[dict]:
        base = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        p = 10000 + random.random() * 30000
        rows = []
        for i in range(points):
            dt = base + timedelta(minutes=interval_min * i)
            o = p * random.uniform(0.998, 1.002)
            c = o * random.uniform(0.996, 1.004)
            h = max(o, c) * random.uniform(1.0, 1.002)
            l = min(o, c) * random.uniform(0.998, 1.0)
            v = random.randint(1000, 20000)
            rows.append({'dt': dt.isoformat(), 'open': o, 'high': h, 'low': l, 'close': c, 'volume': v, 'trading_value': v * c})
            p = c
        return rows
