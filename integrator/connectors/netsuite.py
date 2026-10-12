"""NetSuite connector: SuiteQL source and REST record-API destination (token-based auth)."""

import json
import re
from urllib.parse import quote, urlencode

from integrator.auth import oauth1_header
from integrator.connectors.base import Connector
from integrator.errors import ConfigError, ConnectorError

_SINCE = re.compile(r"\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}:\d{2})?")
EPOCH = "1970-01-01 00:00:00"
PAGE_SIZE = 1000


class NetSuite(Connector):
    CRED_KEYS = ("account", "consumer_key", "consumer_secret", "token_id", "token_secret")

    def __init__(self, config, transport=None):
        super().__init__(config, transport)
        self.require(*self.CRED_KEYS)

    @property
    def base_url(self) -> str:
        host = self.config["account"].lower().replace("_", "-")
        return f"https://{host}.suitetalk.api.netsuite.com/services/rest"

    def _call(self, method, url, body=None, extra=None):
        headers = {
            "Authorization": oauth1_header(
                method, url, account=self.config["account"],
                consumer_key=self.config["consumer_key"], consumer_secret=self.config["consumer_secret"],
                token_id=self.config["token_id"], token_secret=self.config["token_secret"]),
            "Content-Type": "application/json",
            "Accept": "application/json",
            **(extra or {}),
        }
        data = json.dumps(body).encode() if body is not None else None
        resp = self.transport.request(method, url, headers, data)
        resp.raise_for_status(f"NetSuite {method} {url.split('?')[0]}")
        return resp

    def _query(self, state: dict) -> str:
        sql = self.config.get("query")
        if not sql:
            raise ConfigError("netsuite source needs a 'query' (SuiteQL)")
        if "{since}" in sql:
            since = state.get("watermark") or EPOCH
            if not _SINCE.fullmatch(since):
                raise ConfigError(f"watermark {since!r} is not a date; cannot substitute into query")
            sql = sql.replace("{since}", since)
        return sql

    def read(self, state):
        sql, offset = self._query(state), 0
        while True:
            url = f"{self.base_url}/query/v1/suiteql?" + urlencode({"limit": PAGE_SIZE, "offset": offset})
            data = self._call("POST", url, {"q": sql}, {"Prefer": "transient"}).json() or {}
            yield from data.get("items", [])
            if not data.get("hasMore"):
                return
            offset += PAGE_SIZE

    def write_batch(self, records, ctx):
        self.require("record_type")
        rtype, id_field = self.config["record_type"], self.config.get("external_id_field")
        failures = []
        for i, rec in enumerate(records):
            try:
                if id_field:  # idempotent upsert keyed on external id
                    eid = quote(str(rec[id_field]), safe="")
                    self._call("PUT", f"{self.base_url}/record/v1/{rtype}/eid:{eid}", rec)
                else:
                    self._call("POST", f"{self.base_url}/record/v1/{rtype}", rec)
            except KeyError:
                failures.append((i, f"record has no '{id_field}' for external id"))
            except ConnectorError as exc:
                if exc.retryable:
                    raise
                failures.append((i, str(exc)))
        return failures
