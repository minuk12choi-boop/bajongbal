from fastapi.testclient import TestClient

import bajongbal.web.app as web_app
from bajongbal.storage.db import get_conn, init_db


def test_recent_excludes_demo_by_default(tmp_path):
    from bajongbal.config import settings

    settings.db_path = tmp_path / 'db.sqlite3'
    init_db()
    with get_conn() as conn:
        conn.execute("INSERT INTO signals(detected_at,code,name,signal_type,signal_grade,score,is_demo) VALUES ('2026-01-01','111111','REAL','LONG_BOX_TRIGGER','A',80,0)")
        conn.execute("INSERT INTO signals(detected_at,code,name,signal_type,signal_grade,score,is_demo) VALUES ('2026-01-01','222222','DEMO','LONG_BOX_TRIGGER','A',80,1)")
        conn.commit()
    c = TestClient(web_app.app)
    body = c.get('/api/signals/recent').json()
    codes = [x['code'] for x in body['items']]
    assert '111111' in codes
    assert '222222' not in codes
