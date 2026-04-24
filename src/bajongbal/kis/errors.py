class KISError(Exception):
    """KIS 호출 공통 예외"""


class KISRateLimitError(KISError):
    """호출 제한 예외"""
