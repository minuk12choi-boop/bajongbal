import bajongbal.collectors.naver_theme_collector as c


def test_refresh_fallback(monkeypatch):
    monkeypatch.setattr(c, 'fetch_theme_list_page', lambda page: (_ for _ in ()).throw(Exception('fail')))
    r = c.refresh_naver_themes()
    assert r.success is False
    assert '기존 캐시' in r.message
