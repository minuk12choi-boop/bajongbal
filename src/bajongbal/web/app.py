from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from bajongbal.collectors.naver_theme_collector import refresh_naver_themes
from bajongbal.config import settings
from bajongbal.dart.client import DartClient
from bajongbal.kis.client import KISClient
from bajongbal.scanner.service import run_scan
from bajongbal.storage.db import get_conn, init_db


app = FastAPI(title='BAJONGBAL 급등직전 감지기')
templates = Jinja2Templates(directory=str(Path(__file__).parent / 'templates'))
LAST_SCAN: dict = {'signals': [], 'theme_strengths': []}


def _status() -> dict:
    kis = KISClient(settings.kis_base_url)
    dart = DartClient()
    with get_conn() as conn:
        row = conn.execute('SELECT refreshed_at, success, message FROM theme_snapshots ORDER BY id DESC LIMIT 1').fetchone()
    return {
        'now': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'kis_ok': kis.health(),
        'dart_ok': dart.health(),
        'theme_updated_at': row['refreshed_at'] if row else '없음',
        'theme_message': row['message'] if row else '초기 상태',
    }


@app.on_event('startup')
def _startup() -> None:
    init_db()


@app.get('/', response_class=HTMLResponse)
@app.get('/dashboard', response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse('dashboard.html', {'request': request, 'status': _status(), 'scan': LAST_SCAN})


@app.post('/api/themes/refresh')
def api_theme_refresh():
    result = refresh_naver_themes()
    return result.__dict__


@app.get('/api/themes/status')
def api_theme_status():
    return _status()


@app.get('/api/themes/today')
def api_theme_today():
    return {'theme_strengths': LAST_SCAN.get('theme_strengths', [])}


@app.post('/api/scan')
def api_scan(payload: dict | None = None):
    payload = payload or {}
    out = run_scan(
        kis=KISClient(settings.kis_base_url),
        dart=DartClient(),
        watchlist_path=payload.get('watchlist', 'data/watchlist.example.csv'),
        score_threshold=float(payload.get('score_threshold', 60)),
        use_dart=bool(payload.get('use_dart', True)),
        max_symbols=int(payload.get('max_symbols', 50)),
    )
    LAST_SCAN.update(out)
    return out


@app.get('/api/signals/recent')
def api_recent_signals(limit: int = 50):
    with get_conn() as conn:
        rows = conn.execute('SELECT * FROM signals ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        data = [dict(r) for r in rows]
    return {'items': data}


@app.get('/api/health')
def api_health():
    return {'ok': True, **_status()}
