"""AWS connectors (SigV4 over plain HTTPS): S3 source/destination and SQS destination."""

import json
import os
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlencode

from integrator.auth import sigv4_headers
from integrator.connectors.base import Connector
from integrator.errors import ConfigError, ConnectorError


class _AwsConnector(Connector):
    SERVICE = ""

    def __init__(self, config, transport=None):
        super().__init__(config, transport)
        self.require("region")
        self.region = config["region"]
        self.access_key = config.get("access_key_id") or os.environ.get("AWS_ACCESS_KEY_ID")
        self.secret_key = config.get("secret_access_key") or os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.token = config.get("session_token") or os.environ.get("AWS_SESSION_TOKEN")
        if not (self.access_key and self.secret_key):
            raise ConfigError("AWS credentials missing: set access_key_id/secret_access_key "
                              "($env: refs) or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY")

    def _send(self, method, url, body=b"", headers=None, what="AWS call"):
        signed = sigv4_headers(method, url, region=self.region, service=self.SERVICE,
                               access_key=self.access_key, secret_key=self.secret_key,
                               body=body, headers=headers, session_token=self.token)
        resp = self.transport.request(method, url, signed, body or None)
        resp.raise_for_status(what)
        return resp


def _parse_records(text: str) -> list[dict]:
    text = text.strip()
    if not text:
        return []
    if text.startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


class S3(_AwsConnector):
    SERVICE = "s3"

    def __init__(self, config, transport=None):
        super().__init__(config, transport)
        self.require("bucket")

    def _url(self, key="", query=None):
        bucket, endpoint = self.config["bucket"], self.config.get("endpoint")
        if endpoint:  # LocalStack / MinIO: path-style
            base, path = endpoint.rstrip("/"), f"/{bucket}/{quote(key)}" if key else f"/{bucket}"
        else:
            base, path = f"https://{bucket}.s3.{self.region}.amazonaws.com", "/" + quote(key)
        return base + path + ("?" + urlencode(query) if query else "")

    def read(self, state):
        token = None
        while True:
            q = {"list-type": "2", "prefix": self.config.get("prefix", "")}
            if token:
                q["continuation-token"] = token
            root = ET.fromstring(self._send("GET", self._url(query=q), what="S3 list").body)
            ns = {"s": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
            pre = "s:" if ns else ""
            for el in root.findall(f"{pre}Contents/{pre}Key", ns):
                body = self._send("GET", self._url(el.text), what=f"S3 get {el.text}").text()
                yield from _parse_records(body)
            nxt = root.find(f"{pre}NextContinuationToken", ns)
            if nxt is None:
                return
            token = nxt.text

    def write_batch(self, records, ctx):
        key = self.config.get("key", "{run_id}-{batch}.jsonl").format(**ctx)
        body = "".join(json.dumps(r, default=str) + "\n" for r in records).encode()
        self._send("PUT", self._url(key), body, {"Content-Type": "application/x-ndjson"},
                   what=f"S3 put {key}")
        return []


class SQS(_AwsConnector):
    SERVICE = "sqs"

    def __init__(self, config, transport=None):
        super().__init__(config, transport)
        self.require("queue_url")

    def write_batch(self, records, ctx):
        failures = []
        for i, rec in enumerate(records):
            payload = {"QueueUrl": self.config["queue_url"], "MessageBody": json.dumps(rec, default=str)}
            if self.config["queue_url"].endswith(".fifo"):
                payload["MessageGroupId"] = self.config.get("group_id", "default")
                payload["MessageDeduplicationId"] = f"{ctx['run_id']}-{ctx['batch']}-{i}"
            try:
                self._send("POST", f"https://sqs.{self.region}.amazonaws.com/",
                           json.dumps(payload).encode(),
                           {"Content-Type": "application/x-amz-json-1.0",
                            "X-Amz-Target": "AmazonSQS.SendMessage"}, what="SQS SendMessage")
            except ConnectorError as exc:
                if exc.retryable:
                    raise
                failures.append((i, str(exc)))
        return failures
