// Backtest for the gold base cards of TOTW / Destined for Glory players.
// Pure functions only (no DOM), shared by backtest.html and the Node tests in
// fut/test_backtest.mjs. All times are epoch milliseconds (UTC); weekdays and
// hours are German time (Europe/Berlin), as on the rest of the site.
(function (root) {
  "use strict";

  var H = 3600e3;
  var DAY = 24 * H;
  var TAX = 0.95; // EA keeps 5 % of every sale
  // The price history (fut/fetch_futalert.py) covers 5 days before to 7 days
  // after the special card's release, in 4-hour blocks counted from the
  // window start. Everything here uses the same window and blocks.
  var WINDOW = { step: 4 * H, before: 5 * DAY, after: 7 * DAY };
  var WD = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

  // --- German time -------------------------------------------------------

  var fmt = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Berlin", hourCycle: "h23", weekday: "short",
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit"
  });
  var EN_WD = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4, Sat: 5, Sun: 6 };

  function berlin(ms) {
    var o = {};
    fmt.formatToParts(new Date(ms)).forEach(function (p) { o[p.type] = p.value; });
    return {
      year: +o.year, month: +o.month, day: +o.day, hour: +o.hour, minute: +o.minute,
      weekday: EN_WD[o.weekday]
    };
  }

  // Wall-clock time in Berlin -> epoch ms. Two passes settle the DST offset.
  function fromBerlin(y, mo, d, h, mi) {
    var guess = Date.UTC(y, mo - 1, d, h, mi || 0);
    var t = guess;
    for (var i = 0; i < 2; i++) {
      var b = berlin(t);
      var shown = Date.UTC(b.year, b.month - 1, b.day, b.hour, b.minute);
      t += guess - shown;
    }
    return t;
  }

  // --- CSV import ----------------------------------------------------------

  function splitLine(line, sep) {
    var out = [], cur = "", q = false;
    for (var i = 0; i < line.length; i++) {
      var c = line[i];
      if (q) {
        if (c === '"' && line[i + 1] === '"') { cur += '"'; i++; }
        else if (c === '"') q = false;
        else cur += c;
      } else if (c === '"') q = true;
      else if (c === sep) { out.push(cur); cur = ""; }
      else cur += c;
    }
    out.push(cur);
    return out.map(function (s) { return s.trim(); });
  }

  // ISO with Z/offset is taken as is; anything without a zone is German time:
  // "2026-09-23 19:00", "2026-09-23T19:00", "23.09.2026 19:00".
  function parseTime(s) {
    s = String(s || "").trim();
    if (!s) return null;
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})$/i.test(s)) {
      var t = Date.parse(s);
      return isNaN(t) ? null : t;
    }
    var m = /^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ](\d{1,2}):(\d{2})(?::\d{2})?)?$/.exec(s);
    if (m) return fromBerlin(+m[1], +m[2], +m[3], +(m[4] || 0), +(m[5] || 0));
    m = /^(\d{1,2})\.(\d{1,2})\.(\d{2,4}),?(?:\s+(\d{1,2}):(\d{2})(?::\d{2})?)?$/.exec(s);
    if (m) {
      var y = +m[3]; if (y < 100) y += 2000;
      return fromBerlin(y, +m[2], +m[1], +(m[4] || 0), +(m[5] || 0));
    }
    return null;
  }

  // "12500", "12.500", "12 500", "12,5k", "1.2m" -> coins.
  function parsePrice(s) {
    s = String(s || "").trim().toLowerCase().replace(/\s|'/g, "");
    if (!s) return null;
    var mult = 1;
    if (/[km]$/.test(s)) {
      mult = s.slice(-1) === "k" ? 1e3 : 1e6;
      s = s.slice(0, -1).replace(",", ".");
      var f = parseFloat(s);
      return isFinite(f) && f > 0 && /^[\d.]+$/.test(s) ? Math.round(f * mult) : null;
    }
    if (!/^[\d.,]+$/.test(s)) return null;
    var n = parseInt(s.replace(/[.,]/g, ""), 10);
    return n > 0 ? n : null;
  }

  function parsePlatform(s) {
    s = String(s || "").trim().toLowerCase();
    if (/^(pc|computer|origin|ea ?app)$/.test(s)) return "pc";
    if (/^(ps|ps4|ps5|playstation|konsole|console|xbox|xb|xbox ?series|cross|crossplay)$/.test(s)) return "konsole";
    return null;
  }

  function parseCsv(text) {
    var lines = String(text || "").replace(/^﻿/, "").split(/\r?\n/);
    var rows = [], errors = [];
    var head = -1;
    for (var i = 0; i < lines.length; i++) if (lines[i].trim()) { head = i; break; }
    if (head < 0) return { rows: rows, errors: [{ line: 0, msg: "Leer" }] };
    var sep = (lines[head].split(";").length > lines[head].split(",").length) ? ";" : ",";
    var cols = splitLine(lines[head], sep).map(function (c) { return c.toLowerCase(); });
    var idx = {};
    ["karte", "promo", "timestamp", "preis", "plattform", "quelle"].forEach(function (k) { idx[k] = cols.indexOf(k); });
    var missing = ["karte", "promo", "timestamp", "preis", "plattform"].filter(function (k) { return idx[k] < 0; });
    if (missing.length) {
      return { rows: rows, errors: [{ line: head + 1, msg: "Spalte fehlt: " + missing.join(", ") }] };
    }
    for (var j = head + 1; j < lines.length; j++) {
      if (!lines[j].trim()) continue;
      var f = splitLine(lines[j], sep);
      var t = parseTime(f[idx.timestamp]);
      var p = parsePrice(f[idx.preis]);
      var pl = parsePlatform(f[idx.plattform]);
      var bad = [];
      if (!f[idx.karte]) bad.push("karte leer");
      if (t === null) bad.push("Zeit „" + (f[idx.timestamp] || "") + "“ unlesbar");
      if (p === null) bad.push("Preis „" + (f[idx.preis] || "") + "“ unlesbar");
      if (pl === null) bad.push("Plattform „" + (f[idx.plattform] || "") + "“ (ps/konsole oder pc)");
      if (bad.length) { errors.push({ line: j + 1, msg: bad.join("; ") }); continue; }
      rows.push({
        karte: f[idx.karte], promo: f[idx.promo] || "", ts: t, preis: p, plattform: pl,
        quelle: idx.quelle >= 0 && f[idx.quelle] ? f[idx.quelle] : "import"
      });
    }
    return { rows: rows, errors: errors };
  }

  // --- Matching rows to cards ------------------------------------------------

  function norm(s) {
    return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
      .toLowerCase().replace(/ø/g, "o").replace(/ß/g, "ss").replace(/[^a-z0-9]/g, "");
  }

  function normPromo(s) {
    var n = norm(s);
    var d = (n.match(/(\d+)$/) || [])[1] || "";
    if (/dfg|destined|glory/.test(n)) return "dfg" + d;
    if (/totw|teamoftheweek/.test(n)) return "totw" + d;
    return n;
  }

  function cardKey(c) { return normPromo(c.promo) + "|" + norm(c.karte); }

  function makeMatcher(cards) {
    var exact = {}, byPromo = {};
    cards.forEach(function (c) {
      exact[cardKey(c)] = c;
      var p = normPromo(c.promo);
      (byPromo[p] = byPromo[p] || []).push(c);
    });
    return function (row) {
      var p = normPromo(row.promo), n = norm(row.karte);
      if (exact[p + "|" + n]) return exact[p + "|" + n];
      // "Yamal" for "Lamine Yamal": accept only an unambiguous partial match.
      var hits = (byPromo[p] || []).filter(function (c) {
        var cn = norm(c.karte);
        return n.length >= 3 && (cn.indexOf(n) >= 0 || n.indexOf(cn) >= 0);
      });
      return hits.length === 1 ? hits[0] : null;
    };
  }

  // --- Series ----------------------------------------------------------------

  function median(a) {
    if (!a.length) return null;
    var s = a.slice().sort(function (x, y) { return x - y; });
    var m = s.length >> 1;
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  }
  function mean(a) {
    if (!a.length) return null;
    var s = 0; a.forEach(function (x) { s += x; }); return s / a.length;
  }

  function win(card, w) {
    w = w || WINDOW;
    var release = Date.parse(card.release);
    return { release: release, out: Date.parse(card.aus_packs), start: release - w.before, end: release + w.after, step: w.step };
  }

  // Readings -> one price per block of the card's window (median), sorted.
  // Readings outside the window are dropped.
  function toBlocks(rows, card, w) {
    var x = win(card, w), by = {};
    rows.forEach(function (r) {
      if (r.ts < x.start || r.ts >= x.end) return;
      var i = Math.floor((r.ts - x.start) / x.step);
      (by[i] = by[i] || []).push(r.preis);
    });
    return Object.keys(by).map(Number).sort(function (a, b) { return a - b; })
      .map(function (i) { return { t: x.start + i * x.step, p: median(by[i]) }; });
  }

  // Rows of one platform -> {cardKey: blocks}, plus rows that fit no card.
  function buildSeries(cards, rows, w) {
    var match = makeMatcher(cards), per = {}, unmatched = {};
    rows.forEach(function (r) {
      var c = match(r);
      if (!c) { var u = r.karte + " (" + r.promo + ")"; unmatched[u] = (unmatched[u] || 0) + 1; return; }
      var k = cardKey(c);
      (per[k] = per[k] || { card: c, rows: [] }).rows.push(r);
    });
    var series = {};
    Object.keys(per).forEach(function (k) { series[k] = toBlocks(per[k].rows, per[k].card, w); });
    return { series: series, unmatched: unmatched };
  }

  // The block that contains instant `ms`, or null when it has no price.
  function blockAt(series, x, ms) {
    var t = x.start + Math.floor((ms - x.start) / x.step) * x.step;
    for (var i = 0; i < series.length; i++) if (series[i].t === t) return series[i];
    return null;
  }

  function profit(buy, sell) {
    var c = sell * TAX - buy;
    return { coins: c, pct: c / buy };
  }

  function point(x, release) {
    if (!x) return null;
    var b = berlin(x.t);
    return { t: x.t, p: x.p, weekday: b.weekday, hour: b.hour, hSince: Math.round((x.t - release) / H) };
  }

  // Price checkpoints relative to the release, in days (0 = release block,
  // 7 = last block before the window ends, i.e. before packs close).
  var MARKS = [-5, 0, 1, 3, 7];

  // --- Per card --------------------------------------------------------------

  function analyzeCard(card, series, now, w) {
    var x = win(card, w);
    var until = Math.min(x.end, Math.floor((now - x.start) / x.step) * x.step + x.start);
    var s = (series || []).filter(function (b) { return b.t >= x.start && b.t < until; });
    var r = { card: card, n: s.length, release: x.release, out: x.out, start: x.start, end: x.end, step: x.step };
    r.expected = Math.max(0, Math.round((until - x.start) / x.step));
    r.coverage = r.expected ? s.length / r.expected : 0;
    r.open = until < x.end; // window still running
    // Every missing block is a gap; consecutive ones are reported together.
    var gaps = [], prev = x.start - x.step;
    s.concat([{ t: until }]).forEach(function (b) {
      var miss = Math.round((b.t - prev) / x.step) - 1;
      if (miss >= 1) gaps.push({ from: prev + x.step, hours: miss * x.step / H });
      prev = b.t;
    });
    r.gaps = gaps;
    r.longestGap = gaps.reduce(function (m, g) { return Math.max(m, g.hours); }, 0);
    if (!s.length) { r.status = "keine-daten"; r.marks = {}; return r; }
    r.status = gaps.length ? "luecken" : "ok";
    r.median = median(s.map(function (b) { return b.p; }));

    var lo = s[0], hi = s[0];
    s.forEach(function (b) { if (b.p < lo.p) lo = b; if (b.p > hi.p) hi = b; });
    function after(from, better) {
      var res = null;
      s.forEach(function (b) { if (b.t > from.t && (!res || better(b, res))) res = b; });
      return res;
    }
    var bestSell = after(lo, function (a, b) { return a.p > b.p; });
    var worstSell = after(hi, function (a, b) { return a.p < b.p; });
    r.bestBuy = point(lo, x.release);
    r.bestSell = point(bestSell, x.release);
    r.worstBuy = point(hi, x.release);
    r.worstSell = point(worstSell, x.release);
    r.bestTrade = bestSell ? profit(lo.p, bestSell.p) : null;
    r.worstTrade = worstSell ? profit(hi.p, worstSell.p) : null;

    var rel = blockAt(s, x, x.release);
    r.releasePrice = rel ? rel.p : null;
    // Last block before packs close (the window ends with them by default).
    var out = x.out <= x.end ? blockAt(s, x, x.out - 1) : null;
    r.outPrice = out ? out.p : null;
    r.marks = {};
    MARKS.forEach(function (d) {
      var ms = d < 0 ? x.start : d === 7 ? x.end - 1 : x.release + d * DAY;
      var b = blockAt(s, x, ms);
      r.marks[d] = b ? { p: b.p, t: b.t, chg: r.releasePrice ? b.p / r.releasePrice - 1 : null } : null;
    });
    r.series = s;
    return r;
  }

  // --- Patterns across cards --------------------------------------------------

  // Mean and median price relative to the release price, per block offset
  // (hours since release, negative before it).
  function curve(results) {
    var by = {};
    results.forEach(function (r) {
      if (!r.releasePrice || !r.series) return;
      r.series.forEach(function (b) {
        var h = Math.round((b.t - r.release) / H);
        (by[h] = by[h] || []).push(b.p / r.releasePrice);
      });
    });
    return Object.keys(by).map(Number).sort(function (a, b) { return a - b; })
      .map(function (h) { return { h: h, mean: mean(by[h]), median: median(by[h]), n: by[h].length }; });
  }

  // Each block's price against the card's own median over the surrounding
  // 72 hours, so a card that slides all week does not make Sunday look cheap.
  // A card's blocks are averaged per weekday x block start hour (German time)
  // first, then the median over cards is taken, so long histories do not
  // dominate. Only the hours that blocks start at appear.
  function heatmap(results) {
    var cells = {};
    results.forEach(function (r) {
      if (!r.series) return;
      var s = r.series, need = Math.ceil(DAY / r.step), own = {}, start = 0;
      if (s.length < need) return;
      for (var i = 0; i < s.length; i++) {
        while (s[start].t < s[i].t - 36 * H) start++;
        var w = [];
        for (var j = start; j < s.length && s[j].t <= s[i].t + 36 * H; j++) w.push(s[j].p);
        if (w.length < need) continue;
        var b = berlin(s[i].t), k = b.weekday + "-" + b.hour;
        (own[k] = own[k] || []).push(s[i].p / median(w) - 1);
      }
      Object.keys(own).forEach(function (k) { (cells[k] = cells[k] || []).push(mean(own[k])); });
    });
    return Object.keys(cells).map(function (k) {
      var p = k.split("-");
      return { weekday: +p[0], hour: +p[1], dev: median(cells[k]), n: cells[k].length };
    });
  }

  function extremeCells(cells, minCards) {
    var ok = cells.filter(function (c) { return c.dev !== null && c.n >= minCards; });
    if (!ok.length) return null;
    var lo = ok[0], hi = ok[0];
    ok.forEach(function (c) { if (c.dev < lo.dev) lo = c; if (c.dev > hi.dev) hi = c; });
    return { cheapest: lo, dearest: hi };
  }

  // "Buy in the last block before packs close, sell X days later", net of tax.
  // Needs prices after packs close; with the default window there are none,
  // and every row reports n = 0 rather than a guess.
  function ruleTest(results, maxDays) {
    var rows = [];
    for (var d = 1; d <= maxDays; d++) {
      var trades = [];
      results.forEach(function (r) {
        if (!r.series) return;
        var x = { start: r.start, step: r.step };
        var buy = blockAt(r.series, x, r.out - 1);
        var sell = buy && blockAt(r.series, x, buy.t + d * DAY);
        if (buy && sell) trades.push(profit(buy.p, sell.p));
      });
      var wins = trades.filter(function (t) { return t.coins > 0; }).length;
      rows.push({
        days: d, n: trades.length, wins: wins,
        hitRate: trades.length ? wins / trades.length : null,
        meanPct: mean(trades.map(function (t) { return t.pct; })),
        meanCoins: mean(trades.map(function (t) { return t.coins; }))
      });
    }
    return rows;
  }

  function ratingBucket(r) { return r < 86 ? "unter 86" : r <= 88 ? "86–88" : "89+"; }
  function positionGroup(p) {
    if (p === "GK") return "Torwart";
    if (/^(CB|LB|RB|LWB|RWB)$/.test(p)) return "Abwehr";
    if (/^(CDM|CM|CAM|LM|RM)$/.test(p)) return "Mittelfeld";
    return "Sturm";
  }
  function promoType(p) { return /dfg|destined/i.test(p) ? "DFG" : "TOTW"; }

  function groupStats(results, keyFn) {
    var g = {};
    results.forEach(function (r) { var k = keyFn(r.card); (g[k] = g[k] || []).push(r); });
    function avg(rs, f) {
      var v = rs.map(f).filter(function (x) { return x !== null && x !== undefined; });
      return v.length ? mean(v) : null;
    }
    return Object.keys(g).sort().map(function (k) {
      var rs = g[k], withData = rs.filter(function (r) { return r.n > 0; });
      return {
        key: k, cards: rs.length, withData: withData.length,
        bestPct: avg(withData, function (r) { return r.bestTrade && r.bestTrade.pct; }),
        pre: avg(withData, function (r) { return r.marks[-5] && r.marks[-5].chg; }),
        d1: avg(withData, function (r) { return r.marks[1] && r.marks[1].chg; }),
        d3: avg(withData, function (r) { return r.marks[3] && r.marks[3].chg; }),
        d7: avg(withData, function (r) { return r.marks[7] && r.marks[7].chg; }),
        lowH: median(withData.map(function (r) { return r.bestBuy.hSince; }))
      };
    });
  }

  root.BT = {
    H: H, DAY: DAY, TAX: TAX, WD: WD, WINDOW: WINDOW, MARKS: MARKS,
    berlin: berlin, fromBerlin: fromBerlin,
    parseCsv: parseCsv, parseTime: parseTime, parsePrice: parsePrice, parsePlatform: parsePlatform,
    norm: norm, normPromo: normPromo, cardKey: cardKey, makeMatcher: makeMatcher,
    median: median, mean: mean, win: win, toBlocks: toBlocks, buildSeries: buildSeries, blockAt: blockAt, profit: profit,
    analyzeCard: analyzeCard, curve: curve, heatmap: heatmap, extremeCells: extremeCells, ruleTest: ruleTest,
    ratingBucket: ratingBucket, positionGroup: positionGroup, promoType: promoType, groupStats: groupStats
  };
  if (typeof module !== "undefined" && module.exports) module.exports = root.BT;
})(typeof window !== "undefined" ? window : globalThis);
