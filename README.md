# Jev's Store

A prototype e-commerce landing page proving the value of a **system-one model
(Jev)** driving an adaptive shopping feed.

**The concept:** as you hover over products, Jev reads your intent in real time
and pre-populates upcoming (not yet visible) rows with related products — each
badged with a Jev match score. A Jev ON/OFF toggle + metrics strip turns the
demo into objective evidence: same UI, adaptive ranking vs. popularity ranking.

## Quick start

```bash
# 1. Build the catalog (fetches real product records from dummyjson, generates mock variants)
python3 data/build_catalog.py

# 2. Start the server (serves the page + Jev API proxy; key stays in the secure vault)
python3 server/app.py

# 3. Open http://localhost:8099
```

## Run it on your own machine

The server calls Jev through the vault-keyed CLI by default. To run off-box,
set your Typesafe key (from your Typesafe dashboard — never paste it in chat)
as an env var and the server will call the API directly instead:

```bash
export JEV_API_KEY="<key from your Typesafe dashboard>"
python3 server/app.py
```

## How it works

- **Signal layer (browser):** hover dwell (≥600ms), scroll-velocity slowdown,
  clicks, add-to-carts → debounced event stream. All state lives in the
  browser memory only — nothing is persisted. The Reset button (or a refresh) wipes it.
- **Jev layer (server):** `POST /api/noul` maintains the interest profile
  ("probability the user is interested in X"); `POST /api/choice` ranks each
  injected row's ~10 candidates and returns per-option probabilities rendered
  as match-% badges. Calls go through `~/workspace/skills/typesafe/bin/jev.py`
  so the Typesafe credential never touches the client.
- **Feed:** infinite scroll (IntersectionObserver), 4-per-row grid, lazy-loaded
  images. Every 3rd row is a "Picked for you by Jev" row, populated *before* it
  scrolls into view.

## Proof mode

The header toggle switches between **Jev adaptive** and **popularity**
ranking. The metrics strip logs hovers, avg dwell, click-through, and
add-to-carts per mode — the objective lift readout.

## Catalog

`data/catalog.json` — ~600 SKUs. Seeded from 194 real product records
(dummyjson: real titles, prices, categories, hosted photos); variant properties
(colors, sizes, finishes) and price jitter are mocked, seeded RNG for stable
rebuilds.
