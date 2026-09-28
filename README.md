# Jev's Store — the feed that reads your mind

A prototype store where the shelves rearrange themselves around what you're
interested in — live, as you browse. Hover over a few products and Jev, a
fast system-one model, picks upcoming rows for you before they scroll into
view. Each pick carries a match score, so you can see the model's reasoning.

**Try it in 60 seconds:** run it, browse, then flip the Jev toggle OFF.
The same feed goes dead. That gap is the whole point.

## Who this is for

- **Product thinkers:** want to feel what in-session personalization does for
  shoppers — no code needed. Read "How it feels" below, watch the
  [25-second demo](https://github.com/juanri7/jevstore-explainer#watch-it-work--25-seconds).
- **Engineers:** want the integration pattern — signals → interest profile →
  ranked candidates. Read "How it's built" and the endpoint notes.

## How it feels (non-technical)

No quiz, no login, no search. You linger on sneakers; sneaker-adjacent rows
start appearing ahead of you. A sidebar shows what Jev thinks you want,
updating as you browse — transparency instead of a black box. Nothing is
stored: reset the session (or refresh) and it forgets you.

## How it's built (technical)

- **Signal layer (browser):** hover dwell (≥600ms), scroll-velocity slowdown
  (linger), clicks, add-to-carts → debounced event stream (last ~20 events).
  All state lives in browser memory only.
- **Profile (`POST /api/profile`):** the server asks Jev Noul questions —
  "probability this shopper is interested in category X?" — over the last
  ~8 signals and top categories. Returns per-category probabilities rendered
  as the ghost panel's bars. Results cached 120s.
- **Rank (`POST /api/rank`):** the server asks one Jev Choice question over
  ~10 candidate SKUs given the inferred interests. Returns per-SKU
  probabilities rendered as match-% badges. Results cached 120s.
- **Feed:** infinite scroll (IntersectionObserver), 4-per-row grid,
  lazy-loaded images. Every 3rd row is a "Picked for you by Jev" row,
  ranked *before* it scrolls into view — no spinner, no layout shift.
- **Key handling:** the Typesafe credential never touches the client.
  `server/app.py` calls Jev through the vault-keyed CLI by default, or
  directly via `JEV_API_KEY` when set.

## Why a system-one model (not a frontier LLM)

Ranking a row is a judgment call, not an essay. Jev answers in milliseconds,
so rows are ready before you scroll — a frontier round-trip would stall the
feed. And Choice ranks a fixed candidate set, so it can never invent a
product that doesn't exist. Hallucination is structurally impossible.

## Proof mode

The header toggle switches between **Jev adaptive** and **popularity**
ranking. The metrics strip logs hovers, avg dwell, clicks, and add-to-carts
per mode — run both, compare, decide for yourself.

## Quick start

```bash
# 1. Build the catalog (fetches real product records from dummyjson, generates mock variants)
python data/build_catalog.py

# 2. Start the server (serves the page + Jev API proxy; key stays server-side)
python server/app.py

# 3. Open http://localhost:8099 — hover, watch, toggle Jev OFF
```

## Run it on your own machine

The server calls Jev through the vault-keyed CLI by default. To run off-box,
set your Typesafe key (from your Typesafe dashboard — never paste it in chat)
as an env var and the server will call the API directly instead:

```bash
export JEV_API_KEY="<key from your Typesafe dashboard>"
python server/app.py
```

## Catalog

`data/catalog.json` — 578 SKUs. Seeded from real product records
(dummyjson: real titles, prices, categories, hosted photos); variant
properties (colors, sizes, finishes) and price jitter are mocked, seeded RNG
for stable rebuilds.

## Explainer + video

Plain-English walkthrough and 25-second demo video:
[jevstore-explainer](https://github.com/juanri7/jevstore-explainer).
