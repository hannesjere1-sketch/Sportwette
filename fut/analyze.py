#!/usr/bin/env python3
"""Find the hours of the day at which gold cards are cheapest and dearest,
and check with a walk-forward backtest whether trading that pattern pays
after EA's 5 % transfer tax.

Input is a CSV of price observations, as the collector extension exports it:

    timestamp,player_id,name,price
    2026-09-25T05:02:11Z,231747,Kylian Mbappé,412000

Timestamps are UTC (ISO 8601); hours are evaluated in Europe/Berlin.

The method, precisely:
  * observations are collapsed to one price per player and local hour (median)
  * every hour is divided by that player's median price of the same day, so a
    card that rises all week does not make the late hours look expensive —
    only the shape within the day is left
  * the hour profile for day D is learnt from the days before D only, never
    from D itself: the backtest trades exactly what it would have known then
  * a trade buys at the profile's cheapest hour and sells at its dearest hour
    (same day if that comes later, otherwise the next day), and only when the
    learnt spread still clears the tax plus a safety margin
  * selling costs 5 % tax plus the undercut needed to actually sell

Standard library only, like the scripts under .github/scripts.
"""

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
EA_TAX = 0.05


def load_observations(path):
    """Read the CSV into (utc datetime, player_id, name, price) tuples."""
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
            # A price of 0 means "no listing seen" on the price sites, not free.
            if price <= 0:
                continue
            rows.append((ts, str(row["player_id"]).strip(), (row.get("name") or "").strip(), price))
    return rows


def hourly_grid(rows):
    """player -> local date -> hour -> median price of that hour."""
    buckets = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    names = {}
    for ts, pid, name, price in rows:
        local = ts.astimezone(TZ)
        buckets[pid][local.date()][local.hour].append(price)
        if name:
            names[pid] = name
    grid = {
        pid: {day: {h: statistics.median(v) for h, v in hours.items()} for day, hours in days.items()}
        for pid, days in buckets.items()
    }
    return grid, names


def day_ratios(hours, min_hours):
    """Each hour's price relative to the day's median, or None if too sparse."""
    if len(hours) < min_hours:
        return None
    mid = statistics.median(hours.values())
    return {h: p / mid for h, p in hours.items()}


def profile(ratio_days):
    """Mean ratio per hour over several days; hours seen on under half the days are dropped."""
    per_hour = defaultdict(list)
    for ratios in ratio_days:
        for h, r in ratios.items():
            per_hour[h].append(r)
    need = max(1, len(ratio_days) // 2)
    return {h: statistics.fmean(v) for h, v in per_hour.items() if len(v) >= need}


def pick_hours(prof):
    """Cheapest and dearest hour of a profile."""
    buy = min(prof, key=prof.get)
    sell = max(prof, key=prof.get)
    return buy, sell


def forecasts(days, args):
    """Walk forward through one player's days: for every day with enough history,
    the hours learnt from the days before it and what trading them would have made."""
    ordered = sorted(days)
    ratios = {d: day_ratios(days[d], args.min_hours) for d in ordered}
    out = []
    for i, day in enumerate(ordered):
        history = [ratios[d] for d in ordered[max(0, i - args.window):i]
                   if ratios[d] is not None and (day - d).days <= args.window]
        if len(history) < args.min_days:
            continue
        prof = profile(history)
        if len(prof) < 2:
            continue
        buy_h, sell_h = pick_hours(prof)
        expected = prof[sell_h] / prof[buy_h] * (1 - EA_TAX) * (1 - args.slippage) - 1
        sell_day = day if sell_h > buy_h else day + timedelta(days=1)
        buy_price = days[day].get(buy_h)
        sell_price = days.get(sell_day, {}).get(sell_h)
        # No observation at either end means the day can't be scored — skip
        # rather than guess, so gaps in collection never flatter the result.
        if buy_price is None or sell_price is None:
            continue
        net = sell_price * (1 - EA_TAX) * (1 - args.slippage)
        out.append({
            "day": day.isoformat(), "buyHour": buy_h, "sellHour": sell_h,
            "buy": round(buy_price), "sellNet": round(net),
            "profit": round(net - buy_price), "ret": net / buy_price - 1,
            "gross": sell_price / buy_price - 1, "expected": expected,
        })
    return out


def backtest_player(days, args):
    """The forecasts the strategy actually trades: those clearing tax plus margin."""
    return [f for f in forecasts(days, args) if f["expected"] >= args.min_edge]


def wilson_low(hits, n, z=1.96):
    """Lower end of the 95 % Wilson interval for a hit rate."""
    if not n:
        return 0.0
    p = hits / n
    centre = p + z * z / (2 * n)
    margin = z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5
    return (centre - margin) / (1 + z * z / n)


def reliability(all_forecasts, min_player_days=30, min_days=3):
    """How far the learnt hours can be trusted yet, from every out-of-sample day.

    The hit rate asks whether the learnt dear hour really was dearer than the
    learnt cheap hour. The return interval is built from one average per
    calendar day rather than per player-day: all cards share the same market,
    so on a given day they move together and are not independent evidence.
    """
    n = len(all_forecasts)
    hits = sum(f["gross"] > 0 for f in all_forecasts)
    per_day = defaultdict(list)
    for f in all_forecasts:
        per_day[f["day"]].append(f["ret"])
    day_means = [statistics.fmean(v) for _, v in sorted(per_day.items())]
    res = {"playerDays": n, "days": len(day_means), "hits": hits,
           "hitRate": hits / n if n else None, "hitRateLow": wilson_low(hits, n) if n else None,
           "avgNet": statistics.fmean(day_means) if day_means else None, "avgNetLow": None}
    if len(day_means) >= 2:
        se = statistics.stdev(day_means) / len(day_means) ** 0.5
        res["avgNetLow"] = res["avgNet"] - 1.96 * se

    if n < min_player_days or len(day_means) < min_days:
        res["verdict"], res["text"] = "sammeln", "Noch zu wenige Tage für eine Aussage."
    elif res["avgNetLow"] is not None and res["avgNetLow"] > 0:
        res["verdict"], res["text"] = "profitabel", "Das Muster ist stabil und bringt nach Steuer sicher Gewinn."
    elif res["hitRateLow"] > 0.5:
        res["verdict"], res["text"] = "muster", ("Das Muster ist echt, schlägt die 5 % Steuer aber "
                                                 "noch nicht sicher.")
    elif len(day_means) >= 7:
        res["verdict"], res["text"] = "kein-muster", "Nach einer Woche kein verlässliches Tagesmuster."
    else:
        res["verdict"], res["text"] = "sammeln", "Noch nicht eindeutig, weiter sammeln."
    return res


def full_profile(days, min_hours):
    ratios = [r for r in (day_ratios(h, min_hours) for h in days.values()) if r is not None]
    return profile(ratios), len(ratios)


def summarise(trades):
    if not trades:
        return {"trades": 0}
    rets = [t["ret"] for t in trades]
    return {
        "trades": len(trades),
        "winRate": sum(r > 0 for r in rets) / len(rets),
        "avgReturn": statistics.fmean(rets),
        "medianReturn": statistics.median(rets),
        "profitCoins": sum(t["profit"] for t in trades),
        "investedCoins": sum(t["buy"] for t in trades),
    }


def run(rows, args):
    grid, names = hourly_grid(rows)
    latest = {}
    for ts, pid, _name, price in rows:
        if pid not in latest or ts > latest[pid][0]:
            latest[pid] = (ts, price)
    players, all_trades, all_forecasts, market = [], [], [], []
    for pid, days in sorted(grid.items()):
        prof, n_days = full_profile(days, args.min_hours)
        fc = forecasts(days, args)
        all_forecasts.extend(fc)
        trades = [f for f in fc if f["expected"] >= args.min_edge]
        all_trades.extend(trades)
        entry = {"id": pid, "name": names.get(pid, pid), "days": n_days,
                 "lastPrice": round(latest[pid][1]),
                 "lastSeen": latest[pid][0].isoformat(timespec="seconds"),
                 "backtest": summarise(trades), "trades": trades}
        if len(prof) >= 2:
            buy_h, sell_h = pick_hours(prof)
            entry.update({"cheapestHour": buy_h, "dearestHour": sell_h,
                          "spread": prof[sell_h] / prof[buy_h] - 1,
                          "profile": {h: round(v, 4) for h, v in sorted(prof.items())}})
            market.append(prof)
        players.append(entry)
    overall = profile(market) if market else {}
    by_week = defaultdict(list)
    for t in all_trades:
        by_week[datetime.fromisoformat(t["day"]).strftime("%G-W%V")].append(t)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "observations": len(rows),
        "firstSeen": min(r[0] for r in rows).isoformat(timespec="seconds"),
        "settings": {"window": args.window, "minDays": args.min_days, "minHours": args.min_hours,
                     "minEdge": args.min_edge, "slippage": args.slippage, "tax": EA_TAX},
        "marketProfile": {h: round(v, 4) for h, v in sorted(overall.items())},
        "overall": summarise(all_trades),
        "reliability": reliability(all_forecasts),
        "byWeek": {w: summarise(ts) for w, ts in sorted(by_week.items())},
        "players": players,
    }


def pct(x):
    return f"{x * 100:+.2f} %"


def print_report(res):
    print("Tagesprofil über alle Spieler (Preis relativ zum Tagesmedian, Europe/Berlin):")
    prof = res["marketProfile"]
    if not prof:
        print("  zu wenig Daten — mindestens ein paar volle Tage pro Spieler sammeln.")
    else:
        lo, hi = min(prof.values()), max(prof.values())
        for h, v in prof.items():
            bar = "#" * int(round((v - lo) / (hi - lo) * 30)) if hi > lo else ""
            print(f"  {h:02d}:00  {pct(v - 1):>9}  {bar}")
    print()
    print(f"{'Spieler':<24}{'Tage':>5}{'billig':>8}{'teuer':>7}{'Spanne':>10}"
          f"{'Trades':>8}{'Treffer':>9}{'Ø Rendite':>11}{'Gewinn':>12}")
    for p in res["players"]:
        b = p["backtest"]
        cheap = f"{p['cheapestHour']:02d}h" if "cheapestHour" in p else "-"
        dear = f"{p['dearestHour']:02d}h" if "dearestHour" in p else "-"
        spread = pct(p["spread"]) if "spread" in p else "-"
        if b["trades"]:
            tail = f"{b['trades']:>8}{b['winRate'] * 100:>8.0f}%{pct(b['avgReturn']):>11}{b['profitCoins']:>12,}"
        else:
            tail = f"{0:>8}{'-':>9}{'-':>11}{'-':>12}"
        print(f"{p['name'][:23]:<24}{p['days']:>5}{cheap:>8}{dear:>7}{spread:>10}{tail}")
    print()
    r = res["reliability"]
    print(f"Zuverlässigkeit: {r['text']}")
    if r["playerDays"]:
        low = f", sicher mindestens {pct(r['avgNetLow'])}" if r["avgNetLow"] is not None else ""
        print(f"  teure Stunde lag an {r['hits']} von {r['playerDays']} Spieler-Tagen über der billigen "
              f"({r['hitRate'] * 100:.0f} %, sicher mindestens {r['hitRateLow'] * 100:.0f} %); "
              f"Ø nach Steuer {pct(r['avgNet'])}{low} über {r['days']} Tage")
    print()
    o = res["overall"]
    s = res["settings"]
    print(f"Backtest gesamt (walk-forward, {s['window']} Tage Lernfenster, 5 % EA-Steuer, "
          f"{s['slippage'] * 100:.1f} % Unterbieten, Mindestvorteil {s['minEdge'] * 100:.1f} %):")
    if not o["trades"]:
        print("  keine Trades — entweder zu wenig Daten oder das Muster schlägt die Steuer nicht.")
        return
    print(f"  {o['trades']} Trades, Trefferquote {o['winRate'] * 100:.0f} %, "
          f"Ø Rendite {pct(o['avgReturn'])} (Median {pct(o['medianReturn'])}), "
          f"Gewinn {o['profitCoins']:,} bei {o['investedCoins']:,} eingesetzten Coins")
    print("  pro Woche:")
    for w, b in res["byWeek"].items():
        print(f"    {w}: {b['trades']:>3} Trades, Ø {pct(b['avgReturn'])}, Gewinn {b['profitCoins']:,}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("csv", help="Preis-CSV aus der Sammler-Erweiterung")
    ap.add_argument("--window", type=int, default=14, help="Lernfenster in Tagen (Standard 14)")
    ap.add_argument("--min-days", type=int, default=3, help="Mindestzahl Lerntage vor dem ersten Trade")
    ap.add_argument("--min-hours", type=int, default=12, help="Stunden mit Preis, damit ein Tag zählt")
    ap.add_argument("--min-edge", type=float, default=0.01,
                    help="erwarteter Nettovorteil nach Steuer, ab dem gehandelt wird (0.01 = 1 %%)")
    ap.add_argument("--slippage", type=float, default=0.01,
                    help="Abschlag beim Verkauf fürs Unterbieten (0.01 = 1 %%)")
    ap.add_argument("--json", help="Ergebnis zusätzlich als JSON hierhin schreiben")
    args = ap.parse_args(argv)

    rows = load_observations(args.csv)
    if not rows:
        sys.exit(f"Keine gültigen Zeilen in {args.csv}.")
    res = run(rows, args)
    print_report(res)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
