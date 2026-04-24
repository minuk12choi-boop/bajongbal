from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from bajongbal.config import settings


# TODO(사용자확인필요): 실전/모의 환경별 OAuth 경로 차이가 있는지 KIS 공식 문서 재확인 필요
TOKEN_PATH = Path('.kis_token_cache.json')


def _load_cache() -> dict[str, Any] | None:
    if not TOKEN_PATH.exists():
        return None
    try:
        return json.loads(TOKEN_PATH.read_text(encoding='utf-8'))
    except Exception:
        return None


def _is_valid(cache: dict[str, Any]) -> bool:
    expires_at = cache.get('expires_at')
    token = cache.get('access_token')
    if not expires_at or not token:
        return False
    try:
        exp = datetime.fromisoformat(expires_at)
    except ValueError:
        return False
    return exp > datetime.now(timezone.utc) + timedelta(minutes=2)


def request_access_token() -> str | None:
    if not settings.kis_app_key or not settings.kis_app_secret:
        return None

    url = f"{settings.kis_base_url}/oauth2/tokenP"
    payload = {
        'grant_type': 'client_credentials',
        'appkey': settings.kis_app_key,
        'appsecret': settings.kis_app_secret,
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
        data = res.json()
        token = data.get('access_token')
        expires_in = int(data.get('expires_in', 7200))
        if not token:
            return None
        TOKEN_PATH.write_text(
            json.dumps(
                {
                    'access_token': token,
                    'expires_at': (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
                },
                ensure_ascii=False,
            ),
            encoding='utf-8',
        )
        return token
    except Exception:
        return None


def get_access_token() -> str | None:
    cache = _load_cache()
    if cache and _is_valid(cache):
        return cache['access_token']
    return request_access_token()


def build_auth_headers(tr_id: str | None = None) -> dict[str, str]:
    token = get_access_token()
    headers = {'content-type': 'application/json; charset=utf-8'}
    if tr_id:
        headers['tr_id'] = tr_id
    if token:
        headers['authorization'] = f'Bearer {token}'
    if settings.kis_app_key:
        headers['appkey'] = settings.kis_app_key
    if settings.kis_app_secret:
        headers['appsecret'] = settings.kis_app_secret
    return headers
