from pathlib import Path

from bajongbal.collectors.naver_theme_collector import parse_theme_detail_page, parse_theme_list_page


def test_parse_theme_list_page():
    html = Path('tests/fixtures/naver_theme_list.html').read_text(encoding='utf-8')
    rows = parse_theme_list_page(html)
    assert len(rows) == 2
    assert rows[0]['theme_id'] == '123'


def test_parse_theme_detail_page():
    html = Path('tests/fixtures/naver_theme_detail.html').read_text(encoding='utf-8')
    rows = parse_theme_detail_page(html, '100', '반도체')
    assert rows[0]['code'] == '005930'
    assert rows[1]['name'] == 'SK하이닉스'
