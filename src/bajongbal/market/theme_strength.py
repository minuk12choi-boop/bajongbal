from __future__ import annotations

from collections import defaultdict
from statistics import median


def calculate_theme_strength(rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["theme_name"]].append(r)

    result = []
    for theme, items in grouped.items():
        total = len(items)
        up = sum(1 for x in items if x.get("change_rate", 0) > 0)
        flat = sum(1 for x in items if x.get("change_rate", 0) == 0)
        down = total - up - flat
        up_ratio = up / total if total else 0
        avg_change = sum(x.get("change_rate", 0) for x in items) / total if total else 0
        med_change = median([x.get("change_rate", 0) for x in items]) if total else 0
        total_tv = sum(x.get("trading_value", 0) for x in items)
        avg_tv_ratio = sum(x.get("trading_value_ratio_20", 0) for x in items) / total if total else 0
        strong = sum(1 for x in items if x.get("score", 0) >= 80)
        leaders = sorted(items, key=lambda x: x.get("score", 0), reverse=True)[:3]

        score = (
            min(30, up_ratio * 30)
            + max(0, min(20, (avg_change + 5) * 2))
            + min(25, avg_tv_ratio * 8)
            + min(15, strong * 3)
            + (10 if leaders else 0)
        )
        result.append(
            {
                "theme_name": theme,
                "total_stock_count": total,
                "up_count": up,
                "flat_count": flat,
                "down_count": down,
                "up_ratio": up_ratio,
                "avg_change_rate": avg_change,
                "median_change_rate": med_change,
                "total_trading_value": total_tv,
                "avg_trading_value_ratio_20": avg_tv_ratio,
                "strong_signal_count": strong,
                "leader_candidates": [l["name"] for l in leaders],
                "theme_strength_score": round(score, 2),
            }
        )
    return sorted(result, key=lambda x: x["theme_strength_score"], reverse=True)
