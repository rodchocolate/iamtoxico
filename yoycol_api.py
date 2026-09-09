"""Yoycol Open API V4 client — HMAC-signed requests.

Auth (from https://www.yoycol.com/api/2025/redoc, "Signature Guide"):
every /api/2025/open/v4/** request carries X-API-Access-Key / -Timestamp
(epoch ms) / -Nonce (32 chars) / -Algorithm / -Version / -Signature headers,
where the signature is Base64(HMAC_SHA256(signatureData, secretKey)) over
newline-joined method/path/timestamp/nonce/accessKey/algorithm/version plus
a `params=` line of ascending-sorted query keys (omitted when no params).
The request body is NOT part of the signature. Success business code: 100000.

Keys: YOYCOL_API_KEY / YOYCOL_API_SECRET in ~/.hermes/.env.

Scope note: the external API has NO design-upload endpoint. Designs are
created in Yoycol's web designer and surface here as product templates with
a designCode; store products bind variants to (skuCode, designCode). So this
client covers catalog browsing, template listing, store-product mapping,
orders, shipping quotes and tracking — not artwork creation.

Usage:
  python3 yoycol_api.py catalog [query]     # browse blank catalog
  python3 yoycol_api.py templates           # list saved designs
  python3 yoycol_api.py variants <productId> # variant SKUs + base prices
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://www.yoycol.com"
V4 = "/api/2025/open/v4"
OK = "100000"


def _keys() -> tuple[str, str]:
    key = os.environ.get("YOYCOL_API_KEY")
    sec = os.environ.get("YOYCOL_API_SECRET")
    if not key or not sec:
        env = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env):
            for line in open(env):
                line = line.strip()
                if line.startswith("YOYCOL_API_KEY="):
                    key = line.split("=", 1)[1]
                elif line.startswith("YOYCOL_API_SECRET="):
                    sec = line.split("=", 1)[1]
    if not key or not sec:
        raise RuntimeError("YOYCOL_API_KEY / YOYCOL_API_SECRET not set (env or ~/.hermes/.env)")
    return key, sec


def request(method: str, path: str, params: dict | None = None, body: dict | None = None):
    """Signed request to a V4 path (e.g. '/catalog/products'). Returns the
    decoded envelope; raises on transport errors, returns envelope as-is on
    business errors so callers can inspect code/msg."""
    key, sec = _keys()
    full_path = V4 + path
    ts = str(int(time.time() * 1000))
    nonce = secrets.token_hex(16)
    lines = [
        f"method={method.upper()}",
        f"path={full_path}",
        f"timestamp={ts}",
        f"nonce={nonce}",
        f"accessKey={key}",
        "algorithm=HmacSHA256",
        "version=4.0",
    ]
    if params:
        items = sorted((k, str(v)) for k, v in params.items())
        lines.append("params=" + "&".join(f"{k}={v}" for k, v in items))
    sig = base64.b64encode(
        hmac.new(sec.encode(), "\n".join(lines).encode(), hashlib.sha256).digest()
    ).decode()
    url = BASE + full_path
    if params:
        url += "?" + urllib.parse.urlencode(sorted(params.items()))
    req = urllib.request.Request(
        url,
        method=method.upper(),
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "X-API-Access-Key": key,
            "X-API-Timestamp": ts,
            "X-API-Nonce": nonce,
            "X-API-Algorithm": "HmacSHA256",
            "X-API-Version": "4.0",
            "X-API-Signature": sig,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def get(path: str, params: dict | None = None):
    return request("GET", path, params)


def _main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "catalog"
    if cmd == "catalog":
        params = {"page": 1, "size": 10}
        if len(sys.argv) > 2:
            params["query"] = sys.argv[2]
        out = get("/catalog/products", params)
    elif cmd == "templates":
        out = get("/product_templates", {"page": 1, "size": 20})
    elif cmd == "variants" and len(sys.argv) > 2:
        out = get(f"/catalog/products/{sys.argv[2]}/variants", {"page": 1, "size": 50})
    else:
        print(__doc__)
        return 2
    if out.get("code") != OK:
        print("API error:", out.get("code"), out.get("msg"))
        return 1
    print(json.dumps(out.get("data"), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
