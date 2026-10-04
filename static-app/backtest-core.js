// Backtest for the gold base cards of TOTW / Destined for Glory players.
// Pure functions only (no DOM), shared by backtest.html and the Node tests in
// fut/test_backtest.mjs. All times are epoch milliseconds (UTC); weekdays and
// hours are German time (Europe/Berlin), as on the rest of the site.
(function (root) {
  "use strict";

  var H = 3600e3;
  var DAY = 24 * H;
  var TAX = 0.95; // EA keeps 5 % of every sale
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

  // One price per clock hour (median of the readings in it), sorted.
  function hourly(points) {
    var by = {};
    points.forEach(function (pt) {
      var h = Math.floor(pt.ts / H) * H;
      (by[h] = by[h] || []).push(pt.preis);
    });
    return Object.keys(by).map(Number).sort(function (a, b) { return a - b; })
      .map(function (h) { return { t: h, p: median(by[h]) }; });
  }

  // Imported prices win over collected ones for the same card, platform and hour.
  function buildSeries(cards, collectedRows, importedRows) {
    var match = makeMatcher(cards);
    var store = {}, unmatched = {};
    function add(rows, layer) {
      rows.forEach(function (r) {
        var c = match(r);
        if (!c) { var u = r.karte + " (" + r.promo + ")"; unmatched[u] = (unmatched[u] || 0) + 1; return; }
        var k = cardKey(c) + "|" + r.plattform;
        var s = store[k] = store[k] || { collected: [], imported: [] };
        s[layer].push(r);
      });
    }
    add(collectedRows, "collected");
    add(importedRows, "imported");
    var series = {};
    Object.keys(store).forEach(function (k) {
      var imp = hourly(store[k].imported);
      var have = {};
      imp.forEach(function (x) { have[x.t] = 1; });
      var col = hourly(store[k].collected).filter(function (x) { return !have[x.t]; });
      series[k] = imp.map(function (x) { x.src = "import"; return x; })
        .concat(col.map(function (x) { x.src = "collected"; return x; }))
        .sort(function (a, b) { return a.t - b.t; });
    });
    return { series: series, unmatched: unmatched };
  }

  // Price at an instant: the hour itself, else the nearest reading within `tol`.
  function priceAt(series, ms, tol) {
    tol = tol === undefined ? H : tol;
    var target = Math.floor(ms / H) * H, best = null;
    for (var i = 0; i < series.length; i++) {
      var d = Math.abs(series[i].t - target);
      if (d <= tol && (!best || d < best.d)) best = { d: d, x: series[i] };
    }
    return best ? best.x : null;
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

  // --- Per card --------------------------------------------------------------

  function analyzeCard(card, series, now) {
    var release = Date.parse(card.release), out = Date.parse(card.aus_packs);
    var s = (series || []).filter(function (x) { return x.t >= Math.floor(release / H) * H && x.t <= now; });
    var r = { card: card, n: s.length, release: release, out: out };
    var expected = Math.max(1, Math.floor((now - release) / H) + 1);
    r.expected = expected;
    r.coverage = Math.min(1, s.length / expected);
    // Gaps of three hours or more, including before the first and after the last reading.
    var gaps = [], prev = Math.floor(release / H) * H - H;
    s.concat([{ t: Math.floor(now / H) * H + H }]).forEach(function (x) {
      var miss = Math.round((x.t - prev) / H) - 1;
      if (miss >= 3) gaps.push({ from: prev + H, hours: miss });
      prev = x.t;
    });
    r.gaps = gaps;
    r.longestGap = gaps.reduce(function (m, g) { return Math.max(m, g.hours); }, 0);
    if (!s.length) { r.status = "keine-daten"; return r; }
    r.status = gaps.length ? "luecken" : "ok";
    r.first = s[0].t; r.last = s[s.length - 1].t;
    r.median = median(s.map(function (x) { return x.p; }));
    r.current = s[s.length - 1].p;

    var lo = s[0], hi = s[0];
    s.forEach(function (x) { if (x.p < lo.p) lo = x; if (x.p > hi.p) hi = x; });
    var after = function (from, pick) {
      var res = null;
      s.forEach(function (x) { if (x.t > from.t && (!res || pick(x, res))) res = x; });
      return res;
    };
    var bestSell = after(lo, function (x, y) { return x.p > y.p; });
    var worstSell = after(hi, function (x, y) { return x.p < y.p; });
    r.bestBuy = point(lo, release);
    r.bestSell = point(bestSell, release);
    r.worstBuy = point(hi, release);
    r.worstSell = point(worstSell, release);
    r.bestTrade = bestSell ? profit(lo.p, bestSell.p) : null;
    r.worstTrade = worstSell ? profit(hi.p, worstSell.p) : null;

    var rel = priceAt(s, release, 2 * H);
    r.releasePrice = rel && rel.t >= Math.floor(release / H) * H ? rel.p : null;
    var o = priceAt(s, out);
    r.outPrice = o ? o.p : null;
    r.after = {};
    [1, 3, 7].forEach(function (d) {
      var x = priceAt(s, out + d * DAY);
      r.after[d] = x ? { p: x.p, chg: r.outPrice ? x.p / r.outPrice - 1 : null } : null;
    });
    r.series = s;
    return r;
  }

  // --- Patterns across cards --------------------------------------------------

  // Mean and median price relative to the release price, per hour since release.
  function curve(results, maxHours) {
    var by = [];
    results.forEach(function (r) {
      if (!r.releasePrice || !r.series) return;
      r.series.forEach(function (x) {
        var h = Math.round((x.t - r.release) / H);
        if (h < 0 || h > maxHours) return;
        (by[h] = by[h] || []).push(x.p / r.releasePrice);
      });
    });
    var pts = [];
    for (var h = 0; h <= maxHours; h++) {
      if (by[h] && by[h].length) pts.push({ h: h, mean: mean(by[h]), median: median(by[h]), n: by[h].length });
    }
    return pts;
  }

  // Each hourly price against the card's own median over the surrounding
  // 72 hours, so a card that slides all week does not make Sunday look cheap.
  // A card's readings are averaged per weekday x hour first, then the median
  // over cards is taken, so cards with long histories do not dominate.
  function heatmap(results) {
    var cells = [];
    for (var i = 0; i < 7 * 24; i++) cells.push([]);
    results.forEach(function (r) {
      if (!r.series || r.series.length < 24) return;
      var s = r.series, own = {};
      var start = 0;
      for (var i = 0; i < s.length; i++) {
        while (s[start].t < s[i].t - 36 * H) start++;
        var win = [];
        for (var j = start; j < s.length && s[j].t <= s[i].t + 36 * H; j++) win.push(s[j].p);
        if (win.length < 24) continue;
        var dev = s[i].p / median(win) - 1;
        var b = berlin(s[i].t), c = b.weekday * 24 + b.hour;
        (own[c] = own[c] || []).push(dev);
      }
      Object.keys(own).forEach(function (c) { cells[c].push(mean(own[c])); });
    });
    return cells.map(function (v, i) {
      return { weekday: Math.floor(i / 24), hour: i % 24, dev: v.length ? median(v) : null, n: v.length };
    });
  }

  function extremeCells(cells, minCards) {
    var ok = cells.filter(function (c) { return c.dev !== null && c.n >= minCards; });
    if (!ok.length) return null;
    var lo = ok[0], hi = ok[0];
    ok.forEach(function (c) { if (c.dev < lo.dev) lo = c; if (c.dev > hi.dev) hi = c; });
    return { cheapest: lo, dearest: hi };
  }

  // "Buy in the last hour in packs, sell X days later", net of tax.
  function ruleTest(results, maxDays) {
    var rows = [];
    for (var x = 1; x <= maxDays; x++) {
      var trades = [];
      results.forEach(function (r) {
        if (!r.series) return;
        var buy = priceAt(r.series, r.out - H);
        var sell = buy && priceAt(r.series, buy.t + x * DAY);
        if (buy && sell) trades.push(profit(buy.p, sell.p));
      });
      var wins = trades.filter(function (t) { return t.coins > 0; }).length;
      rows.push({
        days: x, n: trades.length, wins: wins,
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

  function groupStats(results, keyFn, ruleDays) {
    var g = {};
    results.forEach(function (r) {
      var k = keyFn(r.card);
      (g[k] = g[k] || []).push(r);
    });
    return Object.keys(g).sort().map(function (k) {
      var rs = g[k], withData = rs.filter(function (r) { return r.n > 0; });
      var rule = ruleTest(rs, ruleDays)[ruleDays - 1];
      return {
        key: k, cards: rs.length, withData: withData.length,
        bestPct: mean(withData.filter(function (r) { return r.bestTrade; }).map(function (r) { return r.bestTrade.pct; })),
        chg3: mean(withData.filter(function (r) { return r.after[3] && r.after[3].chg !== null; }).map(function (r) { return r.after[3].chg; })),
        chg7: mean(withData.filter(function (r) { return r.after[7] && r.after[7].chg !== null; }).map(function (r) { return r.after[7].chg; })),
        rule: rule
      };
    });
  }

  root.BT = {
    H: H, DAY: DAY, TAX: TAX, WD: WD,
    berlin: berlin, fromBerlin: fromBerlin,
    parseCsv: parseCsv, parseTime: parseTime, parsePrice: parsePrice, parsePlatform: parsePlatform,
    norm: norm, normPromo: normPromo, cardKey: cardKey, makeMatcher: makeMatcher,
    median: median, mean: mean, hourly: hourly, buildSeries: buildSeries, priceAt: priceAt, profit: profit,
    analyzeCard: analyzeCard, curve: curve, heatmap: heatmap, extremeCells: extremeCells, ruleTest: ruleTest,
    ratingBucket: ratingBucket, positionGroup: positionGroup, promoType: promoType, groupStats: groupStats
  };
  if (typeof module !== "undefined" && module.exports) module.exports = root.BT;
})(typeof window !== "undefined" ? window : globalThis);
