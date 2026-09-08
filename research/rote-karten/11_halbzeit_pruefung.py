"""Phase 10b - Halbzeit-Gegenprobe.

Der Endstand-Abgleich zeigt nur, ob die SUMME der Tore stimmt. Er wuerde
zwei sich aufhebende Fehler nicht bemerken. Genau darauf kommt es beim
35er-Trigger aber an: er haengt daran, WER das erste Tor erzielt und WANN.

Deshalb hier die zweite, unabhaengige Probe: aus den ESPN-Ereignissen der
ersten Halbzeit wird der Halbzeitstand rekonstruiert und mit dem
Halbzeitstand von football-data.co.uk verglichen (Spalten HTHG/HTAG).
Beide Quellen wissen nichts voneinander.

Ein Fall des 35er-Triggers liegt per Definition vor Minute 35, also immer
in der ersten Halbzeit - der Halbzeitstand deckt ihn ab.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import log, write_csv  # noqa: E402

HIER = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HIER, "data", "cache")
TEAMID_RE = re.compile(r"/teams/(\d+)")
CLOCK_RE = re.compile(r"^(\d+)(?:\+(\d+))?")


def lade_teamids():
    out = {}
    with open(os.path.join(HIER, "data", "erw_teamids.csv"),
              newline="", encoding="utf-8") as fh:
        for reihe in csv.reader(fh):
            if len(reihe) >= 3 and reihe[1].isdigit():
                out[reihe[0]] = (reihe[1], reihe[2])
    return out


def pruefe(auftrag):
    match_id, hid, aid, fthg, ftag, hthg, htag, ist_fall = auftrag
    pfad = os.path.join(CACHE, "espn_plays_%s.json" % match_id)
    try:
        with open(pfad, encoding="utf-8") as fh:
            daten = json.load(fh)
    except Exception:
        return None

    end_h = end_a = hz_h = hz_a = 0
    eigentor_h1 = False
    for eintrag in daten.get("items") or []:
        if not eintrag.get("scoringPlay"):
            continue
        treffer = TEAMID_RE.search(((eintrag.get("team") or {}).get("$ref") or ""))
        if not treffer:
            return {"match_id": match_id, "ist_fall": ist_fall,
                    "status": "Tor ohne Team", "eigentor_h1": "0"}
        tid = treffer.group(1)
        if tid == hid:
            end_h += 1
        elif tid == aid:
            end_a += 1
        else:
            return {"match_id": match_id, "ist_fall": ist_fall,
                    "status": "Tor ohne Team", "eigentor_h1": "0"}
        # Erste Halbzeit? ESPN fuehrt period.number; als Rueckfall die Uhr.
        periode = (eintrag.get("period") or {}).get("number")
        uhr = CLOCK_RE.search(((eintrag.get("clock") or {}).get("displayValue") or ""))
        if periode is None:
            erste = bool(uhr) and int(uhr.group(1)) <= 45
        else:
            erste = periode == 1
        if erste:
            if tid == hid:
                hz_h += 1
            else:
                hz_a += 1
            typ = ((eintrag.get("type") or {}).get("text") or "").strip()
            if typ == "Own Goal":
                eigentor_h1 = True

    if (end_h, end_a) != (fthg, ftag):
        status = "Endstand weicht ab"
    elif hthg is None:
        status = "kein Halbzeitstand bei football-data"
    elif (hz_h, hz_a) == (hthg, htag):
        status = "Halbzeit stimmt"
    else:
        status = "Halbzeit weicht ab"
    return {
        "match_id": match_id,
        "ist_fall": ist_fall,
        "status": status,
        "espn_hz": "%d:%d" % (hz_h, hz_a),
        "fd_hz": "%s:%s" % (hthg, htag),
        "eigentor_h1": "1" if eigentor_h1 else "0",
    }


def main():
    teamids = lade_teamids()
    with open(os.path.join(HIER, "data", "erw_matches_kandidaten.csv"),
              newline="", encoding="utf-8") as fh:
        kandidaten = list(csv.DictReader(fh))
    with open(os.path.join(HIER, "data", "35er-erweitert-faelle.csv"),
              newline="", encoding="utf-8") as fh:
        fall_ids = {r["match_id"] for r in csv.DictReader(fh)}

    auftraege = []
    for reihe in kandidaten:
        mid = reihe["match_id"]
        if mid not in teamids:
            continue
        if not os.path.exists(os.path.join(CACHE, "espn_plays_%s.json" % mid)):
            continue
        try:
            fthg, ftag = int(reihe["fthg"]), int(reihe["ftag"])
        except ValueError:
            continue
        try:
            hthg, htag = int(reihe["hthg"]), int(reihe["htag"])
        except (ValueError, KeyError):
            hthg = htag = None
        hid, aid = teamids[mid]
        auftraege.append((mid, hid, aid, fthg, ftag, hthg, htag,
                          "1" if mid in fall_ids else "0"))

    log("pruefe %d Spiele auf Halbzeitstand" % len(auftraege))
    ergebnisse = []
    with Pool(4) as pool:
        for res in pool.imap_unordered(pruefe, auftraege, chunksize=64):
            if res:
                ergebnisse.append(res)

    ergebnisse.sort(key=lambda r: r["match_id"])

    def bericht(titel, menge):
        z = Counter(r["status"] for r in menge)
        pruefbar = z["Halbzeit stimmt"] + z["Halbzeit weicht ab"]
        log("")
        log("%s (%d Spiele)" % (titel, len(menge)))
        for status, anz in z.most_common():
            log("   %-38s %6d" % (status, anz))
        if pruefbar:
            log("   -> von %d pruefbaren stimmen %d  (%.2f %%)"
                % (pruefbar, z["Halbzeit stimmt"],
                   z["Halbzeit stimmt"] / pruefbar * 100))
        return z

    bericht("Alle zwischengespeicherten Spiele", ergebnisse)
    faelle = [r for r in ergebnisse if r["ist_fall"] == "1"]
    bericht("Nur die 35er-Faelle", faelle)
    og = [r for r in ergebnisse if r["eigentor_h1"] == "1"]
    bericht("Nur Spiele mit Eigentor in der ersten Halbzeit", og)

    abw = [r for r in faelle if r["status"] == "Halbzeit weicht ab"]
    if abw:
        log("")
        log("35er-Faelle mit abweichendem Halbzeitstand:")
        for r in abw:
            log("   %-55s ESPN %s  football-data %s"
                % (r["match_id"], r["espn_hz"], r["fd_hz"]))

    write_csv(os.path.join(HIER, "data", "halbzeit-pruefung.csv"), ergebnisse,
              ["match_id", "ist_fall", "status", "espn_hz", "fd_hz", "eigentor_h1"])
    log("")
    log("geschrieben: data/halbzeit-pruefung.csv")


if __name__ == "__main__":
    main()
