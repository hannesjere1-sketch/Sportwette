"""Phase 10a - Vollstaendige Eigentor-Pruefung.

Frage: Ordnet ESPN Eigentore der richtigen Mannschaft zu?

Methode: Fuer JEDES zwischengespeicherte Spiel, in dem mindestens ein
Eigentor vorkommt, wird der Endstand allein aus den Team-Referenzen der
Tor-Ereignisse rekonstruiert und mit dem Endstand von football-data.co.uk
verglichen - zwei voellig unabhaengige Quellen.

Stimmen beide ueberein, hat ESPN das Eigentor der Mannschaft gutgeschrieben,
der es zaehlt (also der gegnerischen). Weicht es ab, wird der Fall einzeln
ausgegeben, damit die Ursache benannt werden kann statt geschaetzt.

Frueher wurde das an einer Stichprobe von 80 Spielen geprueft. Diese
Fassung prueft alle - eine Stichprobe laesst offen, ob die Ausnahmen
Zufall oder Muster sind.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import log, write_csv  # noqa: E402

HIER = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HIER, "data", "cache")
TEAMID_RE = re.compile(r"/teams/(\d+)")


def lade_teamids():
    pfad = os.path.join(HIER, "data", "erw_teamids.csv")
    out = {}
    with open(pfad, newline="", encoding="utf-8") as fh:
        for reihe in csv.reader(fh):
            if len(reihe) >= 3 and reihe[1].isdigit():
                out[reihe[0]] = (reihe[1], reihe[2])
    return out


def lade_kandidaten():
    pfad = os.path.join(HIER, "data", "erw_matches_kandidaten.csv")
    with open(pfad, newline="", encoding="utf-8") as fh:
        return {r["match_id"]: r for r in csv.DictReader(fh)}


def pruefe(auftrag):
    """Laeuft im Unterprozess. Gibt None zurueck, wenn kein Eigentor drin ist."""
    match_id, hid, aid, fthg, ftag = auftrag
    pfad = os.path.join(CACHE, "espn_plays_%s.json" % match_id)
    try:
        with open(pfad, encoding="utf-8") as fh:
            daten = json.load(fh)
    except Exception:
        return None
    items = daten.get("items") or []

    eigentore = []
    heim = gast = 0
    ohne_team = 0
    for eintrag in items:
        # gleiche Erkennung wie in 09_erweitert_auswertung.py: das Feld
        # scoringPlay, nicht der Typ-Text. Nur so zaehlen verwandelte
        # Elfmeter mit und aberkannte Tore nicht.
        if not eintrag.get("scoringPlay"):
            continue
        typ = ((eintrag.get("type") or {}).get("text") or "").strip()
        treffer = TEAMID_RE.search(((eintrag.get("team") or {}).get("$ref") or ""))
        if not treffer:
            ohne_team += 1
            continue
        tid = treffer.group(1)
        if tid == hid:
            heim += 1
            seite = "heim"
        elif tid == aid:
            gast += 1
            seite = "gast"
        else:
            ohne_team += 1
            seite = "fremd"
        text = (eintrag.get("text") or "")
        if typ == "Own Goal" or "Own Goal" in text:
            eigentore.append((
                (eintrag.get("clock") or {}).get("displayValue", ""),
                seite,
                text[:120],
            ))

    passt = (heim, gast) == (fthg, ftag)
    # Wuerde ein Umdrehen der Eigentore die Abweichung beheben? Nur dann
    # waere die Zuordnung des Eigentors die Ursache.
    n_heim_og = sum(1 for _, seite, _ in eigentore if seite == "heim")
    n_gast_og = sum(1 for _, seite, _ in eigentore if seite == "gast")
    gedreht_passt = False
    if eigentore and not passt:
        for k in range(n_heim_og + 1):
            for l in range(n_gast_og + 1):
                if (heim - k + l, gast - l + k) == (fthg, ftag) and (k or l):
                    gedreht_passt = True
    return {
        "match_id": match_id,
        "eigentore": len(eigentore),
        "espn_stand": "%d:%d" % (heim, gast),
        "fd_stand": "%d:%d" % (fthg, ftag),
        "passt": "1" if passt else "0",
        "drehen_wuerde_helfen": "1" if gedreht_passt else "0",
        "tore_ohne_team": ohne_team,
        "details": eigentore,
    }


def main():
    teamids = lade_teamids()
    kandidaten = lade_kandidaten()

    auftraege = []
    for match_id, reihe in kandidaten.items():
        if match_id not in teamids:
            continue
        if not os.path.exists(os.path.join(CACHE, "espn_plays_%s.json" % match_id)):
            continue
        hid, aid = teamids[match_id]
        try:
            auftraege.append((match_id, hid, aid,
                              int(reihe["fthg"]), int(reihe["ftag"])))
        except ValueError:
            continue

    log("pruefe %d zwischengespeicherte Spiele" % len(auftraege))

    alle = []
    with Pool(4) as pool:
        for i, res in enumerate(pool.imap_unordered(pruefe, auftraege, chunksize=64), 1):
            if res:
                alle.append(res)
            if i % 5000 == 0:
                log("  %d/%d" % (i, len(auftraege)))

    alle.sort(key=lambda r: r["match_id"])
    mit_og = [r for r in alle if r["eigentore"] > 0]
    ohne_og = [r for r in alle if r["eigentore"] == 0]

    def quote(menge):
        n = len(menge)
        ab = sum(1 for r in menge if r["passt"] == "0")
        return n, ab, (ab / n * 100 if n else 0.0)

    n1, ab1, q1 = quote(mit_og)
    n2, ab2, q2 = quote(ohne_og)
    log("")
    log("Spiele mit Eigentor:  %5d   Endstand weicht ab: %4d  (%.2f %%)" % (n1, ab1, q1))
    log("Spiele ohne Eigentor: %5d   Endstand weicht ab: %4d  (%.2f %%)" % (n2, ab2, q2))
    log("")

    drehen = [r for r in mit_og if r["drehen_wuerde_helfen"] == "1"]
    log("davon durch Umdrehen der Eigentor-Zuordnung erklaerbar: %d" % len(drehen))
    for r in drehen:
        log("  %s  ESPN %s  football-data %s" % (r["match_id"], r["espn_stand"], r["fd_stand"]))
        for minute, seite, text in r["details"]:
            log("      %s -> %s  %s" % (minute, seite, text))

    from collections import Counter
    liga = Counter(r["match_id"].split("-")[0] for r in mit_og if r["passt"] == "0")
    liga_ges = Counter(r["match_id"].split("-")[0] for r in mit_og)
    log("")
    log("Abweichungen bei Eigentor-Spielen nach Liga:")
    for lg, anz in liga.most_common():
        log("  %-4s %3d von %3d  (%.1f %%)" % (lg, anz, liga_ges[lg], anz / liga_ges[lg] * 100))
    liga2 = Counter(r["match_id"].split("-")[0] for r in ohne_og if r["passt"] == "0")
    liga2_ges = Counter(r["match_id"].split("-")[0] for r in ohne_og)
    log("")
    log("Abweichungen bei Spielen OHNE Eigentor nach Liga:")
    for lg in sorted(liga2_ges):
        log("  %-4s %3d von %4d  (%.1f %%)" % (lg, liga2[lg], liga2_ges[lg],
                                               liga2[lg] / liga2_ges[lg] * 100))

    write_csv(
        os.path.join(HIER, "data", "eigentor-pruefung.csv"),
        [{k: v for k, v in r.items() if k != "details"} for r in alle],
        ["match_id", "eigentore", "espn_stand", "fd_stand", "passt",
         "drehen_wuerde_helfen", "tore_ohne_team"],
    )
    log("geschrieben: data/eigentor-pruefung.csv")


if __name__ == "__main__":
    main()
