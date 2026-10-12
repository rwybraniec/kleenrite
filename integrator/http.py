"""Minimal HTTP transport so connectors can be tested without the network."""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from integrator.errors import ConnectorError

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


@dataclass
class Response:
    status: int
    body: bytes = b""
    headers: dict = field(default_factory=dict)

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.body) if self.body else None

    def raise_for_status(self, what: str) -> None:
        if self.status >= 400:
            raise ConnectorError(
                f"{what} failed: HTTP {self.status}: {self.text()[:500]}",
                retryable=self.status in RETRYABLE_STATUS,
            )


class Transport:
    """Interface: ``request(method, url, headers, body, timeout) -> Response``."""

    def request(self, method, url, headers=None, body=None, timeout=30) -> Response:
        raise NotImplementedError


class UrllibTransport(Transport):
    def request(self, method, url, headers=None, body=None, timeout=30) -> Response:
        req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return Response(resp.status, resp.read(), dict(resp.headers))
        except urllib.error.HTTPError as exc:
            return Response(exc.code, exc.read(), dict(exc.headers))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ConnectorError(f"network error calling {url}: {exc}", retryable=True) from exc
