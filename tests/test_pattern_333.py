from bajongbal.strategy.pattern_333 import detect_333_pattern, score_333_pattern


def _c(o, c, h=None, l=None, date='2026-01-01'):
    h = h or max(o, c)
    l = l or min(o, c)
    return {'open': o, 'close': c, 'high': h, 'low': l, 'date': date}


def test_detect_333_success():
    candles = [_c(10, 11), _c(11, 10), _c(10, 11), _c(11, 10), _c(10, 11), _c(11, 10), _c(10, 11)]
    r = detect_333_pattern(candles)
    assert r['detected'] is True


def test_first_group_d_fail():
    candles = [_c(11, 10), _c(10, 11), _c(11, 10), _c(10, 11), _c(11, 10), _c(10, 11), _c(11, 12)]
    assert detect_333_pattern(candles)['detected'] is False


def test_last_group_d_fail():
    candles = [_c(10, 11), _c(11, 10), _c(10, 11), _c(11, 10), _c(10, 11), _c(11, 10), _c(10, 9)]
    assert detect_333_pattern(candles)['detected'] is False


def test_down_group_2_fail():
    candles = [_c(10, 11), _c(11, 10), _c(10, 11), _c(11, 10), _c(10, 11)]
    assert detect_333_pattern(candles)['detected'] is False


def test_down_group_4_fail():
    candles = [_c(10, 11), _c(11, 10), _c(10, 11), _c(11, 10), _c(10, 11), _c(11, 10), _c(10, 11), _c(11, 10), _c(10, 11)]
    assert detect_333_pattern(candles)['detected'] is False


def test_weak_normal_strong_grade():
    weak = [_c(10, 10.1, h=10.2, l=9.9), _c(10.1, 10, h=10.1, l=9.95), _c(10, 10.1), _c(10.1, 10), _c(10, 10.1), _c(10.1, 10), _c(10, 10.1)]
    normal = [_c(10, 11), _c(11, 10), _c(10, 11), _c(11, 10), _c(10, 11), _c(11, 10), _c(10, 11)]
    strong = [_c(10, 12, h=12, l=9), _c(12, 9, h=12, l=8), _c(9, 10), _c(10, 8), _c(8, 9), _c(9, 7), _c(7, 9.5)]
    rw = detect_333_pattern(weak)
    rn = detect_333_pattern(normal)
    rs = detect_333_pattern(strong)
    assert rw['grade'] in {'WEAK_333', 'NORMAL_333'}
    assert rn['grade'] in {'NORMAL_333', 'WEAK_333'}
    assert rs['grade'] == 'STRONG_333'
    assert score_333_pattern(rs) >= score_333_pattern(rn)
