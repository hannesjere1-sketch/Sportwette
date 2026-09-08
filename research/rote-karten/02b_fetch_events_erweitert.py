#!/usr/bin/env python3
"""Phase 2b — ESPN-Spielverlaeufe fuer die erweiterte Datenbasis.

Holt ausschliesslich die Kandidaten aus Phase 1b: Spiele mit einer
fairen Heimquote unter 1,80. Alles darueber kann in keiner der drei
Staerkevarianten je ein Fall werden und braucht deshalb keinen Abruf —
das spart rund 80 Prozent der Anfragen.

Fortschritt in data/erw_events_progress.json, Neustart macht dort
weiter. Der Rohcache liegt wie gehabt in data/cache/ und wird mit dem
bestehenden Bestand geteilt.
"""

import argparse
import importlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import log, warn

fe = importlib.import_module("02_fetch_events")

FORTSCHRITT = os.path.join(common.DATA_DIR, "erw_events_progress.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pause", type=float, default=2.0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--retry-errors", action="store_true")
    args = ap.parse_args()

    kand = common.read_csv(os.path.join(common.DATA_DIR,
                                        "erw_matches_kandidaten.csv"))
    if not kand:
        warn("erw_matches_kandidaten.csv fehlt — bitte 01b laufen lassen.")
        return 1

    try:
        with open(FORTSCHRITT, "r", encoding="utf-8") as fh:
            fortschritt = json.load(fh)
    except Exception:
        fortschritt = {}

    offen = []
    for m in kand:
        e = fortschritt.get(m["match_id"])
        if e and e.get("status") == "ok":
            continue
        if e and e.get("status") == "error" and not args.retry_errors:
            continue
        # Schon im Rohcache? Dann kostet es keine Anfrage.
        offen.append(m)
    if args.limit:
        offen = offen[: args.limit]
    log("Kandidaten: %d, offen: %d" % (len(kand), len(offen)))

    fetcher = fe.EspnFetcher(pause=args.pause)
    ok = fehler = in_folge = 0
    for i, m in enumerate(offen, start=1):
        try:
            ereignisse = fetcher.fetch(m)
            fortschritt[m["match_id"]] = {
                "status": "ok", "events": ereignisse,
                "geholt": time.strftime("%Y-%m-%d %H:%M")}
            ok += 1
            in_folge = 0
        except Exception as exc:
            warn("%s: %s" % (m["match_id"], exc))
            fortschritt[m["match_id"]] = {"status": "error", "error": str(exc)}
            fehler += 1
            in_folge += 1
            if in_folge >= 5:
                log("Abbruch: 5 Fehler in Folge. Fortschritt gesichert.")
                break
        # Alle 25 Spiele reicht: was hier verlorenginge, liegt ohnehin
        # im Rohcache und kostet beim naechsten Lauf keine Anfrage.
        if i % 25 == 0:
            common.write_text(FORTSCHRITT, json.dumps(fortschritt))
        if i % 50 == 0:
            log("  %d/%d (%d ok, %d Fehler)" % (i, len(offen), ok, fehler))
    common.write_text(FORTSCHRITT, json.dumps(fortschritt))
    log("Fertig: %d ok, %d Fehler, insgesamt %d im Fortschritt"
        % (ok, fehler, len(fortschritt)))
    common.error_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
