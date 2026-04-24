from bajongbal.kis.client import KISClient, KISStatus


def test_current_price_parse_with_alt_fields(monkeypatch):
    c = KISClient('https://example.com')
    monkeypatch.setattr(c, 'health_detail', lambda: type('X', (), {'status': KISStatus.OK})())
    monkeypatch.setattr(c, '_get', lambda *a, **k: type('R', (), {'status': KISStatus.OK, 'data': {'output1': {'cur_prc': '12,345', 'flu_rt': '1.2', 'acml_vol': '1,000'}}})())
    out = c.get_current_price('005930')
    assert out.status == KISStatus.OK
    assert out.data['price'] == 12345


def test_period_parse_output1(monkeypatch):
    c = KISClient('https://example.com')
    monkeypatch.setattr(c, 'health_detail', lambda: type('X', (), {'status': KISStatus.OK})())
    monkeypatch.setattr(c, '_get', lambda *a, **k: type('R', (), {'status': KISStatus.OK, 'data': {'output1': [{'date': '20260101', 'open': '1,000', 'high': '1,100', 'low': '900', 'close': '1,050', 'volume': '10'}]}})())
    out = c.get_period_ohlcv('005930')
    assert out.status == KISStatus.OK
    assert out.data[0]['close'] == 1050


def test_parse_failure_returns_summary(monkeypatch):
    c = KISClient('https://example.com')
    monkeypatch.setattr(c, 'health_detail', lambda: type('X', (), {'status': KISStatus.OK})())
    monkeypatch.setattr(c, '_get', lambda *a, **k: type('R', (), {'status': KISStatus.OK, 'data': {'foo': 'bar'}})())
    out = c.get_current_price('005930')
    assert out.status == KISStatus.PARSE_FAILED
    assert 'response_keys' in (out.diagnostics or {})
    assert 'token' not in str(out.diagnostics).lower()
