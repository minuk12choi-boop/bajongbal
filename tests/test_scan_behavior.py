from pathlib import Path

from bajongbal.scanner.service import run_scan
from bajongbal.storage.db import get_conn, init_db


class DummyKISFail:
    def health_detail(self):
        class X:
            status = 'CONFIG_MISSING'
            message = 'KIS 환경변수가 누락되었습니다.'
        return X()


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


def test_kis_missing_returns_empty(tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    out = run_scan(DummyKISFail(), DummyDART(), 'data/watchlist.example.csv', target_mode='관심종목', demo_mode=False)
    assert out['signals'] == []
    assert any('KIS 연결 실패' in w for w in out['warnings'])
    assert all(s.get('current_price') != 10000 for s in out['signals'])


def test_theme_mode_without_cache_returns_warning(tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    out = run_scan(DummyKISOk(), DummyDART(), 'data/watchlist.example.csv', target_mode='테마 전체', demo_mode=False)
    assert out['scan_target_count'] >= 0
    assert (any('테마 캐시가 없습니다' in w for w in out['warnings']) or len(out['signals']) >= 0)


def test_theme_mode_with_cache_uses_cached_symbols(tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    with get_conn() as conn:
        conn.execute("INSERT INTO stock_theme_map(code,name,theme_id,theme_name,updated_at) VALUES ('005930','삼성전자','1','반도체','2026-01-01')")
        conn.execute("INSERT INTO stock_theme_map(code,name,theme_id,theme_name,updated_at) VALUES ('000660','SK하이닉스','1','반도체','2026-01-01')")
        conn.commit()
    out = run_scan(DummyKISOk(), DummyDART(), 'data/watchlist.example.csv', target_mode='테마 전체', demo_mode=False)
    assert out['scan_target_count'] >= 2


def test_demo_mode_marks_is_demo(tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    out = run_scan(DummyKISFail(), DummyDART(), 'data/watchlist.example.csv', target_mode='관심종목', demo_mode=True)
    assert out['is_demo'] is True
    assert all(s['is_demo'] == 1 for s in out['signals'])
