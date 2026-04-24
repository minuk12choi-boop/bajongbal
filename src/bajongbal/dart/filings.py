from __future__ import annotations

from bajongbal.dart.risk_tags import score_title


def tag_filings(filings: list[dict]) -> list[dict]:
    out = []
    for f in filings:
        tags, delta = score_title(f.get('report_nm', ''))
        g = dict(f)
        g['risk_tags'] = tags
        g['score_delta'] = delta
        out.append(g)
    return out
