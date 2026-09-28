#!/usr/bin/env python3
"""Jev's Store server.

Serves the static frontend and proxies personalization calls to Jev
(Typesafe system-one) via the vault-keyed jev.py CLI, so the credential
never touches the browser.

Endpoints:
  GET  /                  -> web/index.html (static files under web/)
  GET  /api/catalog       -> the product catalog JSON
  POST /api/profile       -> Noul: interest probabilities per category
  POST /api/rank          -> Choice: rank candidate products, return match probs
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
JEV_CLI = Path.home() / "workspace" / "skills" / "typesafe" / "bin" / "jev.py"
JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
JEV_API_KEY = os.environ.get("JEV_API_KEY", "")  # portable path: run anywhere
PORT = 8099

with open(ROOT / "data" / "catalog.json", encoding="utf-8") as f:
    CATALOG = json.load(f)["products"]
BY_SKU = {p["sku"]: p for p in CATALOG}

_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 120.0


def cache_get(key: str):
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    return None


def cache_set(key: str, value: dict):
    _cache[key] = (time.time() + CACHE_TTL, value)


def jev_call_direct(payload: dict, timeout: float = 8.0) -> dict:
    """Direct HTTPS call for running off-box (key from JEV_API_KEY env)."""
    body = {"model": "jev-latest", "state": payload["state"],
            "questions": payload["questions"]}
    req = urllib.request.Request(
        JEV_ENDPOINT, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {JEV_API_KEY}"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"_error": f"direct jev call: {exc}"}


def jev_call(payload: dict, timeout: float = 8.0) -> dict:
    """One Jev round-trip. Prefers JEV_API_KEY; else the vault-keyed CLI."""
    if JEV_API_KEY:
        out = jev_call_direct(payload, timeout)
        if "_error" not in out:
            return out
    return jev_call_cli(payload, timeout)


def jev_call_cli(payload: dict, timeout: float = 8.0) -> dict:
    """One Jev round-trip through the vault-keyed CLI. Never raises."""
    try:
        proc = subprocess.run(
            ["python3", str(JEV_CLI), "--timeout", str(timeout)],
            input=json.dumps(payload).encode("utf-8"),
            capture_output=True,
            timeout=timeout + 5,
        )
    except Exception as exc:  # noqa: BLE001
        return {"_error": f"jev subprocess: {exc}"}
    if proc.returncode != 0:
        return {"_error": (proc.stdout.decode() or proc.stderr.decode())[:300]}
    try:
        return json.loads(proc.stdout.decode())
    except Exception as exc:  # noqa: BLE001
        return {"_error": f"bad jev json: {exc}"}


def describe_signal(s: dict) -> str:
    p = BY_SKU.get(s.get("sku", ""), {})
    title = p.get("title", s.get("sku", "?"))
    cat = p.get("category", "?")
    kind = s.get("type", "dwell")
    if kind == "dwell":
        return f"Dwelled {s.get('dwellMs', 0) / 1000:.1f}s on '{title}' ({cat})"
    if kind == "click":
        return f"Clicked '{title}' ({cat})"
    if kind == "cart":
        return f"Added to cart: '{title}' ({cat})"
    if kind == "linger":
        return f"Scrolled slowly past '{title}' ({cat})"
    return f"Viewed '{title}' ({cat})"


def profile_endpoint(body: dict) -> dict:
    """Noul: probability the shopper is interested in each top category."""
    signals = body.get("signals", [])[-8:]
    top_cats = body.get("topCats", [])[:3]
    if not signals or not top_cats:
        return {"probs": {}}
    key = "prof:" + "|".join(
        f"{s.get('sku')}:{s.get('type')}:{int(s.get('dwellMs', 0) / 500)}" for s in signals
    ) + "@" + ",".join(top_cats)
    hit = cache_get(key)
    if hit:
        return hit

    state_lines = [
        "You are observing a shopper browsing an e-commerce feed called Jev's Store.",
        "Their recent interactions, oldest first:",
    ]
    state_lines += [f"- {describe_signal(s)}" for s in signals]
    state = "\n".join(state_lines)
    questions = {
        f"q{i}": {
            "type": "noul",
            "instructions": (
                f"Judge the statement: this shopper is currently interested "
                f"in buying products in the '{cat}' category."
            ),
        }
        for i, cat in enumerate(top_cats)
    }
    resp = jev_call({"state": state, "questions": questions})
    probs = {}
    if "_error" not in resp:
        for i, cat in enumerate(top_cats):
            ans = (resp.get("answers") or resp.get("results") or {}).get(f"q{i}", {})
            # jev.py prints the raw provider response; tolerate a few shapes
            p = ans.get("noul", ans.get("probability", ans.get("p")))
            if isinstance(p, (int, float)):
                probs[cat] = round(float(p), 3)
    out = {"probs": probs}
    if probs:
        cache_set(key, out)
    return out


def rank_endpoint(body: dict) -> dict:
    """Choice: rank candidate products by fit to the shopper's interests."""
    candidates = body.get("candidates", [])[:10]
    interests = body.get("interests", "")
    if not candidates:
        return {"ranking": []}
    key = "rank:" + ",".join(c["sku"] for c in candidates) + "@" + interests[:80]
    hit = cache_get(key)
    if hit:
        return hit

    state = (
        "You are the personalization engine for Jev's Store, an e-commerce feed.\n"
        f"The shopper's current inferred interests: {interests or 'unknown (cold start)'}.\n"
        "Task: choose which of the candidate products best match what this "
        "shopper wants to see next. Strong matches to their interests first; "
        "you may include one serendipitous but plausibly complementary pick."
    )
    criteria = {
        c["sku"]: f"{c['title']} ({c.get('variant', 'Standard')}) — "
                  f"{c['category']}, ${c['price']}. {c.get('blurb', '')[:90]}"
        for c in candidates
    }
    resp = jev_call(
        {"state": state, "questions": {"rank": {"type": "choice", "criteria": criteria}}},
        timeout=10.0,
    )
    ranking: list[dict] = []
    ans = (resp.get("answers") or resp.get("results") or {}).get("rank", resp)
    probs = ans.get("probabilities") or {}
    if isinstance(probs, dict) and probs:
        for sku, p in sorted(probs.items(), key=lambda kv: kv[1], reverse=True):
            if isinstance(p, (int, float)):
                ranking.append({"sku": sku, "p": round(float(p), 3)})
    out = {"ranking": ranking,
           "choice": ans.get("choice"),
           "confidence": ans.get("confidence")}
    if ranking:
        cache_set(key, out)
    return out


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".webp": "image/webp",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter logs
        print(f"[{self.command}] {self.path}")

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/catalog":
            self._send(200, json.dumps(CATALOG).encode(), "application/json")
            return
        path = self.path.split("?", 1)[0]
        if path == "/":
            path = "/index.html"
        target = (WEB / path.lstrip("/")).resolve()
        if not str(target).startswith(str(WEB)) or not target.is_file():
            self._send(404, b"not found", "text/plain")
            return
        self._send(200, target.read_bytes(),
                   CONTENT_TYPES.get(target.suffix, "application/octet-stream"))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:  # noqa: BLE001
            body = {}
        if self.path == "/api/profile":
            out = profile_endpoint(body)
        elif self.path == "/api/rank":
            out = rank_endpoint(body)
        else:
            self._send(404, b"not found", "text/plain")
            return
        self._send(200, json.dumps(out).encode(), "application/json")


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Jev's Store on http://localhost:{PORT}  ({len(CATALOG)} SKUs)")
    server.serve_forever()


if __name__ == "__main__":
    main()
