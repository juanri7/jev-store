/* Jev's Store — feed logic: infinite scroll, hover-dwell signals, Jev-ranked rows. */
"use strict";

const ROW_SIZE = 4;
const DWELL_MS = 600;          // hover dwell threshold -> interest signal
const PROFILE_DEBOUNCE_MS = 2500;

const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const S = {
  products: [], queue: [], seen: new Set(),
  rowIndex: 0, loading: false,
  jevOn: true,
  cats: {},            // category -> weighted interest score
  skus: {},            // sku -> weighted interest score
  signals: [],         // recent raw signals (max 20)
  jevProbs: {},        // last Noul probabilities per category
  lingerAt: 0,
  hoverT0: new WeakMap(),
  metrics: null,
  profileTimer: null,
};

function freshMetrics() {
  return { hovers: 0, dwellMs: 0, clicks: 0, carts: 0 };
}
function resetState() {
  S.queue = [...S.products];
  S.seen = new Set();
  S.rowIndex = 0; S.loading = false;
  S.cats = {}; S.skus = {}; S.signals = []; S.jevProbs = {};
  S.lingerAt = 0; S.hoverT0 = new WeakMap();
  S.metrics = { on: freshMetrics(), off: freshMetrics() };
  S.profileTimer = null;
}
const M = () => (S.jevOn ? S.metrics.on : S.metrics.off);

/* ---------- catalog ---------- */
async function loadCatalog() {
  const res = await fetch("/api/catalog");
  S.products = await res.json();
  resetState();
}

/* ---------- cards & rows ---------- */
function cardHTML(p, badge) {
  return `
  <article class="card" data-sku="${esc(p.sku)}">
    <div class="img-wrap">
      <img loading="lazy" src="${esc(p.image)}" alt="${esc(p.title)}"
           onerror="this.style.display='none'">
      ${badge || ""}
    </div>
    <div class="body">
      <div class="title">${esc(p.title)}</div>
      <div class="variant">${esc(p.variant || "")} · ${esc(p.brand || "")}</div>
      <div class="meta">
        <span class="price">$${Number(p.price).toFixed(2)}</span>
        <span class="rating">★ ${p.rating ?? "–"}</span>
      </div>
      <button class="cart-btn">Add to cart</button>
    </div>
  </article>`;
}

function badgeFor(pct, explore) {
  if (pct == null) return `<span class="badge explore">✦ exploring</span>`;
  return `<span class="badge" title="Jev match score">${pct}% match</span>`;
}

function attachCard(el) {
  const sku = el.dataset.sku;
  el.addEventListener("mouseenter", () => {
    S.hoverT0.set(el, performance.now());
    M().hovers++;
    renderMetrics();
  });
  el.addEventListener("mouseleave", () => {
    const t0 = S.hoverT0.get(el);
    if (!t0) return;
    const dwell = performance.now() - t0;
    S.hoverT0.delete(el);
    if (dwell >= DWELL_MS) {
      M().dwellMs += dwell;
      emitSignal({ type: "dwell", sku, dwellMs: Math.round(dwell) });
      renderMetrics();
    }
  });
  el.addEventListener("click", (e) => {
    if (e.target.closest(".cart-btn")) {
      M().carts++;
      emitSignal({ type: "cart", sku });
      toast(`Added “${esc(shortTitle(sku))}” to cart`);
    } else {
      M().clicks++;
      emitSignal({ type: "click", sku });
    }
    renderMetrics();
  });
}

function shortTitle(sku) {
  const p = S.products.find((x) => x.sku === sku);
  return p ? p.title.slice(0, 42) : sku;
}

function takeNext(n) {
  const out = [];
  while (out.length < n && S.queue.length) {
    const p = S.queue.shift();
    if (S.seen.has(p.sku)) continue;
    S.seen.add(p.sku);
    out.push(p);
  }
  return out;
}

function localScore(p) {
  return (S.cats[p.category] || 0) * 2 + (p.rating || 3) / 5;
}

function appendRows(n) {
  const grid = $("#grid");
  for (let i = 0; i < n; i++) {
    const isJevRow = (S.rowIndex + 1) % 3 === 0;
    const row = document.createElement("div");
    row.className = "row" + (isJevRow ? " jev-row" : "");
    if (isJevRow) {
      const label = document.createElement("div");
      label.className = "row-label" + (S.jevOn ? "" : " pop");
      label.textContent = S.jevOn ? "✦ Picked for you by Jev" : "Popular right now";
      row.appendChild(label);
      // shimmer placeholders; filled async (pre-populated before visible)
      for (let k = 0; k < ROW_SIZE; k++) {
        const ph = document.createElement("div");
        ph.className = "card shimmer";
        ph.innerHTML = `<div class="img-wrap"></div><div class="body" style="min-height:110px"></div>`;
        row.appendChild(ph);
      }
      grid.appendChild(row);
      fillSmartRow(row);
    } else {
      const items = takeNext(ROW_SIZE);
      if (!items.length) break;
      row.innerHTML = items.map((p) => cardHTML(p)).join("");
      grid.appendChild(row);
      row.querySelectorAll(".card").forEach(attachCard);
    }
    S.rowIndex++;
  }
  if (!S.queue.length) {
    $("#sentinel").classList.add("hidden");
    $("#endMsg").classList.remove("hidden");
  }
}

async function fillSmartRow(row) {
  // candidate pool: next 40 unseen, scored locally; top 10 go to Jev
  const pool = [];
  const tmp = [];
  while (pool.length < 40 && S.queue.length) {
    const p = S.queue.shift();
    tmp.push(p);
    if (!S.seen.has(p.sku)) pool.push(p);
  }
  // return non-chosen back to the front, preserving order
  S.queue = [...tmp, ...S.queue];

  let picks, probs = {};
  if (S.jevOn && S.signals.length >= 2) {
    const cands = [...pool].sort((a, b) => localScore(b) - localScore(a)).slice(0, 10);
    const ranked = await rankViaJev(cands);
    if (ranked && ranked.length) {
      const bySku = Object.fromEntries(cands.map((c) => [c.sku, c]));
      picks = ranked.map((r) => bySku[r.sku]).filter(Boolean).slice(0, ROW_SIZE);
      probs = Object.fromEntries(ranked.map((r) => [r.sku, r.p]));
    }
  }
  if (!picks) {
    // OFF mode: popularity. ON but cold: local exploration.
    const sorted = [...pool].sort((a, b) =>
      S.jevOn ? localScore(b) - localScore(a) : (b.rating || 0) - (a.rating || 0));
    picks = sorted.slice(0, ROW_SIZE);
  }
  picks.forEach((p) => S.seen.add(p.sku));

  row.querySelectorAll(".shimmer").forEach((el) => el.remove());
  picks.forEach((p) => {
    const pct = probs[p.sku] != null ? Math.round(probs[p.sku] * 100) : null;
    const badge = S.jevOn
      ? badgeFor(pct, S.signals.length < 2)
      : `<span class="badge cat">${esc(p.category)}</span>`;
    const wrap = document.createElement("div");
    wrap.innerHTML = cardHTML(p, badge);
    const card = wrap.firstElementChild;
    row.appendChild(card);
    attachCard(card);
  });
}

async function rankViaJev(cands) {
  try {
    const interests = topCats(3)
      .map(([c, s]) => `${c} ${Math.round(s * 100)}%`).join(", ") || "cold start";
    const res = await fetch("/api/rank", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        interests,
        candidates: cands.map((c) => ({
          sku: c.sku, title: c.title, variant: c.variant,
          category: c.category, price: c.price, blurb: c.blurb,
        })),
      }),
    });
    const data = await res.json();
    return data.ranking && data.ranking.length ? data.ranking : null;
  } catch {
    return null;
  }
}

/* ---------- signals -> profile ---------- */
const WEIGHTS = { dwell: (s) => Math.min(s.dwellMs / 3000, 1), click: () => 1.0, cart: () => 1.5, linger: () => 0.3 };

function emitSignal(s) {
  const p = S.products.find((x) => x.sku === s.sku);
  if (!p) return;
  const w = (WEIGHTS[s.type] || (() => 0.5))(s);
  S.cats[p.category] = (S.cats[p.category] || 0) + w;
  S.skus[s.sku] = (S.skus[s.sku] || 0) + w;
  S.signals.push(s);
  if (S.signals.length > 20) S.signals.shift();
  renderGhost();
  clearTimeout(S.profileTimer);
  S.profileTimer = setTimeout(refreshJevProfile, PROFILE_DEBOUNCE_MS);
}

function topCats(n) {
  const max = Math.max(0.0001, ...Object.values(S.cats));
  return Object.entries(S.cats)
    .map(([c, v]) => {
      const local = v / max;
      const jev = S.jevProbs[c];
      const blended = jev != null ? 0.6 * jev + 0.4 * local : local;
      return [c, blended, jev != null];
    })
    .sort((a, b) => b[1] - a[1])
    .slice(0, n);
}

async function refreshJevProfile() {
  const tops = topCats(3);
  if (!tops.length || !S.signals.length) return;
  try {
    const res = await fetch("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        signals: S.signals.slice(-8),
        topCats: tops.map(([c]) => c),
      }),
    });
    const data = await res.json();
    if (data.probs && Object.keys(data.probs).length) {
      S.jevProbs = data.probs;
      renderGhost();
    }
  } catch { /* profile stays local on failure */ }
}

function renderGhost() {
  const box = $("#ghostBars");
  const tops = topCats(5);
  if (!tops.length) {
    box.innerHTML = `<p class="empty">No signals yet — go browse.</p>`;
  } else {
    box.innerHTML = tops.map(([c, s, isJev]) => `
    <div class="ghost-row${isJev ? " jev" : ""}">
      <div class="lbl"><span>${esc(c)}</span><span>${Math.round(s * 100)}%</span></div>
      <div class="bar"><div class="fill" style="width:${Math.round(s * 100)}%"></div></div>
    </div>`).join("");
  }
  // mobile strip + bottom sheet mirror the same state
  const chips = $("#stripChips");
  if (chips) {
    chips.innerHTML = tops.length
      ? tops.slice(0, 3).map(([c, s, isJev]) =>
          `<span class="chip${isJev ? " jev" : ""}">${esc(c)} ${Math.round(s * 100)}%</span>`).join("")
      : `<span class="strip-empty">Browse — Jev starts reading you</span>`;
  }
  const sb = $("#sheetBars");
  if (sb) sb.innerHTML = box.innerHTML;
}

/* ---------- linger detection (slow-scroll corroboration) ---------- */
let lastY = window.scrollY, lastT = performance.now(), scrollDist = 0, scrollWinT = performance.now();
window.addEventListener("scroll", () => {
  const now = performance.now();
  scrollDist += Math.abs(window.scrollY - lastY);
  lastY = window.scrollY; lastT = now;
  if (now - scrollWinT > 1500) { scrollDist = 0; scrollWinT = now; }
}, { passive: true });

setInterval(() => {
  const now = performance.now();
  if (now - scrollWinT < 1500 || scrollDist > 220) { scrollDist = 0; scrollWinT = now; return; }
  if (now - S.lingerAt < 5000) return;
  // slow scroll: find row nearest viewport middle
  const mid = window.scrollY + window.innerHeight / 2;
  let best = null, bestD = 1e9;
  document.querySelectorAll(".row").forEach((r) => {
    const d = Math.abs(r.offsetTop + r.offsetHeight / 2 - mid);
    if (d < bestD) { bestD = d; best = r; }
  });
  if (best && bestD < window.innerHeight / 2) {
    const cards = [...best.querySelectorAll(".card[data-sku]")].slice(0, 2);
    if (cards.length) {
      S.lingerAt = now;
      cards.forEach((c) => emitSignal({ type: "linger", sku: c.dataset.sku }));
    }
  }
  scrollDist = 0; scrollWinT = now;
}, 2000);

/* ---------- metrics / toggle / reset ---------- */
function renderMetrics() {
  document.querySelectorAll("[data-mode]").forEach((col) => {
    const on = col.dataset.mode === "on";
    const m = on ? S.metrics.on : S.metrics.off;
    col.classList.toggle("active", on === S.jevOn);
    col.querySelector('[data-m="hovers"]').textContent = m.hovers;
    col.querySelector('[data-m="dwell"]').textContent =
      m.hovers ? (m.dwellMs / m.hovers / 1000).toFixed(1) + "s" : "–";
    col.querySelector('[data-m="clicks"]').textContent = m.clicks;
    col.querySelector('[data-m="carts"]').textContent = m.carts;
  });
}

function setJev(on) {
  S.jevOn = on;
  $("#jevSwitch").classList.toggle("on", on);
  $("#jevSwitch").setAttribute("aria-checked", String(on));
  $("#jevModeLabel").textContent = on ? "adaptive" : "popularity";
  const banner = $("#feedBanner");
  banner.classList.toggle("off", !on);
  $("#feedBannerText").textContent = on
    ? "Jev adaptive ranking is ON — rows ahead are picked for you."
    : "Jev is OFF — rows ahead use plain popularity ranking.";
  renderMetrics();
}

let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 2200);
}

function rebuild() {
  $("#grid").innerHTML = "";
  $("#sentinel").classList.remove("hidden");
  $("#endMsg").classList.add("hidden");
  resetState();
  // queue reshuffled per session for variety
  for (let i = S.queue.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [S.queue[i], S.queue[j]] = [S.queue[j], S.queue[i]];
  }
  renderGhost();
  renderMetrics();
  appendRows(3);
  window.scrollTo(0, 0);
}

/* ---------- boot ---------- */
$("#jevSwitch").addEventListener("click", () => setJev(!S.jevOn));
$("#resetBtn").addEventListener("click", () => { rebuild(); toast("Session reset"); });
$("#reshuffleBtn").addEventListener("click", rebuild);

/* bottom sheet (mobile tracker detail) */
const sheet = $("#sheet"), sheetBack = $("#sheetBack");
function setSheet(open) {
  sheet.hidden = !open;
  sheetBack.hidden = !open;
  document.body.classList.toggle("noscroll", open);
}
$("#stripBtn").addEventListener("click", () => setSheet(true));
$("#sheetClose").addEventListener("click", () => setSheet(false));
sheetBack.addEventListener("click", () => setSheet(false));
window.addEventListener("keydown", (e) => { if (e.key === "Escape") setSheet(false); });

const observer = new IntersectionObserver((entries) => {
  if (entries[0].isIntersecting && !S.loading && S.queue.length) {
    S.loading = true;
    setTimeout(() => { appendRows(2); S.loading = false; }, 250);
  }
}, { rootMargin: "600px" });

(async function boot() {
  await loadCatalog();
  renderGhost();
  renderMetrics();
  appendRows(3);
  observer.observe($("#sentinel"));
})();
