from __future__ import annotations

from pathlib import Path
import json

CACHE = Path('.dart_cache_corp_codes.json')


def load_corp_map() -> dict[str, str]:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}


def save_corp_map(data: dict[str, str]) -> None:
    CACHE.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
