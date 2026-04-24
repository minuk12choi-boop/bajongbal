from fastapi.testclient import TestClient

import bajongbal.web.app as web_app


def test_routes(monkeypatch):
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
    assert c.get('/api/signals/recent').status_code == 200
