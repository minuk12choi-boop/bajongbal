from bajongbal.scanner.service import run_scan
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
            diagnostics = None
        return X()

    def get_period_ohlcv(self, code, timeframe, count):
        class X:
            status = 'OK'
            message = '정상'
            data = [{'date': f'2026-01-{i:02d}', 'open': 19000+i, 'high': 21000+i, 'low': 18000+i, 'close': 20000+i, 'volume': 1000+i, 'trading_value': 10000000+i, 'timeframe': 'D'} for i in range(1, 121)]
            diagnostics = None
        return X()

    def get_intraday_minutes(self, code, interval, points):
        class X:
            status = 'OK'
            message = '정상'
            data = [{'dt': f'09:{i:02d}', 'open': 20000+i, 'high': 20005+i, 'low': 19995+i, 'close': 20001+i, 'volume': 100+i, 'trading_value': 100000+i} for i in range(1, 61)]
            diagnostics = None
        return X()


class DummyDART:
    def get_recent_filings(self, code, limit):
        return []


def test_selected_theme_count_and_limit(tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    with get_conn() as conn:
        for i in range(144):
            conn.execute('INSERT INTO stock_theme_map(code,name,theme_id,theme_name,updated_at) VALUES (?,?,?,?,?)', (f'{100000+i:06d}', f'N{i}', '64', '2차전지', '2026-01-01'))
        conn.execute("INSERT INTO watchlist_groups(name,description,created_at,updated_at,is_active) VALUES ('g','', '2026-01-01','2026-01-01',1)")
        conn.commit()

    out = run_scan(DummyKISOk(), DummyDART(), 'data/watchlist.example.csv', scope_mode='selected_theme', theme_id='64', theme_name='2차전지', max_symbols=50, score_threshold=0)
    assert out['diagnostics']['selected_theme_stock_count'] == 144
    assert out['diagnostics']['scan_target_count_before_limit'] == 144
    assert out['diagnostics']['scan_target_count'] == 144


def test_scope_mode_selected_theme_requires_theme(tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    out = run_scan(DummyKISOk(), DummyDART(), 'data/watchlist.example.csv', scope_mode='selected_theme', score_threshold=0)
    assert any('특정 테마 조회를 선택했지만 테마가 선택되지 않았습니다.' in w for w in out['warnings'])


def test_scope_mode_watchlist_group(tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    with get_conn() as conn:
        conn.execute("INSERT INTO watchlist_groups(name,description,created_at,updated_at,is_active) VALUES ('g','', '2026-01-01','2026-01-01',1)")
        gid = conn.execute('SELECT id FROM watchlist_groups').fetchone()[0]
        conn.execute("INSERT OR IGNORE INTO watchlist_items(group_id,code,name,added_at,updated_at,is_active) VALUES (?,?,?,?,?,1)", (gid, '005930', '삼성전자', '2026-01-01', '2026-01-01'))
        conn.commit()
    out = run_scan(DummyKISOk(), DummyDART(), 'data/watchlist.example.csv', scope_mode='watchlist_group', watchlist_group_id=gid, score_threshold=0)
    assert out['diagnostics']['scope_mode'] == 'watchlist_group'
    assert out['diagnostics']['watchlist_item_count'] >= 1
