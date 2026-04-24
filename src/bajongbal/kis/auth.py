from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta

import requests

from bajongbal.config import settings


TOKEN_PATH = Path('.kis_token_cache.json')


def _load_cache() -> dict | None:
    if not TOKEN_PATH.exists():
        return None
    try:
        return json.loads(TOKEN_PATH.read_text(encoding='utf-8'))
    except Exception:
        return None


def get_access_token() -> str | None:
    cache = _load_cache()
    if cache:
        exp = datetime.fromisoformat(cache['expires_at'])
        if exp > datetime.utcnow() + timedelta(minutes=2):
            return cache['access_token']
    if not settings.kis_app_key or not settings.kis_app_secret:
        return None
    # TODO: 실계정/모의계정별 path, tr_id는 문서 확인 후 보강
    url = f"{settings.kis_base_url}/oauth2/tokenP"
    payload = {
        'grant_type': 'client_credentials',
        'appkey': settings.kis_app_key,
        'appsecret': settings.kis_app_secret,
    }
    try:
        r = requests.post(url, json=payload, timeout=8)
        r.raise_for_status()
        data = r.json()
        token = data.get('access_token')
        if token:
            TOKEN_PATH.write_text(
                json.dumps({
                    'access_token': token,
                    'expires_at': (datetime.utcnow() + timedelta(hours=20)).isoformat(),
                }),
                encoding='utf-8',
            )
        return token
    except Exception:
        return None
