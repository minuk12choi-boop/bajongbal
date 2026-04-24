from __future__ import annotations

from statistics import mean, median


def run_backtest(signals: list[dict]) -> dict:
    if not signals:
        return {'count': 0}
    returns = [min(15.0, s.get('score', 0) / 12) - 2 for s in signals]
    return {
        'count': len(signals),
        'avg_return': round(mean(returns), 2),
        'median_return': round(median(returns), 2),
        'win_rate': round(sum(1 for r in returns if r > 0) / len(returns) * 100, 2),
        'hit_3pct': round(sum(1 for r in returns if r >= 3) / len(returns) * 100, 2),
        'hit_5pct': round(sum(1 for r in returns if r >= 5) / len(returns) * 100, 2),
        'stop_hit': round(sum(1 for r in returns if r <= -3) / len(returns) * 100, 2),
    }
