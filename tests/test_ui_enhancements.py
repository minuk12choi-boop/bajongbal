from fastapi.testclient import TestClient

import bajongbal.web.app as web_app
from bajongbal.web.utils import format_number, format_to_10k, map_market
from bajongbal.storage.db import get_conn, init_db


def test_number_formatting_policy():
    assert format_number(1234567) == '1,234,567'
    assert format_to_10k(23363629500) == '2,336,362.95'


def test_market_mapping():
    assert map_market('J') == 'KOSPI'
    assert map_market('Q') == 'KOSDAQ'
    assert map_market('ETF') == 'ETF'


def test_types_route_and_suggest(tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    with get_conn() as conn:
        conn.execute("INSERT INTO stock_theme_map(code,name,theme_id,theme_name,updated_at) VALUES ('005930','삼성전자','64','2차전지','2026-01-01')")
        conn.commit()

    c = TestClient(web_app.app)
    assert c.get('/types').status_code == 200
    body = c.get('/api/suggest?q=전지&kind=theme').json()
    assert any('전지' in x for x in body['items'])


def test_theme_stocks_sort_failure_bottom_function_exists():
    html = (web_app.Path(web_app.__file__).parent / 'templates' / 'theme_stocks.html').read_text(encoding='utf-8')
    assert 'failRank' in html
    assert '↕' in html and '▲' in html and '▼' in html


def test_dashboard_chart_container_and_theme_rank_exists():
    html = (web_app.Path(web_app.__file__).parent / 'templates' / 'dashboard.html').read_text(encoding='utf-8')
    assert '가격 차트' in html
    assert 'themeRankRows' in html
