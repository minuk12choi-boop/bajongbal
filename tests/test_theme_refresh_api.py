from fastapi.testclient import TestClient

import bajongbal.web.app as web_app
from bajongbal.storage.models import ThemeRefreshResult


def test_theme_refresh_zero_warning(monkeypatch, tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    monkeypatch.setattr(web_app, 'refresh_naver_themes', lambda: ThemeRefreshResult(True, 0, 0, '0건'))
    c = TestClient(web_app.app)
    res = c.post('/api/themes/refresh')
    assert res.status_code == 200
    body = res.json()
    assert body['ok'] is False or body['warning'] is True
