#!/usr/bin/env python3
"""Build data/catalog.json for Jev's Store.

Seed: 194 real product records from dummyjson (real titles, prices,
categories, hosted photos). Variants: mocked colors/sizes/finishes + price
jitter, seeded RNG so rebuilds are stable. Output: ~600 SKUs.
"""
from __future__ import annotations

import json
import random
import urllib.request
from pathlib import Path

OUT = Path(__file__).parent / "catalog.json"
RNG = random.Random(20260926)

COLORS = ["Onyx Black", "Arctic White", "Navy", "Forest Green", "Crimson",
          "Sand", "Graphite", "Blush", "Cobalt", "Mustard"]
FINISHES = ["Matte", "Gloss", "Brushed Steel", "Walnut", "Oak"]
APPAREL_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
SHOE_SIZES = ["7", "8", "9", "10", "11", "12"]

APPAREL_CATS = {"tops", "womens-dresses", "womens-tops", "mens-shirts"}
SHOE_CATS = {"mens-shoes", "womens-shoes"}
WATCH_CATS = {"mens-watches", "womens-watches"}


def fetch_products() -> list[dict]:
    url = ("https://dummyjson.com/products?limit=194&select="
           "id,title,description,price,category,thumbnail,images,rating,brand,tags,stock")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["products"]


def variants_for(p: dict) -> list[dict]:
    """Return 2-4 variant SKUs for a seed product (first entry is the base)."""
    cat = p.get("category", "")
    imgs = p.get("images") or [p.get("thumbnail")]
    base = {
        "sku": f"p{p['id']}",
        "seed_id": p["id"],
        "title": p["title"],
        "brand": p.get("brand") or "Jev's Basics",
        "category": cat,
        "price": round(float(p["price"]), 2),
        "image": p.get("thumbnail") or (imgs[0] if imgs else ""),
        "images": imgs[:3],
        "rating": p.get("rating"),
        "tags": p.get("tags") or [],
        "blurb": (p.get("description") or "")[:140],
        "props": {},
        "variant": "Standard",
    }
    out = [base]
    n_extra = RNG.choice([1, 2, 2, 3])
    for i in range(n_extra):
        v = dict(base)
        v["images"] = list(base["images"])
        if cat in APPAREL_CATS:
            size = RNG.choice(APPAREL_SIZES)
            color = RNG.choice(COLORS)
            v["variant"] = f"{color} / {size}"
            v["props"] = {"color": color, "size": size}
        elif cat in SHOE_CATS:
            size = RNG.choice(SHOE_SIZES)
            color = RNG.choice(COLORS)
            v["variant"] = f"{color} / US {size}"
            v["props"] = {"color": color, "size": f"US {size}"}
        elif cat in WATCH_CATS:
            finish = RNG.choice(FINISHES)
            v["variant"] = finish
            v["props"] = {"finish": finish}
        else:
            color = RNG.choice(COLORS)
            v["variant"] = color
            v["props"] = {"color": color}
        v["sku"] = f"p{p['id']}-{i + 1}"
        v["price"] = round(float(p["price"]) * RNG.uniform(0.9, 1.12), 2)
        if len(imgs) > 1:
            v["image"] = imgs[RNG.randrange(len(imgs))]
        out.append(v)
    return out


def main() -> None:
    products = fetch_products()
    catalog: list[dict] = []
    for p in products:
        catalog.extend(variants_for(p))
    # Deterministic shuffle so the feed isn't category-clumped
    RNG.shuffle(catalog)
    payload = {
        "built": "2026-09-26",
        "seed_source": "dummyjson.com (real product records; variant props mocked)",
        "count": len(catalog),
        "products": catalog,
    }
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    cats: dict[str, int] = {}
    for c in catalog:
        cats[c["category"]] = cats.get(c["category"], 0) + 1
    print(f"wrote {OUT} — {len(catalog)} SKUs, {len(cats)} categories")
    for k in sorted(cats):
        print(f"  {k}: {cats[k]}")


if __name__ == "__main__":
    main()
