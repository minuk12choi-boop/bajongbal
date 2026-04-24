from bajongbal.dart.risk_tags import score_title
from bajongbal.kis.parsers import safe_float


def test_dart_risk_tag():
    tags, delta = score_title('상장폐지 및 감사의견 관련 공시')
    assert '상장폐지' in tags and delta < 0


def test_kis_safe_parse():
    assert safe_float('1,234.5') == 1234.5
    assert safe_float('') == 0.0
    assert safe_float(None) == 0.0
