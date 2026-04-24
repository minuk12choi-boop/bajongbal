from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import requests

from bajongbal.config import settings


CACHE = Path('.dart_cache_corp_codes.json')


def load_corp_map() -> dict[str, str]:
    if not CACHE.exists():
        return {}
    try:
        return json.loads(CACHE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def save_corp_map(data: dict[str, str]) -> None:
    CACHE.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')


def download_corp_codes(api_key: str | None = None) -> dict[str, str]:
    key = api_key or settings.dart_api_key
    if not key:
        return {}
    try:
        url = 'https://opendart.fss.or.kr/api/corpCode.xml'
        res = requests.get(url, params={'crtfc_key': key}, timeout=15)
        res.raise_for_status()
        zf = zipfile.ZipFile(io.BytesIO(res.content))
        name = zf.namelist()[0]
        xml_data = zf.read(name)
        root = ET.fromstring(xml_data)
        mapping: dict[str, str] = {}
        for item in root.findall('list'):
            stock_code = (item.findtext('stock_code') or '').strip()
            corp_code = (item.findtext('corp_code') or '').strip()
            if stock_code and corp_code:
                mapping[stock_code] = corp_code
        if mapping:
            save_corp_map(mapping)
        return mapping
    except Exception:
        return load_corp_map()


def stock_to_corp_code(stock_code: str) -> str | None:
    data = load_corp_map()
    return data.get(stock_code)
