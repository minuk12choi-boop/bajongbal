from __future__ import annotations


class _Resp:
    def __init__(self, body):
        self.body = body
        self.status_code = 200

    def json(self):
        return self.body if isinstance(self.body, dict) else {'data': self.body}


class TestClient:
    def __init__(self, app):
        self.app = app
        for fn in app._startup:
            fn()

    def get(self, path: str):
        fn = self.app.routes.get(("GET", path))
        if not fn:
            return _Resp({'error': 'not found', 'status_code': 404})
        if 'request' in fn.__code__.co_varnames:
            return _Resp(fn(request=None))
        return _Resp(fn())

    def post(self, path: str, json=None):
        fn = self.app.routes.get(("POST", path))
        if not fn:
            return _Resp({'error': 'not found', 'status_code': 404})
        if fn.__code__.co_argcount:
            return _Resp(fn(json))
        return _Resp(fn())
