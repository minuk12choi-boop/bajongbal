from bajongbal.strategy.pattern_333 import detect_333_pattern, score_333_pattern


def _c(o, c, h=None, l=None, date='2026-01-01'):
    h = h or max(o, c)
    l = l or min(o, c)
    return {'open': o, 'close': c, 'high': h, 'low': l, 'date': date}


def test_detect_333_success():
    candles = [_c(10,11),_c(11,10),_c(10,11),_c(11,10),_c(10,11),_c(11,10),_c(10,11)]
    r = detect_333_pattern(candles)
    assert r['detected'] is True


def test_detect_333_fail_case():
    candles = [_c(10,11),_c(11,10),_c(10,11)]
    r = detect_333_pattern(candles)
    assert r['detected'] is False


def test_detect_333_grade():
    candles = [_c(10,12,h=12,l=9),_c(12,9,h=12,l=8),_c(9,10,h=10,l=9),_c(10,8,h=10,l=7),_c(8,9,h=9,l=8),_c(9,7,h=9,l=6),_c(7,8,h=8,l=7)]
    r = detect_333_pattern(candles)
    assert score_333_pattern(r) >= 3
