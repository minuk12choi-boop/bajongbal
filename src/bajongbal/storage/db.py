from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterable

from bajongbal.config import settings


SCHEMA = [
    '''CREATE TABLE IF NOT EXISTS stocks (code TEXT PRIMARY KEY, name TEXT, market TEXT, updated_at TEXT)''',
    '''CREATE TABLE IF NOT EXISTS theme_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, refreshed_at TEXT, success INTEGER, message TEXT)''',
    '''CREATE TABLE IF NOT EXISTS theme_constituents (id INTEGER PRIMARY KEY AUTOINCREMENT, snapshot_id INTEGER, theme_id TEXT, theme_name TEXT, code TEXT, name TEXT, naver_price REAL, naver_change_rate REAL, naver_volume REAL)''',
    '''CREATE TABLE IF NOT EXISTS stock_theme_map (code TEXT, name TEXT, theme_id TEXT, theme_name TEXT, updated_at TEXT)''',
    '''CREATE TABLE IF NOT EXISTS theme_strengths (id INTEGER PRIMARY KEY AUTOINCREMENT, as_of TEXT, theme_name TEXT, total_stock_count INTEGER, up_count INTEGER, flat_count INTEGER, down_count INTEGER, up_ratio REAL, avg_change_rate REAL, median_change_rate REAL, total_trading_value REAL, avg_trading_value_ratio_20 REAL, strong_signal_count INTEGER, leader_candidates TEXT, theme_strength_score REAL)''',
    '''CREATE TABLE IF NOT EXISTS price_daily (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL, trading_value REAL, timeframe TEXT)''',
    '''CREATE TABLE IF NOT EXISTS price_minute (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, dt TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL, trading_value REAL, interval_min INTEGER)''',
    '''CREATE TABLE IF NOT EXISTS levels (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, detected_at TEXT, nearest_support REAL, nearest_resistance REAL, next_resistance REAL, trigger_price REAL, stop_price REAL, level_source TEXT, box_high REAL, box_low REAL, box_mid REAL, box_width_pct REAL)''',
    '''CREATE TABLE IF NOT EXISTS signals (id INTEGER PRIMARY KEY AUTOINCREMENT, detected_at TEXT, code TEXT, name TEXT, theme_names TEXT, signal_type TEXT, signal_grade TEXT, score REAL, current_price REAL, trigger_price REAL, nearest_support REAL, nearest_resistance REAL, next_resistance REAL, stop_price REAL, volume_ratio REAL, trading_value_ratio REAL, time_adjusted_volume_ratio REAL, touch_count INTEGER, minute_interval INTEGER, minute_window_start TEXT, minute_window_end TEXT, minute_lows_json TEXT, minute_highs_json TEXT, minute_trend TEXT, vwap REAL, is_above_vwap INTEGER, theme_score REAL, dart_score REAL, risk_score REAL, has_333_pattern INTEGER, pattern_333_timeframe TEXT, pattern_333_grade TEXT, score_333 REAL, reason_json TEXT, trade_plan_json TEXT, is_demo INTEGER DEFAULT 0)''',
    '''CREATE TABLE IF NOT EXISTS pattern_333 (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, name TEXT, timeframe TEXT, detected_at TEXT, pattern_start_date TEXT, pattern_end_date TEXT, pattern_sequence TEXT, pattern_grade TEXT, down_group_count INTEGER, up_group_count INTEGER, down_group_1_start TEXT, down_group_1_end TEXT, down_group_2_start TEXT, down_group_2_end TEXT, down_group_3_start TEXT, down_group_3_end TEXT, last_up_group_start TEXT, last_up_group_end TEXT, pattern_high REAL, pattern_low REAL, correction_pct REAL, last_up_volume_ratio REAL, next_resistance REAL, upside_room_pct REAL, stop_price REAL, score_333 REAL, reason_json TEXT)''',
    '''CREATE TABLE IF NOT EXISTS dart_filings (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, corp_code TEXT, rcept_dt TEXT, report_nm TEXT, risk_tags TEXT, score_delta REAL, raw_json TEXT)''',
    '''CREATE TABLE IF NOT EXISTS watchlist_groups (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, is_active INTEGER DEFAULT 1)''',
    '''CREATE TABLE IF NOT EXISTS watchlist_items (id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER NOT NULL, code TEXT NOT NULL, name TEXT, market TEXT, theme_names TEXT, memo TEXT, added_at TEXT NOT NULL, updated_at TEXT NOT NULL, is_active INTEGER DEFAULT 1, UNIQUE(group_id, code))''',
]


@contextmanager
def get_conn():
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        for q in SCHEMA:
            conn.execute(q)
        cols = [r[1] for r in conn.execute('PRAGMA table_info(signals)').fetchall()]
        if 'is_demo' not in cols:
            conn.execute('ALTER TABLE signals ADD COLUMN is_demo INTEGER DEFAULT 0')
        conn.commit()


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec='seconds')


def insert_many(query: str, rows: Iterable[tuple]) -> None:
    with get_conn() as conn:
        conn.executemany(query, rows)
        conn.commit()


def list_theme_filters() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT theme_id, theme_name, COUNT(DISTINCT code) AS stock_count, MAX(updated_at) AS last_refreshed_at
            FROM stock_theme_map
            WHERE COALESCE(theme_name,'') != ''
            GROUP BY theme_id, theme_name
            ORDER BY theme_name ASC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def list_theme_stocks(theme_id: str | None = None, theme_name: str | None = None) -> list[dict]:
    sql = 'SELECT code, MAX(name) AS name, MAX(theme_id) AS theme_id, MAX(theme_name) AS theme_name FROM stock_theme_map WHERE 1=1'
    params: list[str] = []
    if theme_id:
        sql += ' AND theme_id = ?'
        params.append(theme_id)
    if theme_name:
        sql += ' AND theme_name = ?'
        params.append(theme_name)
    sql += ' GROUP BY code ORDER BY code ASC'
    with get_conn() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def list_themes() -> list[dict]:
    return list_theme_filters()


def list_theme_stocks_filtered(theme_id: str | None = None, theme_name: str | None = None, code: str | None = None, name: str | None = None, limit: int | None = None) -> list[dict]:
    sql = 'SELECT code, MAX(name) AS name, MAX(theme_id) AS theme_id, MAX(theme_name) AS theme_name, MAX(updated_at) AS updated_at FROM stock_theme_map WHERE 1=1'
    params: list[str] = []
    if theme_id:
        sql += ' AND theme_id = ?'
        params.append(theme_id)
    if theme_name:
        sql += ' AND theme_name LIKE ?'
        params.append(f'%{theme_name}%')
    if code:
        sql += ' AND code LIKE ?'
        params.append(f'%{code}%')
    if name:
        sql += ' AND name LIKE ?'
        params.append(f'%{name}%')
    sql += ' GROUP BY code ORDER BY code ASC'
    if limit:
        sql += ' LIMIT ?'
        params.append(str(limit))
    with get_conn() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def list_watchlist_groups() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute('SELECT id,name,description,created_at,updated_at FROM watchlist_groups WHERE COALESCE(is_active,1)=1 ORDER BY id DESC').fetchall()
    return [dict(r) for r in rows]


def list_watchlist_items(group_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute('SELECT id,group_id,code,name,market,theme_names,memo,added_at,updated_at FROM watchlist_items WHERE group_id=? AND COALESCE(is_active,1)=1 ORDER BY id DESC', (group_id,)).fetchall()
    return [dict(r) for r in rows]


def add_watchlist_item(group_id: int, code: str, name: str | None, market: str | None = None, theme_names: str | None = None, memo: str | None = None) -> dict | None:
    now = now_iso()
    with get_conn() as conn:
        conn.execute('INSERT OR IGNORE INTO watchlist_items(group_id,code,name,market,theme_names,memo,added_at,updated_at,is_active) VALUES (?,?,?,?,?,?,?,?,1)', (group_id, str(code), name, market, theme_names, memo, now, now))
        conn.execute('UPDATE watchlist_items SET is_active=1, name=COALESCE(?,name), market=COALESCE(?,market), theme_names=COALESCE(?,theme_names), memo=COALESCE(?,memo), updated_at=? WHERE group_id=? AND code=?', (name, market, theme_names, memo, now, group_id, str(code)))
        conn.commit()
        row = conn.execute('SELECT id,group_id,code,name,market,theme_names,memo,added_at,updated_at FROM watchlist_items WHERE group_id=? AND code=? AND COALESCE(is_active,1)=1', (group_id, str(code))).fetchone()
    return dict(row) if row else None


def remove_watchlist_item(group_id: int, item_id: int | None = None, code: str | None = None) -> int:
    with get_conn() as conn:
        if item_id is not None:
            cur = conn.execute('UPDATE watchlist_items SET is_active=0, updated_at=? WHERE id=? AND group_id=?', (now_iso(), item_id, group_id))
        else:
            cur = conn.execute('UPDATE watchlist_items SET is_active=0, updated_at=? WHERE code=? AND group_id=?', (now_iso(), str(code), group_id))
        conn.commit()
        return cur.rowcount


def get_watchlist_membership(code: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT g.id AS group_id, g.name AS group_name, i.id AS item_id, i.added_at FROM watchlist_items i JOIN watchlist_groups g ON g.id = i.group_id WHERE i.code=? AND COALESCE(i.is_active,1)=1 AND COALESCE(g.is_active,1)=1 ORDER BY g.id',
            (str(code),),
        ).fetchall()
    return [dict(r) for r in rows]
