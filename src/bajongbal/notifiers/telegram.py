from __future__ import annotations

from bajongbal.notifiers.base import BaseNotifier


class TelegramNotifier(BaseNotifier):
    def notify(self, message: str) -> None:
        # TODO: 이번 구현에서는 실제 발송 제외
        return None
