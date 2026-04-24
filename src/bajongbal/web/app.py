from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from bajongbal.collectors.naver_theme_collector import refresh_naver_themes
from bajongbal.config import env_diagnostics, settings
from bajongbal.dart.client import DartClient
from bajongbal.kis.client import KISClient
from bajongbal.scanner.service import run_scan
from bajongbal.storage.db import get_conn, init_db, list_theme_filters, list_theme_stocks, now_iso


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
LAST_SCAN: dict = {'signals': [], 'theme_strengths': [], 'warnings': [], 'errors': [], 'scan_target_count': 0, 'scan_success_count': 0, 'scan_fail_count': 0, 'is_demo': False, 'diagnostics': {}}


def _template_response(request: Request, name: str, context: dict):
    return templates.TemplateResponse(request=request, name=name, context=context)


def _config_status() -> dict:
    diag = env_diagnostics()
    return {
        'KIS_APP_KEY': diag['KIS_APP_KEY'],
        'KIS_APP_SECRET': diag['KIS_APP_SECRET'],
        'KIS_BASE_URL': diag['KIS_BASE_URL'],
        'DART_API_KEY': diag['DART_API_KEY'],
        'kis_base_url_message': 'KIS_BASE_URL 미설정' if not settings.has_kis_base_url else '정상',
        'cwd': diag['cwd'],
        'env_candidate_paths': diag['env_candidate_paths'],
        'selected_env_file': diag['selected_env_file'],
        'env_file_path': diag['env_file_path'],
        'env_file_exists': diag['env_file_exists'],
        'env_file_loaded': diag['env_file_loaded'],
        'invalid_env_line_count': diag['invalid_env_line_count'],
        'invalid_env_line_numbers': diag['invalid_env_line_numbers'],
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
        'status': '성공' if ok else ('경고' if warning else '실패'),
        'theme_count': theme_cnt,
        'stock_count': map_cnt,
        'used_cache': result.used_cache or not ok,
        'reason': msg,
        'last_refreshed_at': result.last_refreshed_at or (last['refreshed_at'] if last else None),
        'html_structure_changed_possible': (map_cnt == 0),
    }


@app.get('/api/themes/list')
def api_theme_list():
    _ensure_schema()
    items = list_theme_filters()
    return {
        'items': items,
        'message': '수집된 테마가 없습니다. 먼저 [테마 갱신]을 실행하세요.' if not items else 'OK',
    }


@app.get('/api/themes/{theme_id}/stocks')
def api_theme_stocks(theme_id: str):
    _ensure_schema()
    return {'items': list_theme_stocks(theme_id=theme_id)}


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
        watchlist_group_id=int(payload['watchlist_group_id']) if payload.get('watchlist_group_id') else None,
        theme_id=str(payload['theme_id']) if payload.get('theme_id') else None,
        theme_name=payload.get('theme_name'),
    )
    LAST_SCAN.update(out)
    return out


@app.get('/api/watchlists')
def api_watchlists():
    _ensure_schema()
    with get_conn() as conn:
        rows = conn.execute('SELECT id,name,description,created_at,updated_at FROM watchlist_groups WHERE COALESCE(is_active,1)=1 ORDER BY id DESC').fetchall()
    return {'items': [dict(r) for r in rows]}


@app.post('/api/watchlists')
def api_watchlist_create(payload: dict):
    _ensure_schema()
    now = now_iso()
    with get_conn() as conn:
        cur = conn.execute('INSERT INTO watchlist_groups(name,description,created_at,updated_at,is_active) VALUES (?,?,?,?,1)', (payload['name'], payload.get('description'), now, now))
        conn.commit()
        row = conn.execute('SELECT id,name,description,created_at,updated_at FROM watchlist_groups WHERE id=?', (cur.lastrowid,)).fetchone()
    return dict(row)


@app.put('/api/watchlists/{group_id}')
def api_watchlist_update(group_id: int, payload: dict):
    _ensure_schema()
    with get_conn() as conn:
        conn.execute('UPDATE watchlist_groups SET name=?, description=?, updated_at=? WHERE id=?', (payload['name'], payload.get('description'), now_iso(), group_id))
        conn.commit()
        row = conn.execute('SELECT id,name,description,created_at,updated_at FROM watchlist_groups WHERE id=?', (group_id,)).fetchone()
    return dict(row) if row else {'ok': False}


@app.delete('/api/watchlists/{group_id}')
def api_watchlist_delete(group_id: int):
    _ensure_schema()
    with get_conn() as conn:
        conn.execute('UPDATE watchlist_items SET is_active=0, updated_at=? WHERE group_id=?', (now_iso(), group_id))
        conn.execute('UPDATE watchlist_groups SET is_active=0, updated_at=? WHERE id=?', (now_iso(), group_id))
        conn.commit()
    return {'ok': True}


@app.get('/api/watchlists/{group_id}/items')
def api_watchlist_items(group_id: int):
    _ensure_schema()
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT id,group_id,code,name,market,theme_names,memo,added_at,updated_at FROM watchlist_items WHERE group_id=? AND COALESCE(is_active,1)=1 ORDER BY id DESC',
            (group_id,),
        ).fetchall()
    return {'items': [dict(r) for r in rows]}


@app.post('/api/watchlists/{group_id}/items')
def api_watchlist_item_create(group_id: int, payload: dict):
    _ensure_schema()
    now = now_iso()
    with get_conn() as conn:
        conn.execute(
            'INSERT OR IGNORE INTO watchlist_items(group_id,code,name,market,theme_names,memo,added_at,updated_at,is_active) VALUES (?,?,?,?,?,?,?,?,1)',
            (group_id, str(payload['code']), payload.get('name'), payload.get('market'), payload.get('theme_names'), payload.get('memo'), now, now),
        )
        conn.execute('UPDATE watchlist_items SET is_active=1, name=COALESCE(?,name), updated_at=? WHERE group_id=? AND code=?', (payload.get('name'), now, group_id, str(payload['code'])))
        conn.commit()
        row = conn.execute(
            'SELECT id,group_id,code,name,market,theme_names,memo,added_at,updated_at FROM watchlist_items WHERE group_id=? AND code=? AND COALESCE(is_active,1)=1',
            (group_id, str(payload['code'])),
        ).fetchone()
    return dict(row)


@app.delete('/api/watchlists/{group_id}/items/{item_id}')
def api_watchlist_item_delete(group_id: int, item_id: int):
    _ensure_schema()
    with get_conn() as conn:
        conn.execute('UPDATE watchlist_items SET is_active=0, updated_at=? WHERE id=? AND group_id=?', (now_iso(), item_id, group_id))
        conn.commit()
    return {'ok': True}


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
