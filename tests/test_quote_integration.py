from fastapi.testclient import TestClient

import bajongbal.web.app as web_app
from bajongbal.kis.client import KISStatus
from bajongbal.scanner.service import run_scan
from bajongbal.storage.db import get_conn, init_db
import pytest


@pytest.fixture(autouse=True)
def _restore_db_path():
    from bajongbal.config import settings

    original = settings.db_path
    try:
        yield
    finally:
        settings.db_path = original


class DummyKISMixed:
    def health_detail(self):
        class X:
            status = KISStatus.OK
            message = '정상'
        return X()

    def get_current_price(self, code):
        class X:
            status = KISStatus.OK if str(code) == '005930' else KISStatus.API_FAILED
            message = '정상'
            data = {'code': str(code), 'price': 70000, 'change_rate': 1.0, 'volume': 1000, 'trading_value': 30000000, 'market': 'J'}
            diagnostics = {'response_keys': ['output']}
        return X()

    def get_period_ohlcv(self, code, timeframe, count):
        class X:
            status = KISStatus.OK
            message = '정상'
            data = [{'date': f'2026-01-{i:02d}', 'open': 100+i, 'high': 110+i, 'low': 90+i, 'close': 105+i, 'volume': 1000+i, 'trading_value': 100000+i} for i in range(1, 40)]
            diagnostics = None
        return X()

    def get_intraday_minutes(self, code, interval, points):
        class X:
            status = KISStatus.OK
            message = '정상'
            data = [{'dt': f'15{(i%60):02d}00', 'open': 100+i, 'high': 110+i, 'low': 90+i, 'close': 105+i, 'volume': 1000+i, 'trading_value': 100000+i} for i in range(1, 40)]
            diagnostics = None
        return X()


class DummyDart:
    def get_recent_filings(self, code, limit):
        return []


def test_quote_status_consistency_and_diagnose(monkeypatch, tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    with get_conn() as conn:
        conn.execute("INSERT INTO stock_theme_map(code,name,theme_id,theme_name,updated_at) VALUES ('005930','삼성전자','1','반도체','2026-01-01')")
        conn.execute("INSERT INTO watchlist_groups(name,description,created_at,updated_at,is_active) VALUES ('g','', '2026-01-01','2026-01-01',1)")
        gid = conn.execute('SELECT id FROM watchlist_groups').fetchone()[0]
        conn.execute("INSERT INTO watchlist_items(group_id,code,name,added_at,updated_at,is_active) VALUES (?,?,?,?,?,1)", (gid, '005930', '삼성전자', '2026-01-01', '2026-01-01'))
        conn.commit()

    monkeypatch.setattr(web_app, 'KISClient', lambda *_: DummyKISMixed())
    c = TestClient(web_app.app)

    theme = c.get('/api/theme-stocks?code=005930').json()['items'][0]
    watch = c.get(f'/api/watchlists/{gid}/quotes').json()['items'][0]
    diag = c.get('/api/quote/diagnose?code=005930').json()
    assert theme['kis_status'] == watch['kis_status'] == diag['quote_status'] == 'OK'


def test_watchlist_append_and_code_validation(monkeypatch, tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    monkeypatch.setattr(web_app, 'KISClient', lambda *_: DummyKISMixed())
    c = TestClient(web_app.app)
    gid = c.post('/api/watchlists', json={'name': 'g'}).json()['id']

    bad = c.post(f'/api/watchlists/{gid}/items', json={'code': '', 'name': 'x'}).json()
    assert bad['ok'] is False

    c.post(f'/api/watchlists/{gid}/items', json={'code': '005930', 'name': 'A'})
    c.post(f'/api/watchlists/{gid}/items', json={'code': '000660', 'name': 'B'})
    c.post(f'/api/watchlists/{gid}/items', json={'code': '123456', 'name': 'C'})
    c.post(f'/api/watchlists/{gid}/items', json={'code': '005930', 'name': 'A2'})
    items = c.get(f'/api/watchlists/{gid}/items').json()['items']
    codes = {x['code'] for x in items}
    assert {'005930', '000660', '123456'} <= codes


def test_scan_display_limit_and_threshold_zero(tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    with get_conn() as conn:
        conn.execute("INSERT INTO stock_theme_map(code,name,theme_id,theme_name,updated_at) VALUES ('005930','삼성전자','1','반도체','2026-01-01')")
        conn.execute("INSERT INTO stock_theme_map(code,name,theme_id,theme_name,updated_at) VALUES ('000660','하이닉스','1','반도체','2026-01-01')")
        conn.execute("INSERT INTO stock_theme_map(code,name,theme_id,theme_name,updated_at) VALUES ('035420','네이버','1','반도체','2026-01-01')")
        conn.commit()

    out = run_scan(DummyKISMixed(), DummyDart(), 'data/watchlist.example.csv', scope_mode='all_theme_stocks', max_symbols=2, score_threshold=0)
    assert out['diagnostics']['scan_target_count_before_limit'] == 3
    assert out['diagnostics']['scan_target_count'] == 3
    assert len(out['signals']) <= 2
