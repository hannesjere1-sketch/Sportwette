#!/usr/bin/env python3
"""Append the current market price of every card on the watch list to a CSV.

Source is EasySBC's public API (api-fc27.easysbc.io), which — unlike FUT.GG,
FUTBIN and FUTWIZ — does not sit behind a Cloudflare challenge, so it answers
GitHub Actions runners too. It only knows the current price, never a history,
which is why this runs on a schedule and the history is built up here.

    python3 fut/collect.py data/fut-prices.csv

Rows follow the format analyze.py reads: timestamp,player_id,name,price.
Only prices EasySBC marks as "market" are kept; SBC, objective and token
cards have no transfer-market price to trade on.
"""

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

API = "https://api-fc27.easysbc.io/players/{}"
WATCHLIST = os.path.join(os.path.dirname(__file__), "players.json")
PAUSE = 0.5  # between requests — about 80 per run, never a burst


def fetch(pid):
    req = urllib.request.Request(API.format(pid), headers={
        "User-Agent": "Mozilla/5.0 (fut-price-collector)",
        "Accept": "application/json",
        "Origin": "https://www.easysbc.io",
    })
    with urllib.request.urlopen(req, timeout=20) as res:
        return json.load(res)


def market_price(body):
    info = body.get("priceInfo") or {}
    if info.get("source") != "market":
        return None
    price = info.get("displayPrice") or body.get("price")
    return price if isinstance(price, (int, float)) and price > 0 else None


def main():
    if len(sys.argv) != 2:
        sys.exit("Aufruf: collect.py <csv>")
    out = sys.argv[1]
    with open(WATCHLIST, encoding="utf-8") as fh:
        players = json.load(fh)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows, failed = [], []
    for p in players:
        try:
            price = market_price(fetch(p["id"]))
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            failed.append(f"{p['name']}: {e}")
            price = None
        if price:
            rows.append([now, p["id"], p["name"], int(price)])
        time.sleep(PAUSE)

    new_file = not os.path.exists(out) or os.path.getsize(out) == 0
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(["timestamp", "player_id", "name", "price"])
        w.writerows(rows)

    print(f"{len(rows)}/{len(players)} Preise gespeichert ({now}).")
    for f in failed:
        print("  Fehler:", f)
    # Every request failing means the source is down or has changed — make the
    # run go red so it gets noticed instead of silently collecting nothing.
    if not rows:
        sys.exit(1)


if __name__ == "__main__":
    main()
