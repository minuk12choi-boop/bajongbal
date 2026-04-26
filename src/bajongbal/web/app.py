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
from bajongbal.quote_service import code_valid, diagnose_quote, fetch_quote_for_code, normalize_code
from bajongbal.scanner.service import run_scan
from bajongbal.storage.db import (
    add_watchlist_item,
    get_conn,
    get_watchlist_membership,
    init_db,
    list_theme_filters,
    list_theme_stocks,
    list_theme_stocks_filtered,
    list_watchlist_groups,
    list_watchlist_items,
    now_iso,
    remove_watchlist_item,
)


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
        'KIS_APP_KEY': diag['KIS_APP_KEY'], 'KIS_APP_SECRET': diag['KIS_APP_SECRET'], 'KIS_BASE_URL': diag['KIS_BASE_URL'], 'DART_API_KEY': diag['DART_API_KEY'],
        'cwd': diag['cwd'], 'env_candidate_paths': diag['env_candidate_paths'], 'selected_env_file': diag['selected_env_file'], 'env_file_path': diag['env_file_path'],
        'env_file_exists': diag['env_file_exists'], 'env_file_loaded': diag['env_file_loaded'], 'invalid_env_line_count': diag['invalid_env_line_count'], 'invalid_env_line_numbers': diag['invalid_env_line_numbers'],
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
    return {'now': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'kis_ok': kis.health(), 'dart_ok': dart.health(), 'theme_updated_at': row['refreshed_at'] if row else '테마 캐시 없음', 'theme_message': row['message'] if row else '테마 캐시 없음 / 테마 갱신 필요', 'config': _config_status()}


@app.get('/', response_class=HTMLResponse)
@app.get('/dashboard', response_class=HTMLResponse)
def dashboard(request: Request):
    _ensure_schema()
    return _template_response(request=request, name='dashboard.html', context={'request': request, 'status': _status(), 'scan': LAST_SCAN, 'active_menu': 'dashboard'})


@app.get('/theme-stocks', response_class=HTMLResponse)
def theme_stocks_page(request: Request):
    _ensure_schema()
    return _template_response(request=request, name='theme_stocks.html', context={'request': request, 'status': _status(), 'active_menu': 'theme_stocks'})


@app.get('/watchlists', response_class=HTMLResponse)
def watchlists_page(request: Request):
    _ensure_schema()
    return _template_response(request=request, name='watchlists.html', context={'request': request, 'status': _status(), 'active_menu': 'watchlists'})



@app.get('/types', response_class=HTMLResponse)
def types_page(request: Request):
    _ensure_schema()
    return _template_response(request=request, name='types.html', context={'request': request, 'active_menu': 'types'})

@app.post('/api/themes/refresh')
def api_theme_refresh(payload: dict | None = None):
    _ensure_schema()
    payload = payload or {}
    try:
        result = refresh_naver_themes(force=bool(payload.get('force', False)))
    except TypeError:
        result = refresh_naver_themes()
    with get_conn() as conn:
        conn.execute('INSERT INTO theme_snapshots(refreshed_at, success, message) VALUES (?,?,?)', (result.last_refreshed_at or now_iso(), int(result.success), result.message))
        conn.commit()
        theme_cnt = conn.execute('SELECT COUNT(DISTINCT theme_id) FROM theme_constituents').fetchone()[0]
        map_cnt = conn.execute('SELECT COUNT(*) FROM stock_theme_map').fetchone()[0]
        last = conn.execute('SELECT refreshed_at FROM theme_snapshots ORDER BY id DESC LIMIT 1').fetchone()
    ok = bool(result.success and theme_cnt > 0 and map_cnt > 0)
    msg = result.message if map_cnt > 0 else '수집 0건: 네이버 HTML 구조 변경 가능성 또는 네트워크 이슈'
    return {'ok': ok, 'warning': not ok, 'status': '성공' if ok else '경고', 'theme_count': theme_cnt, 'stock_count': map_cnt, 'used_cache': result.used_cache or not ok, 'reason': msg, 'last_refreshed_at': result.last_refreshed_at or (last['refreshed_at'] if last else None), 'html_structure_changed_possible': (map_cnt == 0)}


@app.get('/api/themes/list')
def api_theme_list():
    _ensure_schema()
    items = list_theme_filters()
    with get_conn() as conn:
        total = conn.execute('SELECT COUNT(*) FROM stock_theme_map').fetchone()[0]
    return {'items': items, 'summary': {'theme_count': len(items), 'stock_count': total}}



@app.get('/api/theme-stats')
def api_theme_stats():
    _ensure_schema()
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT theme_name, COUNT(DISTINCT code) AS stock_count,
                   NULL AS avg_change_rate,
                   0 AS sum_volume,
                   NULL AS sum_trading_value_10k,
                   NULL AS up_count,
                   0 AS down_count,
                   MAX(updated_at) AS last_refreshed_at
            FROM stock_theme_map
            GROUP BY theme_name
        ''').fetchall()
    items=[]
    for r in rows:
        d=dict(r)
        total=max(int(d.get('stock_count') or 0),1)
        d['up_ratio']=round((float(d.get('up_count') or 0)/total)*100,2)
        d['sum_trading_value_10k'] = d['sum_trading_value_10k'] if d.get('sum_trading_value_10k') is not None else '시세 미조회'
        d['avg_change_rate'] = d['avg_change_rate'] if d.get('avg_change_rate') is not None else '시세 미조회'
        d['up_count'] = d['up_count'] if d.get('up_count') is not None else '시세 미조회'
        items.append(d)
    return {'items': items, 'total_count': len(items)}

@app.get('/api/themes/{theme_id}/stocks')
def api_theme_stocks(theme_id: str):
    _ensure_schema()
    return {'items': list_theme_stocks(theme_id=theme_id)}



@app.get('/api/suggest')
def api_suggest(q: str = '', kind: str = 'all', limit: int = 20):
    _ensure_schema()
    q = q.strip()
    items: list[str] = []
    if not q:
        return {'items': []}
    with get_conn() as conn:
        if kind in {'all','theme'}:
            rows = conn.execute('SELECT DISTINCT theme_name FROM stock_theme_map WHERE theme_name LIKE ? LIMIT ?', (f'%{q}%', limit)).fetchall()
            items.extend([r[0] for r in rows if r[0]])
        if kind in {'all','name'}:
            rows = conn.execute('SELECT DISTINCT name FROM stock_theme_map WHERE name LIKE ? LIMIT ?', (f'%{q}%', limit)).fetchall()
            items.extend([r[0] for r in rows if r[0]])
        if kind in {'all','code'}:
            rows = conn.execute('SELECT DISTINCT code FROM stock_theme_map WHERE code LIKE ? LIMIT ?', (f'%{q}%', limit)).fetchall()
            items.extend([r[0] for r in rows if r[0]])
    uniq=[]
    for x in items:
        if x not in uniq:
            uniq.append(x)
    return {'items': uniq[:limit]}

@app.get('/api/theme-stocks')
def api_theme_stocks_search(theme_id: str | None = None, theme_name: str | None = None, code: str | None = None, name: str | None = None, market: str | None = None, status: str | None = None, max_symbols: int = 100):
    _ensure_schema()
    base = list_theme_stocks_filtered(theme_id=theme_id, theme_name=theme_name, code=code, name=name, limit=max_symbols)
    kis = KISClient(settings.kis_base_url)
    items, warnings, errors = [], [], []
    for row in base:
        q = fetch_quote_for_code(kis, str(row.get('code')), context='theme_stocks')
        if q.status != 'OK':
            errors.append(f"{row.get('code')}: {q.status}")
        market_label = '확인 필요' if q.market == 'UNKNOWN' else q.market
        items.append({'star': '☆', 'theme_name': row.get('theme_name'), 'code': q.code or row.get('code'), 'name': row.get('name'), 'price': q.price, 'change_rate': q.change_rate, 'volume': q.volume, 'trading_value': q.trading_value_10k, 'market_cap': q.market_cap_10k, 'market': market_label, 'fetched_at': now_iso(), 'kis_status': q.status, 'failure_reason': q.failure_reason})
    
    if status:
        items = [x for x in items if str(x.get('kis_status')) == status]
    if market:
        items = [x for x in items if market in str(x.get('market', ''))]

    if len(base) >= max_symbols:
        warnings.append(f'조회 대상이 많아 상위 {max_symbols}건만 조회했습니다.')
    return {'items': items, 'diagnostics': {'requested_max_symbols': max_symbols, 'returned': len(items)}, 'warnings': warnings, 'errors': errors[:10]}


@app.get('/api/themes/status')
def api_theme_status():
    _ensure_schema()
    return _status()


@app.post('/api/scan')
def api_scan(payload: dict | None = None):
    _ensure_schema()
    payload = payload or {}
    out = run_scan(
        kis=KISClient(settings.kis_base_url), dart=DartClient(), watchlist_path=payload.get('watchlist', 'data/watchlist.example.csv'),
        score_threshold=float(payload.get('score_threshold', 60)), use_dart=bool(payload.get('use_dart', True)), max_symbols=int(payload.get('display_limit', payload.get('max_symbols', 50))),
        target_mode=payload.get('target_mode', '관심종목'), demo_mode=bool(payload.get('demo_mode', False)),
        watchlist_group_id=int(payload['watchlist_group_id']) if payload.get('watchlist_group_id') else None,
        theme_id=str(payload['theme_id']) if payload.get('theme_id') else None, theme_name=payload.get('theme_name'), scope_mode=payload.get('scope_mode'), filter_code=payload.get('filter_code'), filter_name=payload.get('filter_name'),
    )
    LAST_SCAN.update(out)
    return out


@app.get('/api/watchlists')
def api_watchlists():
    _ensure_schema()
    return {'items': list_watchlist_groups()}


@app.get('/api/watchlists/membership')
def api_watchlist_membership(code: str):
    _ensure_schema()
    return {'items': get_watchlist_membership(code)}


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
    rows = list_watchlist_groups()
    return next((r for r in rows if r['id'] == group_id), {'ok': False})


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
    return {'items': list_watchlist_items(group_id)}


@app.post('/api/watchlists/{group_id}/items')
def api_watchlist_item_create(group_id: int, payload: dict):
    _ensure_schema()
    code = normalize_code(payload.get('code'))
    if not code:
        return {'ok': False, 'error': '종목코드가 없습니다.', 'code': ''}
    if not code_valid(code):
        return {'ok': False, 'error': '유효하지 않은 종목코드(6자리 숫자 아님)', 'code': code}
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM stock_theme_map WHERE code=? LIMIT 1", (code,)).fetchone()
    if not exists:
        return {'ok': False, 'error': '존재하지 않는 종목코드입니다.', 'code': code}
    return add_watchlist_item(group_id, code, payload.get('name'), payload.get('market'), payload.get('theme_names'), payload.get('memo'))


@app.get('/api/watchlists/{group_id}/quotes')
def api_watchlist_quotes(group_id: int):
    _ensure_schema()
    items = list_watchlist_items(group_id)
    kis = KISClient(settings.kis_base_url)
    out = []
    for row in items:
        q = fetch_quote_for_code(kis, str(row.get('code')), context='watchlist')
        out.append(
            {
                **row,
                'price': q.price,
                'change_rate': q.change_rate,
                'volume': q.volume,
                'trading_value': q.trading_value_10k,
                'market_cap': q.market_cap_10k,
                'kis_status': q.status,
                'failure_reason': q.failure_reason,
                'market': q.market,
            }
        )
    return {'items': out}


@app.delete('/api/watchlists/{group_id}/items/{item_id}')
def api_watchlist_item_delete(group_id: int, item_id: int):
    _ensure_schema()
    remove_watchlist_item(group_id, item_id=item_id)
    return {'ok': True}


@app.get('/api/signals/recent')
def api_recent_signals(limit: int = 50, include_demo: bool = False):
    _ensure_schema()
    with get_conn() as conn:
        sql = 'SELECT * FROM signals ORDER BY id DESC LIMIT ?' if include_demo else 'SELECT * FROM signals WHERE COALESCE(is_demo,0)=0 ORDER BY id DESC LIMIT ?'
        rows = conn.execute(sql, (limit,)).fetchall()
    return {'items': [dict(r) for r in rows]}


@app.get('/api/config/status')
def api_config_status():
    return _config_status()


@app.get('/api/health')
def api_health():
    _ensure_schema()
    return {'ok': True, **_status()}


@app.get('/api/quote/diagnose')
def api_quote_diagnose(code: str = ''):
    _ensure_schema()
    kis = KISClient(settings.kis_base_url)
    return diagnose_quote(kis, code)


@app.get('/api/stocks/search')
def api_stocks_search(q: str = '', limit: int = 20):
    _ensure_schema()
    q = q.strip()
    if not q:
        return {'items': []}
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT code, MAX(name) AS name, MAX(theme_name) AS theme_name, MAX(updated_at) AS updated_at
            FROM stock_theme_map
            WHERE code LIKE ? OR name LIKE ?
            GROUP BY code
            ORDER BY code
            LIMIT ?
            """,
            (f'%{q}%', f'%{q}%', limit),
        ).fetchall()
    return {'items': [dict(r) for r in rows]}


@app.get('/api/chart/{code}')
def api_chart(code: str, timeframe: str = 'day', interval: int = 5, points: int = 120):
    _ensure_schema()
    kis = KISClient(settings.kis_base_url)
    ncode = normalize_code(code)
    if timeframe == 'minute':
        out = kis.get_intraday_minutes(ncode, interval, points)
    else:
        tf_map = {'day': 'D', 'week': 'W', 'month': 'M', 'year': 'Y'}
        out = kis.get_period_ohlcv(ncode, tf_map.get(timeframe, 'D'), points)
    if out.status != 'OK':
        return {'ok': False, 'code': ncode, 'timeframe': timeframe, 'reason': 'KIS 차트 데이터 없음 또는 호출 실패', 'items': []}
    return {'ok': True, 'code': ncode, 'timeframe': timeframe, 'interval': interval, 'items': out.data}
