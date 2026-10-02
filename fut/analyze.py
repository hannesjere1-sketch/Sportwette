#!/usr/bin/env python3
"""When are Icons and Heroes cheapest and dearest — by weekday and by hour?

Input is the hourly price CSV written by fut/collect.py:

    timestamp,player_id,name,kind,price
    2026-10-01T16:05:11Z,190042,Diego Armando Maradona,Icon,412000

Everything is gross: no transfer tax, no undercut. Hours are German time.

The method, precisely:
  * readings are collapsed to one price per card and local hour (median)
  * every hourly price is divided by the same card's median over the
    surrounding 72 hours. That removes the card's own trend — a card rising
    all week does not make Sunday look dear — and leaves only how far this
    hour sits above or below the card's going rate. 1.00 = normal, 0.97 = 3 %
    cheaper than usual
  * those ratios are combined per weekday × hour across cards (the median, so
    one card's spike cannot bend it) — that is the weekly heat map
  * the best flips are read off the heat map: buy in one slot, sell in a later
    one within three days, ranked by the difference between them
  * an honest check walks forward through the days: for each day, the cheap
    and dear hours are learnt from earlier days only and then tested on that
    day. A pattern that only shows up in hindsight fails here

Standard library only.
"""

import argparse
import csv
import json
import statistics
import sys
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
HALF_WINDOW = timedelta(hours=36)  # the 72 hours a price is compared against
MIN_WINDOW_HOURS = 24              # fewer readings than this around an hour: no ratio
MAX_HOLD = 72                      # longest flip considered, in hours
MAX_PRICE = 500_000                # the cap for both Icons and Heroes
# A reading this far off the card's 72-hour median is a thin-market artefact
# (at night one overpriced listing can be the cheapest left), not a price
# anyone trades at — it is left out rather than allowed to fake a pattern.
OUTLIER = 1.5
CARD_MIN_HOURS = 48                # per-card hours only after two days of data


def load_observations(path):
    """Read the CSV into (utc datetime, card id, name, kind, price) tuples."""
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
                price = float(row["price"])
            except (KeyError, ValueError):
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if price <= 0:
                continue
            rows.append((ts, str(row["player_id"]).strip(), (row.get("name") or "").strip(),
                         (row.get("kind") or "").strip(), price))
    return rows


def hourly_series(rows):
    """card -> sorted list of (local hour start, median price in that hour)."""
    buckets = defaultdict(lambda: defaultdict(list))
    meta = {}
    for ts, pid, name, kind, price in rows:
        local = ts.astimezone(TZ).replace(minute=0, second=0, microsecond=0)
        buckets[pid][local].append(price)
        meta[pid] = {"name": name or pid, "kind": kind}
    series = {pid: sorted((t, statistics.median(v)) for t, v in hours.items())
              for pid, hours in buckets.items()}
    return series, meta


def relative(series):
    """Each hourly price divided by the card's median over the surrounding 72 h.

    Returns card -> {local hour: ratio}. Hours with too little data around
    them get no ratio rather than a noisy one, and outliers (see OUTLIER) none
    at all."""
    out = {}
    for pid, points in series.items():
        times = [t for t, _ in points]
        prices = [p for _, p in points]
        ratios = {}
        for t, p in points:
            lo = bisect_left(times, t - HALF_WINDOW)
            hi = bisect_right(times, t + HALF_WINDOW)
            if hi - lo < MIN_WINDOW_HOURS:
                continue
            r = p / statistics.median(prices[lo:hi])
            if 1 / OUTLIER < r < OUTLIER:
                ratios[t] = r
        out[pid] = ratios
    return out


def heat_map(ratios, cards):
    """(weekday, hour) -> (median ratio across cards and weeks, number of readings)."""
    cells = defaultdict(list)
    for pid in cards:
        for t, r in ratios.get(pid, {}).items():
            cells[(t.weekday(), t.hour)].append(r)
    return {k: (statistics.median(v), len(v)) for k, v in cells.items()}


def hour_profile(ratios, cards):
    """hour -> median ratio, all weekdays together."""
    cells = defaultdict(list)
    for pid in cards:
        for t, r in ratios.get(pid, {}).items():
            cells[t.hour].append(r)
    return {h: statistics.median(v) for h, v in sorted(cells.items())}


def weekday_profile(ratios, cards):
    cells = defaultdict(list)
    for pid in cards:
        for t, r in ratios.get(pid, {}).items():
            cells[t.weekday()].append(r)
    return {wd: statistics.median(v) for wd, v in sorted(cells.items())}


def best_flips(heat, top=8, min_n=10):
    """Buy slot → sell slot up to MAX_HOLD hours later, ranked by the gap."""
    slots = {k: v for k, v in heat.items() if v[1] >= min_n}
    flips = []
    for (wd, h), (buy, _n) in slots.items():
        for hold in range(1, MAX_HOLD + 1):
            total = h + hold
            key = ((wd + total // 24) % 7, total % 24)
            if key not in slots:
                continue
            sell = slots[key][0]
            flips.append({"buyDay": wd, "buyHour": h, "sellDay": key[0], "sellHour": key[1],
                          "hold": hold, "buy": buy, "sell": sell, "gain": sell / buy - 1})
    flips.sort(key=lambda f: -f["gain"])

    def week_hour(day, hour):
        return day * 24 + hour

    def near(a, b):
        return min(abs(a - b), 168 - abs(a - b)) <= 2

    # Neighbouring slots make near-copies of the same flip; keep the best of each.
    picked = []
    for f in flips:
        if any(near(week_hour(f["buyDay"], f["buyHour"]), week_hour(p["buyDay"], p["buyHour"]))
               and near(week_hour(f["sellDay"], f["sellHour"]), week_hour(p["sellDay"], p["sellHour"]))
               for p in picked):
            continue
        picked.append(f)
        if len(picked) == top:
            break
    return picked


def walk_forward(series, cards, min_days=3, window=14):
    """For each card and day: learn the cheapest and dearest hour from the days
    before only (median of each hour's ratio to its day's median), then buy and
    sell at those hours on this day. Gross, no tax."""
    trades = []
    for pid in cards:
        days = defaultdict(dict)
        for t, p in series[pid]:
            days[t.date()][t.hour] = p
        ordered = sorted(days)
        for i, day in enumerate(ordered):
            history = []
            for d in ordered[max(0, i - window):i]:
                hours = days[d]
                if len(hours) >= 18:
                    mid = statistics.median(hours.values())
                    history.append({h: p / mid for h, p in hours.items()
                                    if 1 / OUTLIER < p / mid < OUTLIER})
            if len(history) < min_days:
                continue
            per_hour = defaultdict(list)
            for hist in history:
                for h, r in hist.items():
                    per_hour[h].append(r)
            need = len(history) // 2 + 1
            prof = {h: statistics.median(v) for h, v in per_hour.items() if len(v) >= need}
            if len(prof) < 2:
                continue
            buy_h = min(prof, key=prof.get)
            sell_h = max((h for h in prof if h != buy_h), key=prof.get)
            sell_day = day if sell_h > buy_h else day + timedelta(days=1)
            buy = days[day].get(buy_h)
            sell = days.get(sell_day, {}).get(sell_h)
            if buy and sell and not 1 / OUTLIER < sell / buy < OUTLIER:
                continue  # an outlier at either end is no tradeable price
            # A missing reading at either end means the flip can't be scored:
            # skip it rather than guess, so gaps never flatter the result.
            if buy is None or sell is None:
                continue
            trades.append({"card": pid, "day": day.isoformat(), "buyHour": buy_h, "sellHour": sell_h,
                           "buy": round(buy), "sell": round(sell), "gain": sell / buy - 1})
    return trades


def summarise(trades):
    if not trades:
        return {"trades": 0}
    gains = [t["gain"] for t in trades]
    per_day = defaultdict(list)
    for t in trades:
        per_day[t["day"]].append(t["gain"])
    day_means = [statistics.fmean(v) for _, v in sorted(per_day.items())]
    out = {"trades": len(gains), "days": len(day_means),
           "winRate": sum(g > 0 for g in gains) / len(gains),
           "avgGain": statistics.fmean(gains), "medianGain": statistics.median(gains),
           "coins": round(sum(t["sell"] - t["buy"] for t in trades)),
           "byDay": {d: round(statistics.fmean(v), 4) for d, v in sorted(per_day.items())}}
    # Cards share one market and move together on a given day, so the
    # uncertainty comes from the spread between days, not between trades.
    if len(day_means) >= 2:
        se = statistics.stdev(day_means) / len(day_means) ** 0.5
        out["avgGainLow"] = out["avgGain"] - 1.96 * se
    return out


def card_entry(pid, meta, series, ratios):
    points = series[pid]
    last_t, last_p = points[-1]
    # Lows and highs from readings that passed the outlier check, where known.
    kept = ratios.get(pid) or {}
    clean = [(t, p) for t, p in points if t in kept] or points
    week = [p for t, p in clean if t >= last_t - timedelta(days=7)] or [last_p]
    prof = hour_profile(ratios, [pid])
    entry = {"id": pid, "name": meta[pid]["name"], "kind": meta[pid]["kind"],
             "price": round(last_p), "seen": last_t.isoformat(timespec="minutes"),
             "low7": round(min(week)), "high7": round(max(week)),
             "median": round(statistics.median(p for _, p in points)),
             "hours": len(points)}
    if len(prof) >= 12 and len(points) >= CARD_MIN_HOURS:
        cheap = min(prof, key=prof.get)
        dear = max(prof, key=prof.get)
        entry.update({"cheapHour": cheap, "dearHour": dear,
                      "spread": prof[dear] / prof[cheap] - 1,
                      "profile": {h: round(v, 4) for h, v in prof.items()}})
    return entry


def section(ratios, series, cards):
    heat = heat_map(ratios, cards)
    return {
        "cards": len(cards),
        "hourProfile": {h: round(v, 4) for h, v in hour_profile(ratios, cards).items()},
        "weekdayProfile": {wd: round(v, 4) for wd, v in weekday_profile(ratios, cards).items()},
        "heat": [{"day": wd, "hour": h, "ratio": round(r, 4), "n": n}
                 for (wd, h), (r, n) in sorted(heat.items())],
        "flips": best_flips(heat),
        "walkForward": summarise(walk_forward(series, cards)),
    }


def run(rows, max_price=MAX_PRICE):
    series, meta = hourly_series(rows)
    # The cap applies to what a card usually costs, so a brief spike over the
    # cap does not throw it out, nor a brief dip let it in.
    cards = sorted(pid for pid, pts in series.items()
                   if statistics.median(p for _, p in pts) <= max_price)
    ratios = relative({pid: series[pid] for pid in cards})
    kinds = defaultdict(list)
    for pid in cards:
        kinds[meta[pid]["kind"] or "?"].append(pid)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "firstSeen": min(r[0] for r in rows).isoformat(timespec="seconds"),
        "lastSeen": max(r[0] for r in rows).isoformat(timespec="seconds"),
        "hoursCovered": len({t for pid in cards for t, _ in series[pid]}),
        "maxPrice": max_price,
        "all": section(ratios, series, cards),
        "byKind": {k: section(ratios, series, v) for k, v in sorted(kinds.items())},
        "cards": sorted((card_entry(pid, meta, series, ratios) for pid in cards),
                        key=lambda c: -c["price"]),
    }


def pct(x):
    return f"{x * 100:+.1f} %"


def slot(day, hour):
    return f"{WEEKDAYS[day]} {hour:02d} Uhr"


def print_report(res):
    a = res["all"]
    print(f"{a['cards']} Karten (Icons und Heroes bis {res['maxPrice']:,} Coins), "
          f"{res['hoursCovered']} Stunden mit Preisen. Alles ohne Steuer.")
    print()
    print("Stundenprofil (Preis gegenüber dem Niveau der umliegenden 3 Tage):")
    prof = a["hourProfile"]
    if prof:
        lo, hi = min(prof.values()), max(prof.values())
        for h, v in prof.items():
            bar = "#" * int(round((v - lo) / (hi - lo) * 30)) if hi > lo else ""
            print(f"  {h:02d} Uhr  {pct(v - 1):>8}  {bar}")
    else:
        print("  noch zu wenig Daten (mindestens 24 Stunden je Karte)")
    print()
    if a["weekdayProfile"]:
        print("Wochentage:", "  ".join(f"{WEEKDAYS[wd]} {pct(v - 1)}"
                                       for wd, v in a["weekdayProfile"].items()))
        print()
    print("Beste Flips (kaufen → verkaufen, Unterschied ohne Steuer):")
    for f in a["flips"]:
        print(f"  {slot(f['buyDay'], f['buyHour'])} → {slot(f['sellDay'], f['sellHour'])}"
              f"  ({f['hold']} h halten): {pct(f['gain'])}")
    if not a["flips"]:
        print("  noch zu wenig Daten")
    print()
    w = a["walkForward"]
    print("Ehrlicher Test (Stunden nur aus Vortagen gelernt, dann an neuen Tagen geflippt):")
    if w["trades"]:
        low = f", sicher mindestens {pct(w['avgGainLow'])}" if "avgGainLow" in w else ""
        print(f"  {w['trades']} Flips an {w['days']} Tagen: Ø {pct(w['avgGain'])}{low}, "
              f"Median {pct(w['medianGain'])}, im Plus {w['winRate'] * 100:.0f} %, "
              f"zusammen {w['coins']:+,} Coins")
    else:
        print("  noch keine — braucht 3 volle Tage zum Lernen")
    print()
    for kind, s in res["byKind"].items():
        p = s["hourProfile"]
        if len(p) >= 2:
            cheap, dear = min(p, key=p.get), max(p, key=p.get)
            print(f"{kind}s ({s['cards']}): billigste Stunde {cheap:02d} Uhr {pct(p[cheap] - 1)}, "
                  f"teuerste {dear:02d} Uhr {pct(p[dear] - 1)}")
    print()
    print(f"{'Karte':<28}{'Typ':<6}{'Preis':>10}{'7T-Tief':>10}{'7T-Hoch':>10}"
          f"{'billig':>8}{'teuer':>7}{'Spanne':>9}")
    for c in res["cards"]:
        cheap = f"{c['cheapHour']:02d}h" if "cheapHour" in c else "-"
        dear = f"{c['dearHour']:02d}h" if "dearHour" in c else "-"
        spread = pct(c["spread"]) if "spread" in c else "-"
        print(f"{c['name'][:27]:<28}{c['kind'][:5]:<6}{c['price']:>10,}{c['low7']:>10,}"
              f"{c['high7']:>10,}{cheap:>8}{dear:>7}{spread:>9}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("csv", help="Preis-CSV aus fut/collect.py")
    ap.add_argument("--max-price", type=int, default=MAX_PRICE)
    ap.add_argument("--json", help="Ergebnis zusätzlich als JSON hierhin schreiben")
    args = ap.parse_args(argv)
    rows = load_observations(args.csv)
    if not rows:
        sys.exit(f"Keine gültigen Zeilen in {args.csv}.")
    res = run(rows, args.max_price)
    print_report(res)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
