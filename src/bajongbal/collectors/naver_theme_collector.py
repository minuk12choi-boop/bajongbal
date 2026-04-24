from __future__ import annotations

import re
from typing import Any

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bajongbal.storage.db import get_conn, now_iso
from bajongbal.storage.models import ThemeRefreshResult


BASE_THEME_URL = 'https://finance.naver.com/sise/theme.naver?&page={page}'
DETAIL_URL = 'https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_id}'
HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://finance.naver.com/',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
}


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount('https://', HTTPAdapter(max_retries=retry))
    s.headers.update(HEADERS)
    return s


def fetch_theme_list_page(page: int) -> str:
    r = _session().get(BASE_THEME_URL.format(page=page), timeout=8)
    r.encoding = r.apparent_encoding or 'euc-kr'
    r.raise_for_status()
    return r.text


def parse_theme_list_page(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, 'html.parser')
    rows = []
    for a in soup.select('table.type_1 a'):
        href = a.get('href', '')
        m = re.search(r'no=(\d+)', href)
        if not m:
            continue
        name = a.get_text(strip=True)
        if not name:
            continue
        rows.append({'theme_id': m.group(1), 'theme_name': name})
    uniq = {r['theme_id']: r for r in rows}
    return list(uniq.values())


def fetch_theme_detail(theme_id: str) -> str:
    r = _session().get(DETAIL_URL.format(theme_id=theme_id), timeout=8)
    r.encoding = r.apparent_encoding or 'euc-kr'
    r.raise_for_status()
    return r.text


def parse_theme_detail_page(html: str, theme_id: str, theme_name: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, 'html.parser')
    result = []

    def _num(text: str) -> float | None:
        raw = text.strip().replace(',', '')
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    for row in soup.select('table.type_5 tr'):
        a = row.select_one('a')
        if not a:
            continue
        href = a.get('href', '')
        m = re.search(r'code=(\d+)', href)
        if not m:
            continue
        tds = row.select('td')
        if not tds:
            continue
        result.append(
            {
                'theme_id': theme_id,
                'theme_name': theme_name,
                'code': m.group(1),
                'name': a.get_text(strip=True),
                'naver_price': _num(tds[1].get_text(strip=True)) if len(tds) > 1 else None,
                'naver_change_rate': _num(tds[3].get_text(strip=True)) if len(tds) > 3 else None,
                'naver_volume': _num(tds[4].get_text(strip=True)) if len(tds) > 4 else None,
            }
        )
    return result


def refresh_naver_themes() -> ThemeRefreshResult:
    try:
        all_themes: list[dict[str, str]] = []
        prev_ids: set[str] = set()
        page = 1
        while True:
            html = fetch_theme_list_page(page)
            themes = parse_theme_list_page(html)
            if not themes:
                break
            ids = {t['theme_id'] for t in themes}
            if ids == prev_ids:
                break
            prev_ids = ids
            all_themes.extend(themes)
            page += 1

        if not all_themes:
            return ThemeRefreshResult(False, 0, 0, '테마 목록이 비어 기존 캐시 유지', warning=True, used_cache=True, last_refreshed_at=now_iso())

        all_constituents: list[dict[str, Any]] = []
        for theme in all_themes:
            detail_html = fetch_theme_detail(theme['theme_id'])
            all_constituents.extend(parse_theme_detail_page(detail_html, theme['theme_id'], theme['theme_name']))

        with get_conn() as conn:
            cur = conn.execute(
                'INSERT INTO theme_snapshots(refreshed_at, success, message) VALUES (?, ?, ?)',
                (now_iso(), 1, 'OK'),
            )
            snapshot_id = cur.lastrowid
            conn.execute('DELETE FROM stock_theme_map')
            for c in all_constituents:
                conn.execute(
                    'INSERT INTO theme_constituents(snapshot_id, theme_id, theme_name, code, name, naver_price, naver_change_rate, naver_volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (snapshot_id, c['theme_id'], c['theme_name'], c['code'], c['name'], c['naver_price'], c['naver_change_rate'], c['naver_volume']),
                )
                conn.execute(
                    'INSERT INTO stock_theme_map(code, name, theme_id, theme_name, updated_at) VALUES (?, ?, ?, ?, ?)',
                    (c['code'], c['name'], c['theme_id'], c['theme_name'], now_iso()),
                )
            conn.commit()
        if len(all_constituents) == 0:
            return ThemeRefreshResult(False, len(all_themes), 0, '테마 상세 수집 0건 (HTML 구조 변경 가능성)', warning=True, used_cache=True, last_refreshed_at=now_iso())
        return ThemeRefreshResult(True, len(all_themes), len(all_constituents), '테마 갱신 완료', warning=False, used_cache=False, last_refreshed_at=now_iso())
    except Exception:
        return ThemeRefreshResult(False, 0, 0, '테마 데이터 갱신 실패 / 기존 캐시 사용 중 (HTML 구조 변경 가능성)', warning=True, used_cache=True, last_refreshed_at=now_iso())
