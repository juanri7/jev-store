# SUPERPOWERS.md — Jev's Store capability gates

Each capability gets a verdict as we build: **ADOPT** (in the prototype),
**V2** (deferred), or **REJECT** (with evidence). Suggested build order is
top-down.

## P0 — the core loop

### S1. Hover-to-row replenishment — ADOPT
Invisible rows pre-populate from the live interest profile, each card badged
with a Jev match score. This is the demo's thesis; everything else is garnish.

### S2. Proof mode (Jev ON/OFF + metrics strip) — ADOPT
Same UI, two ranking modes, live lift readout (hovers, avg dwell, CTR,
add-to-carts per mode). Without this it's a demo; with it, it's evidence.

### S3. Ghost profile panel — ADOPT
Live sidebar showing what Jev thinks you're into, with probability bars
updating as you browse. Transparency as a feature — watching the machine read
your mind is the wow moment.

## P1 — depth

### S4. Cross-category leaps — PLANNED
Hovering running shoes surfaces a fitness tracker and gym bag (complementary,
not just similar). Jev Choice over "similar vs complementary vs trending"
candidate sets.

### S5. Price-sensitivity inference — PLANNED
A quiet Noul read on budget sensitivity that re-ranks within inferred price
bands.

### S6. Serendipity dial — PLANNED
User-controlled explore/exploit slider. Fun, and it shows off the model's range.

### S7. Cold-start sprint — PLANNED
No quiz, no login: a usable interest profile from the first three dwells.
The system-one flex. (Partially inherent in S1; needs explicit measurement.)

## V2 candidates

### S8. Session morph
The category nav itself reorders by inferred interest. Ambitious; revisit after
the core loop is proven.

### S9. Autoplay / game mode (Juan, 2026-09-26)
The feed auto-scrolls at a very slow pace, Tetris-style; the user must
hover/interact with products as they drift by, which drives the Jev loop.
Hypothesis: forced pacing incentivizes interaction where free-roam doesn't,
making the intent signal denser and the demo livelier. Open questions: does
auto-scroll fight the user's reading rhythm? Does it inflate accidental dwells
(noise vs. signal)? Worth a prototype toggle once S1–S3 are solid.
