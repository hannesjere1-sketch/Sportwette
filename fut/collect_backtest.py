#!/usr/bin/env python3
"""Append the current price of every gold card in backtest-cards.json to a CSV.

The backtest (static-app/backtest.html) looks at the gold base cards of the
players who got a TOTW or Destined for Glory card. No site that keeps a price
history lets us read it (FUT.GG's /api/ is disallowed in its robots.txt and
sits behind Cloudflare, FUTBIN answers 403), so — like collect.py — this builds
the history itself, one EasySBC reading per card and hour, from now on.

    python3 fut/collect_backtest.py backtest-prices.csv

Rows use the backtest's import format: karte,promo,timestamp,preis,plattform,quelle.
EasySBC shows one market price without naming the platform; it is filed as
"konsole" and marked with quelle=easysbc, so a PC history can be added by CSV.
"""

import csv
import json
import os
import sys
import time
import urllib.error
from datetime import datetime, timezone

from collect import PAUSE, fetch, market_price

CARDS = os.path.join(os.path.dirname(__file__), "backtest-cards.json")
HEADER = ["karte", "promo", "timestamp", "preis", "plattform", "quelle"]


def main():
    if len(sys.argv) != 2:
        sys.exit("Aufruf: collect_backtest.py <csv>")
    out = sys.argv[1]
    with open(CARDS, encoding="utf-8") as fh:
        cards = [c for c in json.load(fh)["karten"] if c.get("gold_id")]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows, failed = [], []
    for c in cards:
        price = None
        for attempt in range(2):
            try:
                price = market_price(fetch(c["gold_id"]))
                break
            except (urllib.error.URLError, TimeoutError, ValueError) as e:
                if attempt:
                    failed.append(f"{c['karte']}: {e}")
                time.sleep(2)
        if price:
            rows.append([c["karte"], c["promo"], now, int(price), "konsole", "easysbc"])
        time.sleep(PAUSE)

    new_file = not os.path.exists(out) or os.path.getsize(out) == 0
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(HEADER)
        w.writerows(rows)

    print(f"Backtest: {len(rows)}/{len(cards)} Gold-Preise gespeichert ({now}).")
    for f in failed[:10]:
        print("  Fehler:", f)
    if cards and not rows:
        sys.exit(1)


if __name__ == "__main__":
    main()
