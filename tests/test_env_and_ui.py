from importlib import reload

from fastapi.testclient import TestClient

import bajongbal.config as config_module
import bajongbal.web.app as web_app


def test_config_status_has_env_diagnostics(tmp_path, monkeypatch):
    env = tmp_path / '.env'
    env.write_text('KIS_APP_KEY = abc\nINVALID LINE\nDART_API_KEY=\n', encoding='utf-8')
    monkeypatch.setenv('BAJONGBAL_ENV_FILE', str(env))
    monkeypatch.delenv('KIS_APP_KEY', raising=False)
    monkeypatch.delenv('DART_API_KEY', raising=False)
    reload(config_module)

    c = TestClient(web_app.app)
    body = c.get('/api/config/status').json()
    assert body['env_file_exists'] is True
    assert body['env_file_loaded'] is True
    assert body['invalid_env_line_count'] >= 1
    assert body['KIS_APP_KEY'] == 'Y'
    assert body['DART_API_KEY'] == 'N'
    assert 'abc' not in str(body)


def test_env_missing_does_not_crash(tmp_path, monkeypatch):
    missing = tmp_path / 'missing.env'
    monkeypatch.setenv('BAJONGBAL_ENV_FILE', str(missing))
    reload(config_module)
    c = TestClient(web_app.app)
    assert c.get('/api/health').status_code == 200


def test_dashboard_has_loading_overlay_and_helpers():
    html = (web_app.Path(web_app.__file__).parent / 'templates' / 'dashboard.html').read_text(encoding='utf-8')
    assert 'loadingOverlay' in html
    assert 'showLoading' in html and 'hideLoading' in html
    assert 'apiFetchWithLoading' in html
    assert '네이버증권 테마를 수집 중입니다' in html
    assert 'KIS 시세와 바종발식 시그널을 계산 중입니다' in html
    assert '관심종목 그룹을 생성 중입니다' in html
