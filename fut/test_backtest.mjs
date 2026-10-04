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

// Hourly series from release for `hours` hours, price from f(hourIndex).
function series(hours, f, start = REL) {
  const s = [];
  for (let h = 0; h < hours; h++) s.push({ t: start + h * H, p: f(h) });
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

test("imported prices win over collected ones in the same hour", () => {
  const c = card();
  const collected = [
    { karte: c.karte, promo: c.promo, ts: REL + 10 * 60e3, preis: 1000, plattform: "konsole" },
    { karte: c.karte, promo: c.promo, ts: REL + H, preis: 1100, plattform: "konsole" },
  ];
  const imported = [{ karte: "Yamal", promo: "TOTW1", ts: REL, preis: 900, plattform: "konsole" },
    { karte: "Niemand", promo: "TOTW1", ts: REL, preis: 900, plattform: "konsole" }];
  const { series: s, unmatched } = BT.buildSeries([c], collected, imported);
  const k = BT.cardKey(c) + "|konsole";
  assert.deepEqual(s[k].map((x) => [x.t, x.p, x.src]), [[REL, 900, "import"], [REL + H, 1100, "collected"]]);
  assert.deepEqual(unmatched, { "Niemand (TOTW1)": 1 });
});

test("per card: best/worst buy and sell, tax, out-of-packs prices", () => {
  // 1000 at release, falls to 600 at hour 50, rises to 1500 at hour 120, then 700 at hour 200.
  const f = (h) => (h === 50 ? 600 : h === 120 ? 1500 : h === 200 ? 700 : h === 30 ? 1600 : 1000);
  const now = REL + 300 * H;
  const r = BT.analyzeCard(card(), series(300, f), now);
  assert.equal(r.status, "ok");
  assert.equal(r.bestBuy.p, 600);
  assert.equal(r.bestBuy.hSince, 50);
  assert.equal(r.bestSell.p, 1500);  // highest after the best buy, not the 1600 before it
  assert.equal(r.worstBuy.p, 1600);
  assert.equal(r.worstSell.p, 600);  // lowest after the worst buy
  assert.equal(r.bestTrade.coins, 1500 * 0.95 - 600);
  assert.ok(Math.abs(r.bestTrade.pct - 1.375) < 1e-9); // 825 / 600
  assert.equal(r.releasePrice, 1000);
  assert.equal(r.outPrice, 1000);           // hour 168
  assert.equal(r.after[1].p, 1000);         // hour 192
  assert.equal(r.after[1].chg, 0);
  assert.equal(r.after[7], null);           // hour 336 is past `now` → missing, not guessed
  const wd = BT.berlin(REL + 50 * H);
  assert.equal(r.bestBuy.weekday, wd.weekday);
  assert.equal(r.bestBuy.hour, wd.hour);
});

test("gaps are reported, not filled", () => {
  const s = series(100, () => 1000).filter((x) => x.t < REL + 20 * H || x.t >= REL + 30 * H);
  const r = BT.analyzeCard(card(), s, REL + 99 * H);
  assert.equal(r.status, "luecken");
  assert.equal(r.longestGap, 10);
  assert.equal(r.gaps[0].from, REL + 20 * H);
  const none = BT.analyzeCard(card(), [], REL + 99 * H);
  assert.equal(none.status, "keine-daten");
  assert.equal(none.bestBuy, undefined);
  // Data starting late: the hours before the first reading are a gap too.
  const late = BT.analyzeCard(card(), series(50, () => 1000, REL + 50 * H), REL + 99 * H);
  assert.equal(late.gaps[0].from, REL);
  assert.equal(late.releasePrice, null);
});

test("curve is relative to the release price", () => {
  const a = BT.analyzeCard(card(), series(48, (h) => 1000 - h * 10), REL + 47 * H);
  const b = BT.analyzeCard(card({ karte: "B" }), series(48, (h) => 2000 - h * 20), REL + 47 * H);
  const c = BT.curve([a, b], 47);
  assert.equal(c[0].mean, 1);
  assert.ok(Math.abs(c[10].mean - 0.9) < 1e-9);
  assert.equal(c[10].n, 2);
});

test("heatmap finds the cheap hour against the card's own level", () => {
  // Every day 3 % cheaper at 04:00 German time, on a rising trend.
  const s = series(24 * 14, (h) => {
    const b = BT.berlin(REL + h * H);
    return (1000 + h) * (b.hour === 4 ? 0.97 : 1);
  });
  const r = BT.analyzeCard(card(), s, REL + 24 * 14 * H);
  const cells = BT.heatmap([r]);
  const ex = BT.extremeCells(cells, 1);
  assert.equal(ex.cheapest.hour, 4);
  assert.ok(ex.cheapest.dev < -0.02);
});

test("rule: buy in the last hour in packs, sell X days later, net of tax", () => {
  // 1000 until packs end, then +10 % per day.
  const f = (h) => (h < 168 ? 1000 : 1000 * (1 + 0.1 * ((h - 167) / 24)));
  const r = BT.analyzeCard(card(), series(24 * 20, f), REL + 24 * 20 * H);
  const rows = BT.ruleTest([r], 10);
  assert.equal(rows[0].n, 1);
  // after 1 day: 1100 * 0.95 = 1045 → +4.5 %
  assert.ok(Math.abs(rows[0].meanPct - 0.045) < 1e-9);
  assert.equal(rows[0].wins, 1);
  // a flat price loses the 5 % tax
  const flat = BT.analyzeCard(card(), series(24 * 20, () => 1000), REL + 24 * 20 * H);
  const fr = BT.ruleTest([flat], 3)[2];
  assert.equal(fr.hitRate, 0);
  assert.ok(Math.abs(fr.meanPct + 0.05) < 1e-9);
});

test("groups", () => {
  assert.equal(BT.ratingBucket(85), "unter 86");
  assert.equal(BT.ratingBucket(88), "86–88");
  assert.equal(BT.ratingBucket(89), "89+");
  assert.equal(BT.positionGroup("LWB"), "Abwehr");
  assert.equal(BT.positionGroup("CAM"), "Mittelfeld");
  assert.equal(BT.promoType("DFG Team 1"), "DFG");
  const r = BT.analyzeCard(card(), series(24 * 10, () => 1000), REL + 24 * 10 * H);
  const g = BT.groupStats([r, BT.analyzeCard(card({ promo: "DFG Team 1" }), [], REL)], (c) => BT.promoType(c.promo), 3);
  assert.deepEqual(g.map((x) => [x.key, x.cards, x.withData]), [["DFG", 1, 0], ["TOTW", 1, 1]]);
});
