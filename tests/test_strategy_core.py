from bajongbal.strategy.boxes import detect_box
from bajongbal.strategy.intraday import analyze_intraday
from bajongbal.strategy.levels import detect_levels
from bajongbal.strategy.scoring import compute_score
from bajongbal.strategy.trade_plan import build_trade_plan


def test_levels_box_scoring_intraday_trade_plan():
    daily = [{'high': 10+i, 'low': 8+i*0.8} for i in range(30)]
    levels = detect_levels(daily, 20)
    assert levels['nearest_support'] <= 20 <= levels['nearest_resistance']
    box = detect_box(daily)
    assert box['box_high'] > box['box_low']
    mins = [{'dt': f'2026-01-01T09:{i:02d}:00', 'open': 10+i*0.01, 'high': 10+i*0.02, 'low': 10+i*0.005, 'close': 10+i*0.015, 'volume': 1000+i} for i in range(40)]
    intr = analyze_intraday(mins)
    assert intr['touch_count'] >= 0
    score = compute_score({'proximity': 10, 'touch_pressure': 10, 'volume_heat': 10, 'minute_pressure': 10, 'pattern_333': 5, 'upside_rr': 5, 'theme_sync': 5, 'dart_stability': 3, 'risk_penalty': -2})
    assert 0 <= score <= 100
    plan = build_trade_plan('테스트', 100, {**levels, 'trigger_price': 102, 'stop_price': 95}, intr, 1.2, 1.3, True)
    assert plan['target_3'] >= plan['target_1']
