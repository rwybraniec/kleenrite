"""Request signing: OAuth1 (NetSuite token-based auth) and AWS Signature V4."""

import base64
import datetime as dt
import hashlib
import hmac
import secrets
import time
from urllib.parse import parse_qsl, quote, urlsplit

_UNRESERVED = "-_.~"


def pct(value: str) -> str:
    """RFC 3986 percent-encoding."""
    return quote(str(value), safe=_UNRESERVED)


def oauth1_header(method, url, *, account, consumer_key, consumer_secret, token_id, token_secret,
                  timestamp=None, nonce=None) -> str:
    """Build a NetSuite TBA ``Authorization`` header (OAuth 1.0, HMAC-SHA256)."""
    parts = urlsplit(url)
    base_url = f"{parts.scheme}://{parts.netloc}{parts.path}"
    oauth = {
        "oauth_consumer_key": consumer_key,
        "oauth_token": token_id,
        "oauth_signature_method": "HMAC-SHA256",
        "oauth_timestamp": str(timestamp if timestamp is not None else int(time.time())),
        "oauth_nonce": nonce or secrets.token_hex(10),
        "oauth_version": "1.0",
    }
    params = parse_qsl(parts.query, keep_blank_values=True) + list(oauth.items())
    norm = "&".join(f"{k}={v}" for k, v in sorted((pct(k), pct(v)) for k, v in params))
    base = "&".join([method.upper(), pct(base_url), pct(norm)])
    key = f"{pct(consumer_secret)}&{pct(token_secret)}".encode()
    sig = base64.b64encode(hmac.new(key, base.encode(), hashlib.sha256).digest()).decode()
    fields = {"realm": account, **oauth, "oauth_signature": sig}
    return "OAuth " + ", ".join(f'{k}="{pct(v) if k != "realm" else v}"' for k, v in fields.items())


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def sigv4_headers(method, url, *, region, service, access_key, secret_key, body=b"",
                  headers=None, session_token=None, now=None) -> dict:
    """Return request headers (including ``Authorization``) signed with AWS SigV4."""
    now = now or dt.datetime.now(dt.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    day = amz_date[:8]
    parts = urlsplit(url)
    payload_hash = hashlib.sha256(body).hexdigest()

    hdrs = {k.lower(): " ".join(str(v).split()) for k, v in (headers or {}).items()}
    hdrs["host"] = parts.netloc
    hdrs["x-amz-date"] = amz_date
    if service == "s3":
        hdrs["x-amz-content-sha256"] = payload_hash
    if session_token:
        hdrs["x-amz-security-token"] = session_token

    path = parts.path or "/"
    # S3 encodes the path once; every other service encodes it twice.
    canon_path = path if service == "s3" else quote(path, safe="/~")
    query = sorted((pct(k), pct(v)) for k, v in parse_qsl(parts.query, keep_blank_values=True))
    canon_query = "&".join(f"{k}={v}" for k, v in query)
    names = sorted(hdrs)
    canon_headers = "".join(f"{n}:{hdrs[n]}\n" for n in names)
    signed = ";".join(names)
    canonical = "\n".join([method.upper(), canon_path, canon_query, canon_headers, signed, payload_hash])

    scope = f"{day}/{region}/{service}/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    k = _hmac(("AWS4" + secret_key).encode(), day)
    for part in (region, service, "aws4_request"):
        k = _hmac(k, part)
    signature = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    hdrs["authorization"] = (f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
                             f"SignedHeaders={signed}, Signature={signature}")
    hdrs.pop("host")  # urllib sets Host itself
    return hdrs
