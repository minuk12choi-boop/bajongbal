from __future__ import annotations


class Request:
    pass


class FastAPI:
    def __init__(self, title: str = ""):
        self.title = title
        self.routes = {}
        self._startup = []

    def on_event(self, event: str):
        def deco(fn):
            if event == 'startup':
                self._startup.append(fn)
            return fn
        return deco

    def get(self, path: str, response_class=None):
        def deco(fn):
            self.routes[("GET", path)] = fn
            return fn
        return deco

    def post(self, path: str):
        def deco(fn):
            self.routes[("POST", path)] = fn
            return fn
        return deco
