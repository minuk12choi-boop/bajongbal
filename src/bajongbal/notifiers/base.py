from __future__ import annotations


class BaseNotifier:
    def notify(self, message: str) -> None:
        raise NotImplementedError
