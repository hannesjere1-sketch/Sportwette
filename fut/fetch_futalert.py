#!/usr/bin/env python3
"""Fetch the price history of the backtest's gold cards from futalert, locally.

Run it yourself, on your own computer, for your own analysis. futalert's terms
allow personal, non-commercial use only and forbid republishing, so nothing it
writes may go into the repository: cache and CSV live outside it (default
~/fut-daten/), and the CSV is only loaded into backtest.html through the
import box in your own browser.

    python3 fut/fetch_futalert.py            # fetch what is missing, write the CSV
    python3 fut/fetch_futalert.py --plan     # only show what it would fetch

What it does, and nothing more:
  * cards: gold cards of the players in TOTW 2, TOTW 3, DFG Team 1 and Team 2
    (fut/backtest-cards.json, field futalert_id);
  * window per card: 5 days before to 7 days after the special card's release;
    a window that has not ended yet is skipped until it has;
  * one request per card for the whole window, PlayStation prices only, kept
    as 4-hour blocks (median of the readings in the block);
  * 8-15 seconds of random pause between requests;
  * every answer is cached, a cached card is never asked for again, so a
    stopped run simply continues where it left off;
  * HTTP 403/429, any other HTTP error, a network error or a Cloudflare page
    stops the whole run at once, with no retry.

Timestamps from futalert are UTC.
"""

import argparse
import csv
import json
import os
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api20.futalert.co.uk/api/Player/GetCardMovements"
CARDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest-cards.json")
PROMOS = ("TOTW 2", "TOTW 3", "DFG Team 1", "DFG Team 2")
BEFORE = timedelta(days=5)
AFTER = timedelta(days=7)
BLOCK = timedelta(hours=4)
PAUSE = (8.0, 15.0)
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
              "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
CSV_NAME = "backtest-futalert.csv"
HEADER = ["karte", "promo", "timestamp", "preis", "plattform", "quelle"]


class Stop(Exception):
    """The source refused or failed: end the run, retry nothing."""


def utc(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def window(card):
    rel = utc(card["release"])
    return rel - BEFORE, rel + AFTER


def selected(cards):
    return [c for c in cards if c.get("promo") in PROMOS and c.get("gold_id") and c.get("futalert_id")]


def cache_path(folder, card):
    start, end = window(card)
    return os.path.join(folder, "cache", "%s_%s_%s.json" % (
        card["futalert_id"], start.strftime("%Y%m%dT%H%M"), end.strftime("%Y%m%dT%H%M")))


def fetch(card, opener=urllib.request.urlopen):
    """One request for the card's whole window. Returns [(datetime, ps_price)] inside it."""
    start, end = window(card)
    body = json.dumps({
        "PlayerId": card["futalert_id"], "IsHourly": True, "PeriodType": 1,
        "StartDate": start.strftime("%Y-%m-%dT%H:%M:%S"), "EndDate": end.strftime("%Y-%m-%dT%H:%M:%S"),
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Content-Type": "application/json", "Accept": "application/json",
        "Origin": "https://www.futalert.co.uk", "User-Agent": USER_AGENT,
    })
    try:
        with opener(req, timeout=30) as res:
            text = res.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            raise Stop("futalert antwortet mit HTTP %d (gesperrt bzw. zu viele Anfragen)." % e.code)
        raise Stop("futalert antwortet mit HTTP %d." % e.code)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Stop("Netzwerkfehler: %s" % e)
    if "Just a moment" in text or "challenge-platform" in text or "cf-chl" in text:
        raise Stop("futalert zeigt eine Cloudflare-Prüfseite.")
    try:
        data = json.loads(text)
    except ValueError:
        raise Stop("Antwort ist kein JSON (Schnittstelle geändert?).")
    if (data.get("Status") or {}).get("StatusType") not in (None, "Ok"):
        raise Stop("futalert meldet einen Fehler: %s" % data.get("Status"))
    points = []
    for m in data.get("CardMovements") or []:
        price = m.get("CurrentPricePS4")
        stamp = m.get("LastUpdatedDate")
        if not stamp or not isinstance(price, (int, float)) or price <= 0:
            continue
        t = datetime.fromisoformat(stamp[:19]).replace(tzinfo=timezone.utc)
        if start <= t < end:
            points.append((t, int(price)))
    return points


def blocks(points, start, end):
    """4-hour blocks from the window start: [(block start, median price)], empty blocks left out."""
    by = {}
    for t, p in points:
        if start <= t < end:
            by.setdefault(int((t - start) / BLOCK), []).append(p)
    return [(start + i * BLOCK, int(round(statistics.median(by[i])))) for i in sorted(by)]


def save_cache(path, points):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump([[iso(t), p] for t, p in points], fh)
    os.replace(tmp, path)  # never leaves a half-written cache file behind


def load_cache(path):
    with open(path, encoding="utf-8") as fh:
        return [(utc(t), p) for t, p in json.load(fh)]


def write_csv(folder, cards):
    """Rebuild the import CSV from every cached card. Returns (rows, cards with data)."""
    rows, with_data = [], 0
    for c in cards:
        path = cache_path(folder, c)
        if not os.path.exists(path):
            continue
        start, end = window(c)
        bl = blocks(load_cache(path), start, end)
        with_data += bool(bl)
        rows += [[c["karte"], c["promo"], iso(t), p, "ps", "futalert-4h"] for t, p in bl]
    path = os.path.join(folder, CSV_NAME)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        w.writerows(rows)
    return path, len(rows), with_data


def run(folder, cards, now, plan_only=False, opener=urllib.request.urlopen, sleep=time.sleep, out=print):
    todo, waiting, cached = [], [], 0
    for c in cards:
        start, end = window(c)
        if os.path.exists(cache_path(folder, c)):
            cached += 1
        elif end > now:
            waiting.append(c)
        else:
            todo.append(c)
    out("%d Karten: %d schon geladen, %d zu laden, %d warten noch auf das Ende ihres Zeitfensters."
        % (len(cards), cached, len(todo), len(waiting)))
    for c in waiting:
        out("  wartet: %s (%s) bis %s" % (c["karte"], c["promo"], iso(window(c)[1])))
    if todo:
        lo, hi = PAUSE
        out("Geschätzte Dauer: %d Abfragen, etwa %d–%d Minuten."
            % (len(todo), (len(todo) - 1) * lo // 60 + 1, (len(todo) - 1) * hi // 60 + 1))
    if plan_only:
        return 0
    done, stopped = 0, None
    for i, c in enumerate(todo):
        if i:
            sleep(random.uniform(*PAUSE))
        try:
            points = fetch(c, opener)
        except Stop as e:
            stopped = str(e)
            break
        save_cache(cache_path(folder, c), points)
        done += 1
        out("  %d/%d %s (%s): %d Messwerte" % (i + 1, len(todo), c["karte"], c["promo"], len(points)))
    path, nrows, with_data = write_csv(folder, cards)
    out("CSV: %s (%d Zeilen, %d Karten mit Preisen)." % (path, nrows, with_data))
    if stopped:
        out("ABBRUCH: %s Nichts wird wiederholt. %d Karten in diesem Lauf geladen. "
            "Später einfach erneut starten, es geht beim nächsten offenen Eintrag weiter." % (stopped, done))
        return 2
    if waiting:
        out("Nach dem Ende der offenen Zeitfenster noch einmal starten.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=os.path.expanduser("~/fut-daten"),
                    help="Ordner für Cache und CSV, außerhalb des Repositorys (Standard: ~/fut-daten)")
    ap.add_argument("--plan", action="store_true", help="nur anzeigen, was geladen würde")
    args = ap.parse_args()
    folder = os.path.abspath(os.path.expanduser(args.dir))
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if folder == repo or folder.startswith(repo + os.sep):
        sys.exit("Der Datenordner darf nicht im Repository liegen: " + folder)
    with open(CARDS, encoding="utf-8") as fh:
        cards = selected(json.load(fh)["karten"])
    os.makedirs(folder, exist_ok=True)
    sys.exit(run(folder, cards, datetime.now(timezone.utc), plan_only=args.plan))


if __name__ == "__main__":
    main()
