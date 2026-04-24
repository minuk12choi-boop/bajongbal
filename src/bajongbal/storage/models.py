from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ThemeRefreshResult:
    success: bool
    theme_count: int
    stock_count: int
    message: str
    warning: bool = False
    used_cache: bool = False
    last_refreshed_at: str | None = None


@dataclass
class SignalRecord:
    code: str
    name: str
    score: float
    signal_grade: str
    signal_type: str
    fields: dict[str, Any]
