from fastapi.testclient import TestClient

import bajongbal.web.app as web_app
from bajongbal.storage.db import get_conn, init_db


class DummyKISFail:
    def health_detail(self):
        class X:
            status = 'CONFIG_MISSING'
            message = 'KIS 환경변수가 누락되었습니다.'
        return X()

    def get_current_price(self, code):
        class X:
            status = 'API_FAILED'
            message = '실패'
            diagnostics = None
        return X()


def test_theme_stocks_page_and_modal_exists(tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    c = TestClient(web_app.app)
    assert c.get('/theme-stocks').status_code == 200
    html = c.get('/dashboard').text
    assert 'starModal' in html
    assert '조회 범위' in html
    assert 'demoMode' not in html


def test_theme_refresh_updates_status(monkeypatch, tmp_path):
    from bajongbal.config import settings
    from bajongbal.storage.models import ThemeRefreshResult

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    monkeypatch.setattr(web_app, 'refresh_naver_themes', lambda: ThemeRefreshResult(True, 1, 1, 'OK', last_refreshed_at='2026-04-24T15:13:39'))
    c = TestClient(web_app.app)
    c.post('/api/themes/refresh')
    status = c.get('/api/themes/status').json()
    assert '테마 캐시 없음' not in status['theme_message'] or status['theme_updated_at'] != '테마 캐시 없음'


def test_api_theme_stocks_filters(tmp_path, monkeypatch):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    with get_conn() as conn:
        conn.execute("INSERT INTO stock_theme_map(code,name,theme_id,theme_name,updated_at) VALUES ('005930','삼성전자','64','2차전지','2026-01-01')")
        conn.execute("INSERT INTO stock_theme_map(code,name,theme_id,theme_name,updated_at) VALUES ('000660','SK하이닉스','64','2차전지','2026-01-01')")
        conn.commit()

    monkeypatch.setattr(web_app, 'KISClient', lambda *_: DummyKISFail())
    c = TestClient(web_app.app)
    body = c.get('/api/theme-stocks?theme_id=64&code=0059').json()
    assert any(x['code'] == '005930' for x in body['items'])
