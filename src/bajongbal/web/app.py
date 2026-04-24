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
    try:
        init_db()
    except Exception:
        return


@asynccontextmanager
async def lifespan(_: FastAPI):
    _ensure_schema()
    yield


app = FastAPI(title='BAJONGBAL 급등직전 감지기', lifespan=lifespan)
templates = Jinja2Templates(directory=str(Path(__file__).parent / 'templates'))
LAST_SCAN: dict = {'signals': [], 'theme_strengths': [], 'warnings': [], 'errors': [], 'scan_target_count': 0, 'scan_success_count': 0, 'scan_fail_count': 0, 'is_demo': False}


def _template_response(request: Request, name: str, context: dict):
    return templates.TemplateResponse(request=request, name=name, context=context)


def _config_status() -> dict:
    return {
        'KIS_APP_KEY': 'Y' if settings.has_kis_app_key else 'N',
        'KIS_APP_SECRET': 'Y' if settings.has_kis_app_secret else 'N',
        'KIS_BASE_URL': 'Y' if settings.has_kis_base_url else 'N',
        'DART_API_KEY': 'Y' if settings.has_dart_api_key else 'N',
        'kis_base_url_message': 'KIS_BASE_URL 미설정' if not settings.has_kis_base_url else '정상',
    }


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
        'config': _config_status(),
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
    with get_conn() as conn:
        theme_cnt = conn.execute('SELECT COUNT(DISTINCT theme_id) FROM theme_constituents').fetchone()[0]
        map_cnt = conn.execute('SELECT COUNT(*) FROM stock_theme_map').fetchone()[0]
        last = conn.execute('SELECT refreshed_at FROM theme_snapshots ORDER BY id DESC LIMIT 1').fetchone()

    ok = bool(result.success and theme_cnt > 0 and map_cnt > 0)
    warning = not ok
    msg = result.message
    if map_cnt == 0:
        msg = '수집 0건: 네이버 HTML 구조 변경 가능성 또는 네트워크 이슈'

    return {
        'ok': ok,
        'warning': warning,
        'theme_count': theme_cnt,
        'stock_count': map_cnt,
        'used_cache': not ok,
        'reason': msg,
        'last_refreshed_at': last['refreshed_at'] if last else None,
    }


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
        target_mode=payload.get('target_mode', '관심종목'),
        demo_mode=bool(payload.get('demo_mode', False)),
    )
    LAST_SCAN.update(out)
    return out


@app.get('/api/signals/recent')
def api_recent_signals(limit: int = 50, include_demo: bool = False):
    _ensure_schema()
    with get_conn() as conn:
        if include_demo:
            rows = conn.execute('SELECT * FROM signals ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM signals WHERE COALESCE(is_demo,0)=0 ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        data = [dict(r) for r in rows]
    return {'items': data}


@app.get('/api/config/status')
def api_config_status():
    return _config_status()


@app.get('/api/health')
def api_health():
    _ensure_schema()
    return {'ok': True, **_status()}
