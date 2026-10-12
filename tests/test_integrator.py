"""Tests for the integrator package. No network: a FakeTransport records and answers requests."""

import datetime as dt
import json
import os
import tempfile
import unittest

from integrator.auth import oauth1_header, sigv4_headers
from integrator.cli import main as cli_main
from integrator.config import resolve_env, validate_flow
from integrator.connectors import build
from integrator.errors import ConfigError, ConnectorError, MappingError
from integrator.http import Response, Transport
from integrator.mapping import map_record, validate_mapping
from integrator.runner import run_flow
from integrator.store import Store


class FakeTransport(Transport):
    """Answers with queued responses (or a handler function) and records every call."""

    def __init__(self, handler=None, responses=None):
        self.calls, self.handler, self.responses = [], handler, list(responses or [])

    def request(self, method, url, headers=None, body=None, timeout=30):
        self.calls.append({"method": method, "url": url, "headers": headers or {}, "body": body})
        if self.handler:
            return self.handler(method, url, headers, body)
        return self.responses.pop(0) if self.responses else Response(204)


NS = {"type": "netsuite", "account": "1234567_SB1", "consumer_key": "ck", "consumer_secret": "cs",
      "token_id": "ti", "token_secret": "ts"}
AWS = {"region": "us-east-1", "access_key_id": "AKID", "secret_access_key": "SECRET"}


class SigningTests(unittest.TestCase):
    def test_sigv4_matches_aws_published_vector(self):
        # AWS Signature V4 test suite, "get-vanilla".
        h = sigv4_headers("GET", "https://example.amazonaws.com/", region="us-east-1", service="service",
                          access_key="AKIDEXAMPLE", secret_key="wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY",
                          now=dt.datetime(2015, 8, 30, 12, 36, 0, tzinfo=dt.timezone.utc))
        self.assertIn("Signature=5fa00fa31553b73ebf1942676e86291e8372ff2a2260956d9b8aae1d763fbf31",
                      h["authorization"])
        self.assertIn("SignedHeaders=host;x-amz-date", h["authorization"])

    def test_sigv4_s3_includes_payload_hash_header(self):
        h = sigv4_headers("PUT", "https://b.s3.us-east-1.amazonaws.com/k", region="us-east-1", service="s3",
                          access_key="a", secret_key="b", body=b"hi")
        self.assertEqual(h["x-amz-content-sha256"],
                         "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4")

    def test_oauth1_header_shape_and_determinism(self):
        kw = dict(account="1234567_SB1", consumer_key="ck", consumer_secret="cs", token_id="ti",
                  token_secret="ts", timestamp=1700000000, nonce="abc")
        a = oauth1_header("POST", "https://x.com/p?limit=1&offset=0", **kw)
        self.assertEqual(a, oauth1_header("POST", "https://x.com/p?limit=1&offset=0", **kw))
        self.assertNotEqual(a, oauth1_header("POST", "https://x.com/p?limit=1&offset=1", **kw))
        self.assertTrue(a.startswith('OAuth realm="1234567_SB1"'))
        self.assertIn('oauth_signature_method="HMAC-SHA256"', a)


class MappingTests(unittest.TestCase):
    def test_paths_transforms_const_default(self):
        m = {"fields": {"a.b": {"from": "x.0.y", "transform": ["strip", "upper"]},
                        "c": {"const": 1}, "d": {"from": "nope", "default": "z"}, "e": "n"}}
        self.assertEqual(map_record({"x": [{"y": " hi "}], "n": 5}, m),
                         {"a": {"b": "HI"}, "c": 1, "d": "z", "e": 5})

    def test_required_missing_raises(self):
        with self.assertRaises(MappingError):
            map_record({}, {"fields": {"a": {"from": "x", "required": True}}})

    def test_bad_transform_value_raises(self):
        with self.assertRaises(MappingError):
            map_record({"x": "abc"}, {"fields": {"a": {"from": "x", "transform": "int"}}})

    def test_passthrough_and_validation(self):
        self.assertEqual(map_record({"a": 1}, {"fields": None}), {"a": 1})
        with self.assertRaises(ConfigError):
            validate_mapping({"fields": {"a": {"from": "x", "transform": "nope"}}})


class ConfigTests(unittest.TestCase):
    def test_env_resolution(self):
        self.assertEqual(resolve_env({"k": ["$env:A", "plain"]}, {"A": "v"}), {"k": ["v", "plain"]})
        with self.assertRaises(ConfigError):
            resolve_env("$env:MISSING", {})

    def test_validate_flow(self):
        with self.assertRaises(ConfigError):
            validate_flow({"name": "x"})
        with self.assertRaises(ConfigError):
            validate_flow({"name": "bad name!", "source": {"type": "a"}, "destination": {"type": "b"}})


class ConnectorTests(unittest.TestCase):
    def test_netsuite_suiteql_paginates_and_signs(self):
        pages = [Response(200, json.dumps({"items": [{"id": "1"}], "hasMore": True}).encode()),
                 Response(200, json.dumps({"items": [{"id": "2"}], "hasMore": False}).encode())]
        t = FakeTransport(responses=pages)
        ns = build({**NS, "query": "SELECT id FROM customer"}, t)
        self.assertEqual([r["id"] for r in ns.read({})], ["1", "2"])
        self.assertIn("1234567-sb1.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql", t.calls[0]["url"])
        self.assertIn("offset=1000", t.calls[1]["url"])
        self.assertEqual(t.calls[0]["headers"]["Prefer"], "transient")
        self.assertTrue(t.calls[0]["headers"]["Authorization"].startswith("OAuth realm="))

    def test_netsuite_since_placeholder_is_validated(self):
        ns = build({**NS, "query": "x > '{since}'"}, FakeTransport())
        self.assertEqual(ns._query({"watermark": "2024-01-02 03:04:05"}), "x > '2024-01-02 03:04:05'")
        with self.assertRaises(ConfigError):
            ns._query({"watermark": "'; DROP TABLE x; --"})

    def test_netsuite_upsert_uses_external_id(self):
        t = FakeTransport()
        ns = build({**NS, "record_type": "customer", "external_id_field": "externalId"}, t)
        fails = ns.write_batch([{"externalId": "a/b"}, {"x": 1}], {})
        self.assertEqual(t.calls[0]["method"], "PUT")
        self.assertTrue(t.calls[0]["url"].endswith("/record/v1/customer/eid:a%2Fb"))
        self.assertEqual([i for i, _ in fails], [1])

    def test_netsuite_retryable_error_propagates(self):
        ns = build({**NS, "record_type": "customer"}, FakeTransport(responses=[Response(429, b"slow")]))
        with self.assertRaises(ConnectorError) as cm:
            ns.write_batch([{"a": 1}], {})
        self.assertTrue(cm.exception.retryable)

    def test_s3_write_and_read(self):
        t = FakeTransport()
        s3 = build({"type": "aws_s3", **AWS, "bucket": "bkt", "key": "k/{flow}-{batch}.jsonl"}, t)
        s3.write_batch([{"a": 1}, {"a": 2}], {"run_id": 1, "flow": "f", "batch": 3})
        c = t.calls[0]
        self.assertEqual((c["method"], c["url"]), ("PUT", "https://bkt.s3.us-east-1.amazonaws.com/k/f-3.jsonl"))
        self.assertEqual(c["body"], b'{"a": 1}\n{"a": 2}\n')
        self.assertIn("AWS4-HMAC-SHA256", c["headers"]["authorization"])

        listing = (b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                   b"<Contents><Key>in/a.jsonl</Key></Contents></ListBucketResult>")
        t2 = FakeTransport(responses=[Response(200, listing), Response(200, b'{"x":1}\n{"x":2}\n')])
        s3r = build({"type": "aws_s3", **AWS, "bucket": "bkt", "prefix": "in/"}, t2)
        self.assertEqual(list(s3r.read({})), [{"x": 1}, {"x": 2}])

    def test_sqs_send(self):
        t = FakeTransport()
        q = build({"type": "aws_sqs", **AWS, "queue_url": "https://sqs.us-east-1.amazonaws.com/1/q"}, t)
        self.assertEqual(q.write_batch([{"a": 1}], {"run_id": 1, "batch": 1}), [])
        self.assertEqual(t.calls[0]["headers"]["x-amz-target"], "AmazonSQS.SendMessage")
        self.assertEqual(json.loads(json.loads(t.calls[0]["body"])["MessageBody"]), {"a": 1})

    def test_missing_aws_credentials(self):
        old = {k: os.environ.pop(k, None) for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")}
        try:
            with self.assertRaises(ConfigError):
                build({"type": "aws_s3", "region": "us-east-1", "bucket": "b"})
        finally:
            os.environ.update({k: v for k, v in old.items() if v})

    def test_unknown_connector(self):
        with self.assertRaises(ConfigError):
            build({"type": "salesforce"})


def _ns_page(items, more=False):
    return Response(200, json.dumps({"items": items, "hasMore": more}).encode())


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(os.path.join(self.tmp.name, "t.db"))
        self.flow = {
            "name": "ns-to-s3",
            "source": {**NS, "query": "SELECT * FROM customer WHERE m > '{since}'", "delta_field": "m"},
            "mapping": {"fields": {"id": "id", "email": {"from": "email", "transform": "lower", "required": True}}},
            "destination": {"type": "aws_s3", **AWS, "bucket": "b"},
            "retries": 2,
        }

    def _transport(self, items, s3_statuses=()):
        statuses = list(s3_statuses)

        def handler(method, url, headers, body):
            if "suitetalk" in url:
                return _ns_page(items)
            return Response(statuses.pop(0) if statuses else 200)
        return FakeTransport(handler)

    def test_success_advances_watermark_and_next_run_uses_it(self):
        items = [{"id": 1, "email": "A@X.COM", "m": "2024-01-01 10:00:00"},
                 {"id": 2, "email": "B@X.COM", "m": "2024-01-03 10:00:00"}]
        t = self._transport(items)
        res = run_flow(self.flow, self.store, transport=t)
        self.assertEqual((res.status, res.read, res.written, res.failed), ("success", 2, 2, 0))
        put = [c for c in t.calls if c["method"] == "PUT"][0]
        self.assertIn(b'"email": "a@x.com"', put["body"])
        self.assertEqual(self.store.get_state("ns-to-s3")["watermark"], "2024-01-03 10:00:00")
        t2 = self._transport([])
        run_flow(self.flow, self.store, transport=t2)
        self.assertIn(b"2024-01-03 10:00:00", t2.calls[0]["body"])

    def test_mapping_failure_is_partial_and_holds_watermark(self):
        items = [{"id": 1, "email": "a@x.com", "m": "2024-01-01 00:00:00"}, {"id": 2, "m": "2024-01-02 00:00:00"}]
        res = run_flow(self.flow, self.store, transport=self._transport(items))
        self.assertEqual((res.status, res.written, res.failed), ("partial", 1, 1))
        self.assertEqual(self.store.get_state("ns-to-s3"), {})
        self.assertEqual(self.store.errors("ns-to-s3")[0][2], "mapping")

    def test_retries_transient_then_succeeds(self):
        sleeps = []
        t = self._transport([{"id": 1, "email": "a@x.com", "m": "2024-01-01 00:00:00"}], s3_statuses=[503, 200])
        res = run_flow(self.flow, self.store, transport=t, sleep=sleeps.append)
        self.assertEqual(res.status, "success")
        self.assertEqual(sleeps, [1])

    def test_retries_exhausted_marks_failed(self):
        t = self._transport([{"id": 1, "email": "a@x.com", "m": "2024-01-01 00:00:00"}], s3_statuses=[503] * 5)
        res = run_flow(self.flow, self.store, transport=t, sleep=lambda s: None)
        self.assertEqual(res.status, "failed")
        self.assertEqual(self.store.get_state("ns-to-s3"), {})

    def test_dry_run_does_not_write_or_advance(self):
        t = self._transport([{"id": 1, "email": "a@x.com", "m": "2024-01-01 00:00:00"}])
        res = run_flow(self.flow, self.store, transport=t, dry_run=True)
        self.assertEqual((res.status, res.read, res.written), ("success", 1, 0))
        self.assertFalse([c for c in t.calls if c["method"] == "PUT"])
        self.assertEqual(self.store.get_state("ns-to-s3"), {})

    def test_env_secrets_resolved(self):
        self.flow["source"]["consumer_secret"] = "$env:NS_CS"
        with self.assertRaises(ConfigError):
            run_flow(self.flow, self.store, transport=self._transport([]), env={})
        res = run_flow(self.flow, self.store, transport=self._transport([]), env={"NS_CS": "x"})
        self.assertEqual(res.status, "success")


class CliTests(unittest.TestCase):
    def test_validate_run_and_history(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.json")
            with open(path, "w") as fh:
                json.dump({"name": "f", "source": {"type": "nope"}, "destination": {"type": "aws_s3"}}, fh)
            db = os.path.join(d, "db")
            self.assertEqual(cli_main(["--db", db, "validate", path]), 0)
            self.assertEqual(cli_main(["--db", db, "run", path]), 2)  # unknown connector
            self.assertEqual(cli_main(["--db", db, "serve", path, "--every", "0", "--max-runs", "2"]), 0)
            self.assertEqual(cli_main(["--db", db, "runs"]), 0)
            self.assertEqual(cli_main(["connectors"]), 0)


if __name__ == "__main__":
    unittest.main()


class S3StateTests(unittest.TestCase):
    def test_seen_keys_skip_and_persist_only_on_clean_run(self):
        listing = (b"<ListBucketResult><Contents><Key>in/a</Key></Contents>"
                   b"<Contents><Key>in/b</Key></Contents></ListBucketResult>")

        def handler(method, url, headers, body):
            return Response(200, listing if "list-type" in url else b'{"k": "%s"}' % url.rsplit("/", 1)[-1].encode())
        with tempfile.TemporaryDirectory() as d:
            store = Store(os.path.join(d, "t.db"))
            flow = {"name": "s3in", "source": {"type": "aws_s3", **AWS, "bucket": "b", "prefix": "in/"},
                    "destination": {"type": "aws_sqs", **AWS, "queue_url": "https://sqs.us-east-1.amazonaws.com/1/q"}}
            t = FakeTransport(handler)
            self.assertEqual(run_flow(flow, store, transport=t).read, 2)
            self.assertEqual(store.get_state("s3in")["seen_keys"], ["in/a", "in/b"])
            self.assertEqual(run_flow(flow, store, transport=FakeTransport(handler)).read, 0)


class LocalHttpEndToEndTests(unittest.TestCase):
    """Real UrllibTransport against a local fake S3 (path-style endpoint): copies in/ -> out/."""

    def test_s3_to_s3_over_real_http(self):
        import http.server
        import threading
        import urllib.parse
        objects = {"in/a.jsonl": b'{"n": "  Ann "}\n{"n": "Bob"}\n'}
        seen_auth = []

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body=b""):
                self.send_response(code)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                u = urllib.parse.urlsplit(self.path)
                seen_auth.append(self.headers.get("Authorization", ""))
                if u.path == "/bkt":
                    prefix = urllib.parse.parse_qs(u.query).get("prefix", [""])[0]
                    keys = "".join(f"<Contents><Key>{k}</Key></Contents>" for k in objects if k.startswith(prefix))
                    return self._send(200, f"<ListBucketResult>{keys}</ListBucketResult>".encode())
                key = urllib.parse.unquote(u.path[len("/bkt/"):])
                self._send(200, objects[key]) if key in objects else self._send(404, b"nope")

            def do_PUT(self):
                seen_auth.append(self.headers.get("Authorization", ""))
                objects[urllib.parse.unquote(self.path[len("/bkt/"):])] = self.rfile.read(
                    int(self.headers["Content-Length"]))
                self._send(200)

        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        old = os.environ.get("no_proxy")
        os.environ["no_proxy"] = "127.0.0.1"
        self.addCleanup(lambda: os.environ.__setitem__("no_proxy", old) if old else os.environ.pop("no_proxy", None))
        ep = f"http://127.0.0.1:{srv.server_port}"
        flow = {"name": "e2e", "source": {"type": "aws_s3", **AWS, "bucket": "bkt", "prefix": "in/", "endpoint": ep},
                "mapping": {"fields": {"name": {"from": "n", "transform": ["strip", "upper"]}}},
                "destination": {"type": "aws_s3", **AWS, "bucket": "bkt", "endpoint": ep, "key": "out/{flow}.jsonl"}}
        with tempfile.TemporaryDirectory() as d:
            res = run_flow(flow, Store(os.path.join(d, "t.db")))
        self.assertEqual((res.status, res.read, res.written), ("success", 2, 2))
        self.assertEqual(objects["out/e2e.jsonl"], b'{"name": "ANN"}\n{"name": "BOB"}\n')
        self.assertTrue(all(a.startswith("AWS4-HMAC-SHA256") for a in seen_auth))
