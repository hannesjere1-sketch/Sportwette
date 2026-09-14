#!/usr/bin/env python3
"""Phase 2c — ESPN-Abruf parallel und im Vordergrund.

Warum diese Variante: abgekoppelte Hintergrundprozesse ueberleben in
dieser Umgebung nicht — zwei Laeufe starben jeweils 11 bis 14 Minuten
nach dem Start an einem Netzaussetzer. Dieses Skript laeuft deshalb im
Vordergrund, begrenzt auf eine vorgegebene Laufzeit, und wird so oft
aufgerufen, bis nichts mehr offen ist.

Der Rohcache in data/cache/ IST der Fortschritt. Eine eigene
Fortschrittsdatei gibt es hier nicht: wer abbricht, verliert hoechstens
die gerade laufenden Anfragen.

Tempo: mehrere Arbeiter mit je eigener Pause. Bei 6 Arbeitern und 1,5 s
sind das 4 Anfragen je Sekunde. Das ist deutlich schneller als die
bisherigen 0,5/s, aber fuer einen einmaligen Nachlauf vertretbar — in
bisher rund 20000 Anfragen hat ESPN kein einziges Mal gebremst.
"""

import argparse
import importlib
import json
import os
import queue
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import log, warn

fe = importlib.import_module("02_fetch_events")
CACHE = os.path.join(common.DATA_DIR, "cache")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=540,
                    help="Laufzeit, danach sauberer Ausstieg")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--resolve-only", action="store_true",
                    help="nur die Adressen aufloesen und ablegen")
    ap.add_argument("--pause", type=float, default=1.5,
                    help="Pause je Arbeiter zwischen zwei Anfragen")
    args = ap.parse_args()

    kand = common.read_csv(os.path.join(common.DATA_DIR,
                                        "erw_matches_kandidaten.csv"))
    offen = [m for m in kand
             if not os.path.isfile(os.path.join(CACHE, "espn_plays_%s.json"
                                                % m["match_id"]))]
    log("Kandidaten %d, offen %d" % (len(kand), len(offen)))
    if not offen:
        log("Nichts zu tun.")
        return 0

    # Schritt 1: Adressen der Spielverlaeufe. Das kostet 608
    # Spielplan-Abrufe und 17000 Zuordnungen — deshalb einmal machen und
    # das Ergebnis ablegen. Spaetere Laeufe lesen es nur noch.
    url_datei = os.path.join(common.DATA_DIR, "erw_plays_urls.csv")
    bekannt = {r["match_id"]: r["url"]
               for r in common.read_csv(url_datei)} if os.path.isfile(url_datei) else {}
    # Spiele, die ESPN nicht kennt, werden mit leerer Adresse vermerkt —
    # sonst sucht jeder Lauf sie erneut.
    fehlt = [m for m in offen if m["match_id"] not in bekannt]
    if fehlt:
        log("Adressen aufloesen fuer %d Spiele (einmalig) …" % len(fehlt))
        plan_fetcher = fe.EspnFetcher(pause=0.6)
        gemeldet = set()
        for i, m in enumerate(fehlt, start=1):
            try:
                bekannt[m["match_id"]] = plan_fetcher.plays_url(m)
            except Exception as exc:
                bekannt[m["match_id"]] = ""
                schluessel = "%s-%s" % (m["league"], m["season"])
                if schluessel not in gemeldet:
                    gemeldet.add(schluessel)
                    warn("%s: %s" % (m["match_id"], str(exc)[:110]))
            if i % 2000 == 0:
                log("  %d/%d zugeordnet" % (i, len(fehlt)))
                common.write_csv(url_datei,
                                 [{"match_id": k, "url": v} for k, v in bekannt.items()],
                                 ["match_id", "url"])
        common.write_csv(url_datei,
                         [{"match_id": k, "url": v} for k, v in bekannt.items()],
                         ["match_id", "url"])
    aufgaben = [(m["match_id"], bekannt[m["match_id"]])
                for m in offen if bekannt.get(m["match_id"])]
    log("Adressen bekannt: %d von %d" % (len(aufgaben), len(offen)))
    if args.resolve_only:
        return 0

    ende = time.time() + args.seconds
    aufgabe_q = queue.Queue()
    for a in aufgaben:
        aufgabe_q.put(a)

    zaehler = {"ok": 0, "fehler": 0}
    sperre = threading.Lock()

    def arbeiter():
        sess = common.new_session({"Accept": "application/json"})
        while time.time() < ende:
            try:
                match_id, url = aufgabe_q.get_nowait()
            except queue.Empty:
                return
            pfad = os.path.join(CACHE, "espn_plays_%s.json" % match_id)
            if os.path.isfile(pfad):
                continue
            status, text = common.http_get(url, session=sess)
            if status == 200:
                try:
                    json.loads(text)          # nur gueltiges JSON ablegen
                    with open(pfad, "w", encoding="utf-8") as fh:
                        fh.write(text)
                    with sperre:
                        zaehler["ok"] += 1
                except Exception:
                    with sperre:
                        zaehler["fehler"] += 1
            else:
                with sperre:
                    zaehler["fehler"] += 1
            time.sleep(args.pause)

    threads = [threading.Thread(target=arbeiter, daemon=True)
               for _ in range(args.workers)]
    for t in threads:
        t.start()

    letzte = 0
    while any(t.is_alive() for t in threads) and time.time() < ende:
        time.sleep(15)
        with sperre:
            jetzt = zaehler["ok"]
        if jetzt != letzte:
            rest = len(offen) - jetzt
            log("  %d geholt, %d Fehler, noch %d offen"
                % (jetzt, zaehler["fehler"], rest))
            letzte = jetzt
    for t in threads:
        t.join(timeout=5)

    imc = sum(1 for m in kand
              if os.path.isfile(os.path.join(CACHE, "espn_plays_%s.json"
                                             % m["match_id"])))
    log("Ende: %d ok, %d Fehler in diesem Lauf" % (zaehler["ok"], zaehler["fehler"]))
    log("Im Cache jetzt %d von %d (%.1f %%), offen %d"
        % (imc, len(kand), 100.0 * imc / len(kand), len(kand) - imc))
    common.error_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
