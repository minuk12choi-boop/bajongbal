from __future__ import annotations

import json
from urllib.request import Request, urlopen


class Response:
    def __init__(self, text: str, status: int = 200):
        self.text = text
        self.status_code = status
        self.encoding = 'utf-8'
        self.apparent_encoding = 'utf-8'

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f'http {self.status_code}')

    def json(self):
        return json.loads(self.text)


class Session:
    def __init__(self):
        self.headers = {}

    def mount(self, prefix, adapter):
        return None

    def get(self, url: str, timeout: int = 8):
        req = Request(url, headers=self.headers)
        with urlopen(req, timeout=timeout) as r:
            return Response(r.read().decode('utf-8', errors='ignore'), r.status)


def post(url: str, json=None, timeout: int = 8):
    data = b'{}'
    req = Request(url, data=data, method='POST')
    with urlopen(req, timeout=timeout) as r:
        return Response(r.read().decode('utf-8', errors='ignore'), r.status)
