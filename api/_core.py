"""Shared Jev logic for Vercel serverless functions.

Mirrors the endpoints in server/app.py (local dev server) so both paths run
the same ranking. If you change scoring here, change it there too.

Serverless notes:
- Reads JEV_API_KEY from the environment only (set it in the Vercel
  dashboard; never commit it). No vault-CLI fallback: there is no vault
  on Vercel.
- Cache is per-instance memory; cold starts reload the catalog (~442KB).
- Keep each Jev round-trip well under the function maxDuration (see
  vercel.json). Timeouts below are conservative on purpose.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
JEV_API_KEY = os.environ.get("JEV_API_KEY", "")
JEV_TIMEOUT = 8.0
MAX_BODY_BYTES = 256 * 1024

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


def jev_call(payload: dict) -> dict:
    """One Jev round-trip over HTTPS. Never raises; returns {"_error": ...}."""
    if not JEV_API_KEY:
        return {"_error": "JEV_API_KEY is not set"}
    body = {"model": "jev-latest", "state": payload["state"],
            "questions": payload["questions"]}
    req = urllib.request.Request(
        JEV_ENDPOINT, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {JEV_API_KEY}"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=JEV_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"_error": f"jev call: {exc}"}


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
    key = "rank:" + ",".join(c.get("sku", "?") for c in candidates) + "@" + interests[:80]
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
        c.get("sku", "?"): f"{c.get('title', c.get('sku', '?'))} ({c.get('variant', 'Standard')}) — "
                  f"{c.get('category', '?')}, ${c.get('price', '?')}. {c.get('blurb', '')[:90]}"
        for c in candidates
    }
    resp = jev_call(
        {"state": state, "questions": {"rank": {"type": "choice", "criteria": criteria}}},
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
