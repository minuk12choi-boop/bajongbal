from pathlib import Path

from fastapi.testclient import TestClient

import bajongbal.web.app as web_app
from bajongbal.config import settings


def test_routes(monkeypatch, tmp_path):
    # 새 DB(테이블 없음) 상태에서도 대시보드가 500이 나지 않아야 한다.
    settings.db_path = tmp_path / 'fresh.sqlite3'

    monkeypatch.setattr(
        web_app,
        'run_scan',
        lambda **kwargs: {
            'signals': [
                {
                    'name': '테스트',
                    'code': '000000',
                    'score': 80,
                    'signal_grade': 'A',
                    'signal_type': 'LONG_BOX_TRIGGER',
                }
            ],
            'theme_strengths': [],
        },
    )

    c = TestClient(web_app.app)
    assert c.get('/').status_code == 200
    assert c.get('/dashboard').status_code == 200
    assert c.get('/api/health').status_code == 200
    assert c.get('/api/themes/status').status_code == 200
    assert c.get('/api/themes/today').status_code == 200
    assert c.post('/api/scan', json={'score_threshold': 60, 'use_dart': False, 'max_symbols': 2}).status_code == 200
