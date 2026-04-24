from fastapi.testclient import TestClient

import bajongbal.web.app as web_app
from bajongbal.config import settings


def test_routes(monkeypatch, tmp_path):
    settings.db_path = tmp_path / 'fresh.sqlite3'

    monkeypatch.setattr(
        web_app,
        'run_scan',
        lambda **kwargs: {
            'signals': [],
            'theme_strengths': [],
            'warnings': ['KIS 연결 실패로 실시간 시세 조회 불가'],
            'errors': [],
            'scan_target_count': 3,
            'scan_success_count': 0,
            'scan_fail_count': 3,
            'is_demo': False,
        },
    )

    c = TestClient(web_app.app)
    assert c.get('/').status_code == 200
    assert c.get('/dashboard').status_code == 200
    assert c.get('/api/health').status_code == 200
    assert c.get('/api/themes/status').status_code == 200
    assert c.get('/api/config/status').status_code == 200
    r = c.post('/api/scan', json={'score_threshold': 60, 'use_dart': False, 'max_symbols': 2, 'demo_mode': False})
    assert r.status_code == 200
    assert r.json()['signals'] == []
