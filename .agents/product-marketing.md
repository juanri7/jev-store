# Product Marketing Context

**Document version:** v1
**Last updated:** 2026-09-28

## Product Overview
**One-liner:** JevStore is a demo store whose shelves rearrange themselves around what you're actually interested in — live, as you browse.
**What it does:** A prototype e-commerce feed personalized in real time by Jev, a system-one model. Hover dwells, slow scrolls, clicks, and carts feed an interest profile (Noul); upcoming infinite-scroll rows are ranked (Choice) and pre-filled before they scroll into view, each card badged with a match score. A Jev ON/OFF toggle with a metrics strip proves lift vs. plain popularity ranking.
**Product category:** AI personalization demo / reference implementation for consumer storefronts.
**Product type:** Open-source prototype (Python server + static frontend) with a static explainer page.
**Business model:** None — educational artifact. Conversion = engineers run the demo; non-technical readers grasp the consumer value.

## Target Audience
**Target companies:** Consumer e-commerce / marketplace teams; system-one model evaluators.
**Decision-makers:** Non-technical product thinkers (what could this do for shoppers?) and engineers (how is it built?).
**Primary use case:** Show — don't tell — that a small, fast model can personalize a feed without frontier-LLM latency, cost, or hallucination.
**Jobs to be done:**
- See what adaptive ranking feels like as a shopper (browse → feed reads intent → relevant rows appear).
- Evaluate the Noul/Choice integration pattern for their own catalog (signals → profile → ranked candidates).
**Use cases:**
- Shopper browses shoes; sneaker-adjacent rows arrive before scrolling.
- Engineer clones repo, sets `JEV_API_KEY`, watches ghost profile + match scores respond to their own behavior.

## Personas
| Persona | Cares about | Challenge | Value we promise |
|---------|-------------|-----------|------------------|
| Non-technical product thinker | What shoppers feel; why this beats today's recommendations | AI demos are either hype videos or code dumps | A plain-English loop (browse → Jev learns → shelves rearrange) plus a 25s video showing it |
| Evaluating engineer | Signal schema, API contract, latency, key handling, cold start | Frontier-LLM rerankers are slow, pricey, hallucinate; rules engines are dumb | Candidate-constrained Choice over real SKUs (can't invent products), ms-scale ranks, key stays server-side, profile from ~3 dwells |

## Problems & Pain Points
**Core problem:** Storefront recommendations feel generic because real personalization is either too slow (frontier-LLM round-trip per ranking), too risky (free-text output can hallucinate products), or too dumb (popularity lists, hand-written rules).
**Why alternatives fall short:**
- Frontier-LLM reranking: seconds of latency per row, per-token cost, can recommend items that don't exist.
- Popularity / rules: same shelves for everyone; blind to in-session intent.
- Black-box feeds: shoppers (and PMs) can't see why anything was shown.
**What it costs them:** Bounces from irrelevant rows; engineering time babysitting prompts; latency budgets blown at scroll time.
**Emotional tension:** "AI personalization" overpromises — teams doubt any demo until they can toggle it off and feel the difference themselves.

## Competitive Landscape
**Direct:** Frontier-LLM rerankers — fall short on latency, cost, hallucination risk at scroll time.
**Secondary:** Classic recommenders (collaborative filtering, popularity) — fall short on in-session intent; same feed for everyone.
**Indirect:** Hand-tuned merchandising rules — fall short on adaptability; every new intent needs a new rule.

## Differentiation
**Key differentiators:**
- System-one model (Jev) scores intent in milliseconds — ranking happens before the row scrolls into view, no spinner.
- Choice is constrained to real candidate SKUs — it ranks, never invents; hallucination is structurally impossible.
- Proof mode: same UI, adaptive vs. popularity, with a live metrics strip (hovers, dwell, clicks, carts per mode).
- Ghost panel: the inferred profile is visible and live — transparency as a feature.
**How we do it differently:** Signals → Noul interest probabilities per category → Choice probabilities over ~10 candidate SKUs → match-% badges. Key never touches the browser.
**Why that's better:** Fast enough for infinite scroll, safe enough for production-shaped catalogs, legible enough to trust.
**Why customers choose us:** They can feel it in 60 seconds: toggle Jev off and the same feed goes dead.

## Objections
| Objection | Response |
|-----------|----------|
| Are the match scores real? | In the live demo with a key, yes — computed per session. In the video they are staged representative values (says so in the plan). |
| What about cold start? | Usable profile from the first ~3 dwells; no quiz, no login. |
| Will it work on my catalog? | The pattern is catalog-agnostic: candidate sets in, ranked SKUs out. 578-SKU demo is the reference. |
| Is my browsing data stored? | No. All state is browser memory; Reset or refresh wipes it. |

**Anti-persona:** Teams wanting a hosted personalization SaaS or a frontier-LLM chatbot — this is a self-run pattern demo, not a service.

## Switching Dynamics
**Push:** Generic recommendations; slow/expensive LLM experiments; prompt babysitting.
**Pull:** A feed that visibly reads intent in-session; toggle-off proof in under a minute.
**Habit:** "Popularity sort works fine" and merchandising rules already shipped.
**Anxiety:** New model dependency; key management; "will it hallucinate?" — answered structurally (ranked SKUs only, server-side key).

## Customer Language
**How they describe the problem:**
- "Recommendations feel generic."
- "LLM reranking is too slow for scroll time."
**How they describe us:**
- "The feed that reads your mind."
- "Rows ahead are picked for you."
**Words to use:** match score, picked for you, adaptive ranking, popularity ranking, intent, in-session, pre-filled.
**Words to avoid:** streamline, leverage, cutting-edge, seamless, revolutionary, AI-powered (vague).
**Glossary:**
| Term | Meaning |
|------|---------|
| Noul | Jev judgment: probability the shopper is interested in X (drives the ghost panel). |
| Choice | Jev ranking: probabilities over a fixed candidate set (drives match-% badges). |
| Ghost panel | Live sidebar showing inferred interests as probability bars. |
| Proof mode | Jev ON vs OFF toggle + per-mode metrics strip. |
| System-one | Fast, intuitive model tier — ms judgments, not deliberative reasoning. |

## Brand Voice
**Tone:** Plain, educational, honest. Confident but never hypey.
**Style:** Conversational for shoppers; precise for engineers. Numbers over adjectives (600ms, 2.5s, ~10 candidates, 578 SKUs).
**Personality:** Helpful, transparent, specific, calm, a little playful.

## Proof Points
**Metrics:** Proof-mode strip (hovers, avg dwell, clicks, carts per mode) — reader generates their own numbers by running the demo.
**Customers:** None (prototype).
**Testimonials:** None — the toggle-off moment is the testimonial.
**Value themes:**
| Theme | Proof |
|-------|-------|
| Speed | Rows populate before scrolling into view; no spinner (IntersectionObserver + pre-rank). |
| Safety | Choice ranks fixed SKUs; cannot hallucinate products. |
| Legibility | Ghost panel + match-% badges show the model's mind. |
| Honesty | Same UI both modes; metrics strip quantifies the gap. |

## Goals
**Business goal:** Engineers run the demo and understand the pattern; non-technical readers grasp the consumer value in <2 minutes.
**Conversion action:** Explainer → watch video / clone demo repo. Demo repo → run locally, flip the toggle.
**Current metrics:** None tracked.

## Changelog
- v1 (2026-09-28) — Initial context. Dual persona (product thinker + evaluating engineer); latency/safety differentiation; duplicated across jev-store and jevstore-explainer so each repo is self-contained for agents.
