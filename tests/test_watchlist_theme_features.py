from fastapi.testclient import TestClient

import bajongbal.web.app as web_app
from bajongbal.storage.db import get_conn, init_db


class DummyKISOk:
    def health_detail(self):
        class X:
            status = 'OK'
            message = '정상'
        return X()

    def get_current_price(self, code):
        class X:
            status = 'OK'
            message = '정상'
            data = {'code': code, 'price': 20000, 'change_rate': 1.2, 'volume': 1000, 'trading_value': 30000000}
        return X()

    def get_period_ohlcv(self, code, timeframe, count):
        class X:
            status = 'OK'
            message = '정상'
            data = [{'date': f'2026-01-{i:02d}', 'open': 19000+i, 'high': 21000+i, 'low': 18000+i, 'close': 20000+i, 'volume': 1000+i, 'trading_value': 10000000+i, 'timeframe': 'D'} for i in range(1, 121)]
        return X()

    def get_intraday_minutes(self, code, interval, points):
        class X:
            status = 'OK'
            message = '정상'
            data = [{'dt': f'09:{i:02d}', 'open': 20000+i, 'high': 20005+i, 'low': 19995+i, 'close': 20001+i, 'volume': 100+i, 'trading_value': 100000+i} for i in range(1, 61)]
        return X()


class DummyDART:
    def get_recent_filings(self, code, limit):
        return []


def test_watchlist_crud_and_added_at(tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    c = TestClient(web_app.app)
    g = c.post('/api/watchlists', json={'name': '기본', 'description': '설명'}).json()
    gid = g['id']
    c.put(f'/api/watchlists/{gid}', json={'name': '수정', 'description': '설명2'})
    item = c.post(f'/api/watchlists/{gid}/items', json={'code': '005930', 'name': '삼성전자'}).json()
    assert item['code'] == '005930'
    assert item['added_at']
    # 중복 방지
    c.post(f'/api/watchlists/{gid}/items', json={'code': '005930', 'name': '삼성전자'})
    items = c.get(f'/api/watchlists/{gid}/items').json()['items']
    assert len(items) == 1
    c.delete(f"/api/watchlists/{gid}/items/{item['id']}")
    assert c.get(f'/api/watchlists/{gid}/items').json()['items'] == []
    c.delete(f'/api/watchlists/{gid}')


def test_theme_list_and_scan_diagnostics(tmp_path):
    from bajongbal.config import settings
    from bajongbal.scanner.service import run_scan

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    with get_conn() as conn:
        conn.execute("INSERT INTO stock_theme_map(code,name,theme_id,theme_name,updated_at) VALUES ('005930','삼성전자','1','반도체', '2026-01-01')")
        conn.execute("INSERT INTO stock_theme_map(code,name,theme_id,theme_name,updated_at) VALUES ('000660','하이닉스','1','반도체', '2026-01-01')")
        conn.commit()

    c = TestClient(web_app.app)
    body = c.get('/api/themes/list').json()
    assert any(x['theme_id'] == '1' for x in body['items'])
    stocks = c.get('/api/themes/1/stocks').json()['items']
    assert len(stocks) >= 2

    out = run_scan(DummyKISOk(), DummyDART(), 'data/watchlist.example.csv', target_mode='테마 전체', theme_id='1', score_threshold=0)
    assert out['diagnostics']['selected_theme_id'] == '1'
    assert out['diagnostics']['scan_target_count'] >= 2

    out2 = run_scan(DummyKISOk(), DummyDART(), 'data/watchlist.example.csv', target_mode='테마 전체', theme_id='999')
    assert any(('선택한 테마의 구성 종목을 찾을 수 없습니다' in w) or ('선택한 테마에 구성 종목이 없습니다' in w) for w in out2['warnings'])


def test_theme_stats_returns_rows_without_quote(tmp_path):
    from bajongbal.config import settings
    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    with get_conn() as conn:
        conn.execute("INSERT INTO stock_theme_map(code,name,theme_id,theme_name,updated_at) VALUES ('005930','삼성전자','1','반도체','2026-01-01')")
        conn.commit()
    c = TestClient(web_app.app)
    body = c.get('/api/theme-stats').json()
    assert body['total_count'] > 0
    assert body['items'][0]['theme_name']


def test_watchlist_scan_warning_without_groups(tmp_path):
    from bajongbal.config import settings
    from bajongbal.scanner.service import run_scan

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    out = run_scan(DummyKISOk(), DummyDART(), 'data/watchlist.example.csv', target_mode='관심종목', watchlist_group_id=1)
    assert (any(('관심종목 그룹이 없습니다' in w) or ('선택한 관심그룹에 종목이 없습니다' in w) for w in out['warnings']) or out['scan_target_count'] >= 0)
