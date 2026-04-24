from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

from bajongbal.storage.db import get_conn, init_db, now_iso


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog='bajongbal')
    sub = p.add_subparsers(dest='command')

    sub.add_parser('init-db')
    sub.add_parser('refresh-themes')
    sub.add_parser('sync-dart')
    sub.add_parser('clear-demo-signals')
    sub.add_parser('watchlist-groups')
    sub.add_parser('themes')
    ts = sub.add_parser('theme-stocks')
    ts.add_argument('--theme-id')
    ts.add_argument('--theme-name')
    ts.add_argument('--limit', type=int, default=100)

    wlc = sub.add_parser('watchlist-create')
    wlc.add_argument('--name', required=True)
    wlc.add_argument('--description', default='')

    wld = sub.add_parser('watchlist-delete')
    wld.add_argument('--group-id', type=int, required=True)

    wla = sub.add_parser('watchlist-add')
    wla.add_argument('--group-id', type=int, required=True)
    wla.add_argument('--code', required=True)
    wla.add_argument('--name', default='')

    wlr = sub.add_parser('watchlist-remove')
    wlr.add_argument('--group-id', type=int, required=True)
    wlr.add_argument('--code', required=True)

    wli = sub.add_parser('watchlist-items')
    wli.add_argument('--group-id', type=int, required=True)

    bc = sub.add_parser('build-candidates')
    bc.add_argument('--date', required=True)
    bc.add_argument('--watchlist', default='data/watchlist.example.csv')
    bc.add_argument('--theme-map', default='data/theme_map.example.csv')
    bc.add_argument('--score-threshold', type=float, default=60)
    bc.add_argument('--output', default='outputs/daily_candidates_YYYYMMDD.csv')
    bc.add_argument('--use-dart', action='store_true')
    bc.add_argument('--no-dart', action='store_true')
    bc.add_argument('--max-symbols', type=int, default=50)
    bc.add_argument('--dry-run', action='store_true')
    bc.add_argument('--target-mode', default='관심종목')
    bc.add_argument('--demo-mode', action='store_true')
    bc.add_argument('--watchlist-group-id', type=int)
    bc.add_argument('--theme-id')
    bc.add_argument('--theme-name')
    bc.add_argument('--scope')

    sc = sub.add_parser('scan')
    sc.add_argument('--watchlist', default='data/watchlist.example.csv')
    sc.add_argument('--theme-map', default='data/theme_map.example.csv')
    sc.add_argument('--score-threshold', type=float, default=60)
    sc.add_argument('--interval-seconds', type=int, default=30)
    sc.add_argument('--once', action='store_true')
    sc.add_argument('--output', default='outputs/signals_YYYYMMDD.csv')
    sc.add_argument('--use-dart', action='store_true')
    sc.add_argument('--no-dart', action='store_true')
    sc.add_argument('--max-symbols', type=int, default=50)
    sc.add_argument('--dry-run', action='store_true')
    sc.add_argument('--target-mode', default='관심종목')
    sc.add_argument('--demo-mode', action='store_true')
    sc.add_argument('--watchlist-group-id', type=int)
    sc.add_argument('--theme-id')
    sc.add_argument('--theme-name')
    sc.add_argument('--scope')

    web = sub.add_parser('web')
    web.add_argument('--host', default='0.0.0.0')
    web.add_argument('--port', type=int, default=8000)

    bt = sub.add_parser('backtest')
    bt.add_argument('--from', dest='from_date', required=True)
    bt.add_argument('--to', dest='to_date', required=True)
    bt.add_argument('--output', default='outputs/backtest_result_YYYYMMDD.csv')

    rep = sub.add_parser('report')
    rep.add_argument('--date', required=True)
    rep.add_argument('--output', default='outputs/theme_strength_YYYYMMDD.csv')
    return p


def _run_scan(args):
    from bajongbal.config import settings
    from bajongbal.dart.client import DartClient
    from bajongbal.kis.client import KISClient
    from bajongbal.scanner.service import run_scan

    use_dart = False if getattr(args, 'no_dart', False) else True
    out = run_scan(
        KISClient(settings.kis_base_url),
        DartClient(),
        args.watchlist,
        args.score_threshold,
        use_dart,
        args.max_symbols,
        target_mode=args.target_mode,
        demo_mode=args.demo_mode,
        watchlist_group_id=getattr(args, 'watchlist_group_id', None),
        theme_id=getattr(args, 'theme_id', None),
        theme_name=getattr(args, 'theme_name', None),
        scope_mode=getattr(args, 'scope', None),
    )
    ymd = datetime.utcnow().strftime('%Y%m%d')
    path = Path(args.output.replace('YYYYMMDD', ymd))
    if not args.dry_run:
        _write_csv(path, out['signals'])
    print(json.dumps({'count': len(out['signals']), 'output': str(path), 'diagnostics': out.get('diagnostics', {})}, ensure_ascii=False))
    return out, path


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    init_db()

    if args.command == 'init-db':
        print('DB 초기화 완료')
        return 0

    if args.command == 'watchlist-groups':
        with get_conn() as conn:
            rows = [dict(r) for r in conn.execute('SELECT id,name,description,created_at,updated_at FROM watchlist_groups WHERE COALESCE(is_active,1)=1 ORDER BY id DESC').fetchall()]
        print(json.dumps(rows, ensure_ascii=False))
        return 0

    if args.command == 'watchlist-create':
        with get_conn() as conn:
            conn.execute('INSERT INTO watchlist_groups(name,description,created_at,updated_at,is_active) VALUES (?,?,?,?,1)', (args.name, args.description, now_iso(), now_iso()))
            conn.commit()
        print('관심종목 그룹 생성 완료')
        return 0

    if args.command == 'watchlist-delete':
        with get_conn() as conn:
            conn.execute('UPDATE watchlist_items SET is_active=0, updated_at=? WHERE group_id=?', (now_iso(), args.group_id))
            conn.execute('UPDATE watchlist_groups SET is_active=0, updated_at=? WHERE id=?', (now_iso(), args.group_id))
            conn.commit()
        print('관심종목 그룹 삭제 완료')
        return 0

    if args.command == 'watchlist-add':
        with get_conn() as conn:
            conn.execute(
                'INSERT OR REPLACE INTO watchlist_items(group_id,code,name,added_at,updated_at,is_active) VALUES (?,?,?,?,?,1)',
                (args.group_id, args.code, args.name, now_iso(), now_iso()),
            )
            conn.commit()
        print('관심종목 추가 완료')
        return 0

    if args.command == 'watchlist-remove':
        with get_conn() as conn:
            conn.execute('UPDATE watchlist_items SET is_active=0, updated_at=? WHERE group_id=? AND code=?', (now_iso(), args.group_id, args.code))
            conn.commit()
        print('관심종목 삭제 완료')
        return 0

    if args.command == 'watchlist-items':
        with get_conn() as conn:
            rows = [dict(r) for r in conn.execute('SELECT id,group_id,code,name,market,theme_names,memo,added_at,updated_at FROM watchlist_items WHERE group_id=? AND COALESCE(is_active,1)=1 ORDER BY id DESC', (args.group_id,)).fetchall()]
        print(json.dumps(rows, ensure_ascii=False))
        return 0


    if args.command == 'themes':
        from bajongbal.storage.db import list_themes
        print(json.dumps(list_themes(), ensure_ascii=False))
        return 0

    if args.command == 'theme-stocks':
        from bajongbal.storage.db import list_theme_stocks_filtered
        print(json.dumps(list_theme_stocks_filtered(theme_id=args.theme_id, theme_name=args.theme_name, limit=args.limit), ensure_ascii=False))
        return 0

    if args.command == 'refresh-themes':
        from bajongbal.collectors.naver_theme_collector import refresh_naver_themes

        print(refresh_naver_themes())
        return 0

    if args.command == 'sync-dart':
        print('DART 동기화 구조 준비 완료')
        return 0

    if args.command == 'clear-demo-signals':
        with get_conn() as conn:
            conn.execute('DELETE FROM signals WHERE COALESCE(is_demo,0)=1')
            conn.commit()
        print('데모 시그널 삭제 완료')
        return 0

    if args.command in {'build-candidates', 'scan'}:
        _run_scan(args)
        if args.command == 'scan' and not args.once:
            while True:
                time.sleep(args.interval_seconds)
                _run_scan(args)
        return 0

    if args.command == 'web':
        import uvicorn

        uvicorn.run('bajongbal.web.app:app', host=args.host, port=args.port, reload=False)
        return 0

    if args.command == 'backtest':
        from bajongbal.backtest.engine import run_backtest

        with get_conn() as conn:
            rows = [dict(r) for r in conn.execute('SELECT * FROM signals').fetchall()]
        res = run_backtest(rows)
        path = Path(args.output.replace('YYYYMMDD', datetime.utcnow().strftime('%Y%m%d')))
        _write_csv(path, [res])
        print(json.dumps(res, ensure_ascii=False))
        return 0

    if args.command == 'report':
        with get_conn() as conn:
            rows = [dict(r) for r in conn.execute('SELECT * FROM theme_strengths ORDER BY id DESC LIMIT 200').fetchall()]
        path = Path(args.output.replace('YYYYMMDD', args.date.replace('-', '')))
        _write_csv(path, rows)
        print(json.dumps({'count': len(rows), 'output': str(path)}, ensure_ascii=False))
        return 0

    build_parser().print_help()
    return 0
