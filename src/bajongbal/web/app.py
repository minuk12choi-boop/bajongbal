from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from bajongbal.collectors.naver_theme_collector import refresh_naver_themes
from bajongbal.config import settings
from bajongbal.dart.client import DartClient
from bajongbal.kis.client import KISClient
from bajongbal.scanner.service import run_scan
from bajongbal.storage.db import get_conn, init_db


def _ensure_schema() -> None:
    """요청 시점에도 스키마를 보장해 테이블 미생성으로 500이 나지 않게 방어한다."""
    try:
        init_db()
    except Exception:
        # 경로 권한 문제 등에서도 대시보드가 완전히 죽지 않도록 보호
        return


@asynccontextmanager
async def lifespan(_: FastAPI):
    _ensure_schema()
    yield


app = FastAPI(title='BAJONGBAL 급등직전 감지기', lifespan=lifespan)
templates = Jinja2Templates(directory=str(Path(__file__).parent / 'templates'))
LAST_SCAN: dict = {'signals': [], 'theme_strengths': []}


def _template_response(request: Request, name: str, context: dict):
    """Starlette/FastAPI 버전 차이에 안전한 TemplateResponse 호출 래퍼."""
    return templates.TemplateResponse(request=request, name=name, context=context)


def _status() -> dict:
    _ensure_schema()
    kis = KISClient(settings.kis_base_url)
    dart = DartClient()

    row = None
    try:
        with get_conn() as conn:
            row = conn.execute('SELECT refreshed_at, success, message FROM theme_snapshots ORDER BY id DESC LIMIT 1').fetchone()
    except Exception:
        row = None

    return {
        'now': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'kis_ok': kis.health(),
        'dart_ok': dart.health(),
        'theme_updated_at': row['refreshed_at'] if row else '테마 캐시 없음',
        'theme_message': row['message'] if row else '테마 캐시 없음 / 테마 갱신 필요',
    }


@app.get('/', response_class=HTMLResponse)
@app.get('/dashboard', response_class=HTMLResponse)
def dashboard(request: Request):
    _ensure_schema()
    return _template_response(request=request, name='dashboard.html', context={'request': request, 'status': _status(), 'scan': LAST_SCAN})


@app.post('/api/themes/refresh')
def api_theme_refresh():
    _ensure_schema()
    result = refresh_naver_themes()
    return result.__dict__


@app.get('/api/themes/status')
def api_theme_status():
    _ensure_schema()
    return _status()


@app.get('/api/themes/today')
def api_theme_today():
    _ensure_schema()
    return {'theme_strengths': LAST_SCAN.get('theme_strengths', [])}


@app.post('/api/scan')
def api_scan(payload: dict | None = None):
    _ensure_schema()
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
    _ensure_schema()
    with get_conn() as conn:
        rows = conn.execute('SELECT * FROM signals ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        data = [dict(r) for r in rows]
    return {'items': data}


@app.get('/api/health')
def api_health():
    _ensure_schema()
    return {'ok': True, **_status()}
