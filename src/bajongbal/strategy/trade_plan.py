from __future__ import annotations


def build_trade_plan(name: str, current_price: float, levels: dict, intraday: dict, volume_ratio: float, tv_ratio: float, dart_safe: bool) -> dict:
    attack_buy = round((levels['trigger_price'] + current_price) / 2, 2)
    conservative_buy = round(levels['nearest_support'] * 1.005, 2)
    stop = round(min(levels['stop_price'], levels['nearest_support'] * 0.99), 2)
    t1 = round(levels['nearest_resistance'], 2)
    t2 = round((levels['nearest_resistance'] + levels['next_resistance']) / 2, 2)
    t3 = round(levels['next_resistance'], 2)
    summary = (
        f"{name}은 현재가 {current_price:.0f}원이 장기 기준가 {levels['trigger_price']:.0f}원에 접근했고, "
        f"{intraday.get('minute_interval', 5)}분봉 기준 {intraday.get('minute_window_start')}~{intraday.get('minute_window_end')} 구간에서 저점이 상승하는 흐름입니다. "
        f"당일 거래량은 20일 평균 대비 {volume_ratio:.2f}배, 거래대금은 {tv_ratio:.2f}배이며 "
        f"다음 저항선 {levels['next_resistance']:.0f}원까지 여유가 있습니다. "
        + ("최근 DART 악재성 공시는 감지되지 않았습니다." if dart_safe else "최근 DART 리스크 공시가 있어 주의가 필요합니다.")
    )
    return {
        'summary': summary,
        'aggressive_buy': attack_buy,
        'conservative_buy': conservative_buy,
        'stop_price': stop,
        'target_1': t1,
        'target_2': t2,
        'target_3': t3,
        'rationale': {
            't1': '가장 가까운 단기 저항선',
            't2': '직전 고점/중간 매물대',
            't3': '다음 장기 저항선',
            'stop': '기준 지지선 및 패턴 하단 이탈 기준',
        },
    }
