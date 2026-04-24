from fastapi.testclient import TestClient

from bajongbal.web.app import app


def test_routes():
    c = TestClient(app)
    assert c.get('/').status_code == 200
    assert c.get('/dashboard').status_code == 200
    assert c.get('/api/health').status_code == 200
    assert c.get('/api/themes/status').status_code == 200
    assert c.get('/api/themes/today').status_code == 200
    assert c.post('/api/scan', json={'score_threshold': 60, 'use_dart': False, 'max_symbols': 2}).status_code == 200
    assert c.get('/api/signals/recent').status_code == 200
