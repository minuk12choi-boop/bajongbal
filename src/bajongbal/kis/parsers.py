from __future__ import annotations


def safe_float(v, default=0.0) -> float:
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if s in {"", "-", "None", "null"}:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def safe_int(v, default=0) -> int:
    return int(safe_float(v, default))
