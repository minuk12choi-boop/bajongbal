from bajongbal.market.theme_strength import calculate_theme_strength


def test_theme_strength():
    out = calculate_theme_strength([
        {'theme_name': 'A', 'name': 'x', 'score': 90, 'change_rate': 2, 'trading_value': 10, 'trading_value_ratio_20': 2},
        {'theme_name': 'A', 'name': 'y', 'score': 70, 'change_rate': -1, 'trading_value': 5, 'trading_value_ratio_20': 1},
    ])
    assert out[0]['theme_name'] == 'A'
