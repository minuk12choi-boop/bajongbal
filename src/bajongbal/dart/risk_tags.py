RISK_KEYWORDS = ["감사의견", "상장폐지", "관리종목", "불성실공시", "유상증자", "전환사채", "신주인수권부사채", "소송", "횡령", "배임", "영업정지"]
POSITIVE_KEYWORDS = ["단일판매", "공급계약", "자기주식취득", "신규시설투자", "수주", "실적"]


def score_title(title: str) -> tuple[list[str], float]:
    tags = [k for k in RISK_KEYWORDS if k in title]
    positives = [k for k in POSITIVE_KEYWORDS if k in title]
    delta = -min(5.0, len(tags) * 1.5) + min(5.0, len(positives) * 1.0)
    return tags + positives, delta
