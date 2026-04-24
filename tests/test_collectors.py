from bajongbal.collectors.naver_theme_collector import parse_theme_detail_page, parse_theme_list_page


def test_parse_theme_list_page():
    html = '''<table class="type_1"><tr><td><a href="/sise/theme_detail.naver?no=123">반도체</a></td></tr></table>'''
    rows = parse_theme_list_page(html)
    assert rows[0]['theme_id'] == '123'


def test_parse_theme_detail_page():
    html = '''<table class="type_5"><tr><td><a href="/item/main.naver?code=005930">삼성전자</a></td><td>70,000</td><td></td><td>1.2</td><td>123,456</td></tr></table>'''
    rows = parse_theme_detail_page(html, '100', '반도체')
    assert rows[0]['code'] == '005930'
