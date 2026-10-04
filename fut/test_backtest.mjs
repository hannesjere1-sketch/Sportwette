// Tests for static-app/backtest-core.js with made-up prices whose answer is known.
//   node --test fut/test_backtest.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const BT = require("../static-app/backtest-core.js");
const H = BT.H, DAY = BT.DAY;

const card = (over = {}) => ({
  karte: "Lamine Yamal", promo: "TOTW 1", gold_id: 1, spezial_rating: 91, position: "RW",
  liga: "LALIGA EA SPORTS", release: "2026-09-16T17:00:00Z", aus_packs: "2026-09-23T17:00:00Z", ...over
});
const REL = Date.parse("2026-09-16T17:00:00Z");
const OUT = Date.parse("2026-09-23T17:00:00Z");

const STEP = 4 * H;
const START = REL - 5 * DAY;       // window: 5 days before release …
const END = REL + 7 * DAY;         // … to 7 days after
const NOW = END + DAY;             // window closed
const BLOCKS = (END - START) / STEP; // 72

// One price per 4-hour block over the whole window, price from f(blockIndex).
// Block 30 is the release block.
function series(f, n = BLOCKS) {
  const s = [];
  for (let i = 0; i < n; i++) s.push({ t: START + i * STEP, p: f(i) });
  return s;
}

test("German time: weekday, hour and summer time", () => {
  const b = BT.berlin(REL); // Wed 16 Sep 2026, 17:00 UTC = 19:00 CEST
  assert.equal(b.weekday, 2);
  assert.equal(b.hour, 19);
  assert.equal(BT.fromBerlin(2026, 9, 16, 19, 0), REL);
  // Winter time: 1 Dec 12:00 Berlin = 11:00 UTC
  assert.equal(BT.fromBerlin(2026, 12, 1, 12, 0), Date.parse("2026-12-01T11:00:00Z"));
});

test("CSV: separators, German dates and prices, platforms, errors", () => {
  const csv = [
    "karte;promo;timestamp;preis;plattform",
    "Lamine Yamal;TOTW 1;23.09.2026 19:00;12.500;PS5",
    'Yamal;totw1;2026-09-23T17:00:00Z;"12,5k";pc',
    "Lamine Yamal;TOTW 1;gestern;100;ps",
    "Lamine Yamal;TOTW 1;2026-09-23 19:00;abc;switch",
  ].join("\n");
  const { rows, errors } = BT.parseCsv(csv);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].ts, OUT); // 19:00 German summer time = 17:00 UTC
  assert.equal(rows[0].preis, 12500);
  assert.equal(rows[0].plattform, "konsole");
  assert.equal(rows[1].ts, OUT);
  assert.equal(rows[1].preis, 12500);
  assert.equal(rows[1].plattform, "pc");
  assert.deepEqual(errors.map((e) => e.line), [4, 5]);
  assert.match(errors[1].msg, /Preis/);
  assert.match(errors[1].msg, /Plattform/);
  assert.match(BT.parseCsv("karte,preis\nx,1").errors[0].msg, /Spalte fehlt/);
});

test("matching: accents, promo spelling, unambiguous short names only", () => {
  const cards = [card(), card({ karte: "Martin Ødegaard", promo: "TOTW 3" }),
    card({ karte: "Luka Modrić", promo: "TOTW 3" }), card({ karte: "Lucy Bronze" }), card({ karte: "Lewis Dunk" })];
  const m = BT.makeMatcher(cards);
  assert.equal(m({ karte: "martin odegaard", promo: "totw3" }).karte, "Martin Ødegaard");
  assert.equal(m({ karte: "Modric", promo: "Team of the Week 3" }).karte, "Luka Modrić");
  assert.equal(m({ karte: "Yamal", promo: "TOTW 1" }).karte, "Lamine Yamal");
  assert.equal(m({ karte: "Yamal", promo: "TOTW 2" }), null); // wrong promo
  assert.equal(m({ karte: "L", promo: "TOTW 1" }), null);     // too short, ambiguous
  assert.equal(BT.normPromo("Destined for Glory Team 2"), "dfg2");
  assert.equal(BT.normPromo("DFG 2"), "dfg2");
});

test("readings become 4-hour blocks of the card's window, median, outside dropped", () => {
  const c = card();
  const row = (ts, preis) => ({ karte: "Yamal", promo: "TOTW1", ts, preis, plattform: "konsole" });
  const rows = [row(START - H, 999), row(START + 31 * 60e3, 100), row(START + 2 * H, 300), row(START + 3 * H, 200),
    row(START + 9 * H, 50), row(END, 999), { karte: "Niemand", promo: "TOTW1", ts: START, preis: 1, plattform: "konsole" }];
  const { series: s, unmatched } = BT.buildSeries([c], rows);
  assert.deepEqual(s[BT.cardKey(c)], [{ t: START, p: 200 }, { t: START + 2 * STEP, p: 50 }]);
  assert.deepEqual(unmatched, { "Niemand (TOTW1)": 1 });
  // blocks start 17:00 UTC → 19, 23, 03 … German summer time
  assert.equal(BT.berlin(START).hour, 19);
});

test("per card: best/worst buy and sell over the window, tax, checkpoints", () => {
  // 1000 everywhere; 600 at block 40, 1500 at block 60, 1600 at block 10, 700 at block 65.
  const f = (i) => ({ 10: 1600, 40: 600, 60: 1500, 65: 700 })[i] || 1000;
  const r = BT.analyzeCard(card(), series(f), NOW);
  assert.equal(r.status, "ok");
  assert.equal(r.expected, 72);
  assert.equal(r.bestBuy.p, 600);
  assert.equal(r.bestBuy.hSince, 40);           // (40 - 30) blocks × 4 h
  assert.equal(r.bestSell.p, 1500);            // highest after the best buy, not the 1600 before
  assert.equal(r.worstBuy.p, 1600);
  assert.equal(r.worstBuy.hSince, -80);        // before the release
  assert.equal(r.worstSell.p, 600);            // lowest after the worst buy
  assert.equal(r.bestTrade.coins, 1500 * 0.95 - 600);
  assert.ok(Math.abs(r.bestTrade.pct - 1.375) < 1e-9); // 825 / 600
  assert.equal(r.releasePrice, 1000);
  assert.equal(r.outPrice, 1000);              // last block before packs close
  assert.equal(r.marks[-5].t, START);
  assert.equal(r.marks[0].t, REL);
  assert.equal(r.marks[1].t, REL + DAY);
  assert.equal(r.marks[7].t, END - STEP);
  assert.equal(r.marks[1].chg, 0);
  const wd = BT.berlin(START + 40 * STEP);
  assert.equal(r.bestBuy.weekday, wd.weekday);
  assert.equal(r.bestBuy.hour, wd.hour);
});

test("missing blocks are reported, not filled; open windows only count the past", () => {
  const s = series(() => 1000).filter((b, i) => i !== 5 && i !== 6 && i !== 30);
  const r = BT.analyzeCard(card(), s, NOW);
  assert.equal(r.status, "luecken");
  assert.deepEqual(r.gaps.map((g) => [g.from, g.hours]), [[START + 5 * STEP, 8], [REL, 4]]);
  assert.equal(r.releasePrice, null);          // release block missing → no guess
  assert.equal(r.marks[0], null);
  assert.equal(r.marks[1].chg, null);          // no release price, no relative change
  const none = BT.analyzeCard(card(), [], NOW);
  assert.equal(none.status, "keine-daten");
  assert.equal(none.bestBuy, undefined);
  // Window still running: 10 blocks have passed, all present → no gap, open.
  const open = BT.analyzeCard(card(), series(() => 1000, 10), START + 10 * STEP + H);
  assert.equal(open.status, "ok");
  assert.equal(open.expected, 10);
  assert.equal(open.open, true);
});

test("curve is relative to the release price, before and after it", () => {
  const a = BT.analyzeCard(card(), series((i) => 1000 + (i - 30) * 10), NOW);
  const b = BT.analyzeCard(card({ karte: "B" }), series((i) => 2000 + (i - 30) * 20), NOW);
  const c = BT.curve([a, b]);
  const at = (h) => c.find((p) => p.h === h);
  assert.equal(at(0).mean, 1);
  assert.ok(Math.abs(at(-120).mean - 0.7) < 1e-9);
  assert.ok(Math.abs(at(40).mean - 1.1) < 1e-9);
  assert.equal(at(40).n, 2);
});

test("heatmap finds the cheap block against the card's own level", () => {
  // Every day 3 % cheaper in the block starting 03:00 German time, on a rising trend.
  const s = series((i) => (1000 + i * 5) * (BT.berlin(START + i * STEP).hour === 3 ? 0.97 : 1));
  const cells = BT.heatmap([BT.analyzeCard(card(), s, NOW)]);
  assert.deepEqual([...new Set(cells.map((c) => c.hour))].sort((a, b) => a - b), [3, 7, 11, 15, 19, 23]);
  const ex = BT.extremeCells(cells, 1);
  assert.equal(ex.cheapest.hour, 3);
  assert.ok(ex.cheapest.dev < -0.02);
});

test("rule after packs close has no data in the window: n = 0, no guess", () => {
  const r = BT.analyzeCard(card(), series(() => 1000), NOW);
  const rows = BT.ruleTest([r], 10);
  assert.ok(rows.every((x) => x.n === 0 && x.hitRate === null));
  // With a window that reaches past packs close it does compute (net of tax).
  const w = { step: STEP, before: 5 * DAY, after: 10 * DAY };
  const blocks = [];
  for (let i = 0; i < (15 * DAY) / STEP; i++) blocks.push({ t: START + i * STEP, p: START + i * STEP >= END ? 1100 : 1000 });
  const long = BT.analyzeCard(card(), blocks, START + 16 * DAY, w);
  const day1 = BT.ruleTest([long], 1)[0];
  assert.equal(day1.n, 1);
  assert.ok(Math.abs(day1.meanPct - 0.045) < 1e-9); // 1100 × 0.95 / 1000 − 1
});

test("groups", () => {
  assert.equal(BT.ratingBucket(85), "unter 86");
  assert.equal(BT.ratingBucket(88), "86–88");
  assert.equal(BT.ratingBucket(89), "89+");
  assert.equal(BT.positionGroup("LWB"), "Abwehr");
  assert.equal(BT.positionGroup("CAM"), "Mittelfeld");
  assert.equal(BT.promoType("DFG Team 1"), "DFG");
  const r = BT.analyzeCard(card(), series((i) => (i < 30 ? 800 : 1000)), NOW);
  const g = BT.groupStats([r, BT.analyzeCard(card({ promo: "DFG Team 1" }), [], NOW)], (c) => BT.promoType(c.promo));
  assert.deepEqual(g.map((x) => [x.key, x.cards, x.withData]), [["DFG", 1, 0], ["TOTW", 1, 1]]);
  assert.ok(Math.abs(g[1].pre + 0.2) < 1e-9);      // 5 days before: 800 vs 1000 at release
  assert.equal(g[1].lowH, -120);
});
