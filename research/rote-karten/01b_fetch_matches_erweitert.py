#!/usr/bin/env python3
"""Phase 1b — Spieldaten fuer die erweiterte Datenbasis.

Holt die Saison-CSVs von football-data.co.uk fuer

  * die fuenf bisherigen Ligen zurueck bis 2005/06
  * sechs weitere erste Ligen
  * fuenf zweite Ligen

und schreibt sie in dieselbe Struktur wie Phase 1.

BEWUSST NICHT AUFGENOMMEN — Begruendung im Bericht:
  Oesterreich, Schweiz, Daenemark, Norwegen, Schweden. Diese Ligen
  stehen nur in den Zusatzdateien von football-data.co.uk und fuehren
  dort AvgCH statt B365H — eine andere Quotenspalte mit anderer
  Margenstruktur. Norwegen und Schweden spielen ausserdem im
  Kalenderjahr. Die Schweiz fehlt zusaetzlich bei ESPN komplett.

Ausgabe:
  data/erw_matches_all.csv
  data/erw_matches_kandidaten.csv   (Heimquote unter 1,80 — nur diese
                                     brauchen spaeter einen ESPN-Abruf)
"""

import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import log, warn

# Kandidatengrenze: deckt alle drei Staerkevarianten (<1,30 / <1,50 /
# <1,80) ab. Alles darueber kann nie in die Auswertung geraten und
# braucht deshalb keinen Abruf.
KANDIDAT_GRENZE = 1.80

LIGEN = {
    # Kuerzel: (Anzeigename, Stufe)
    "E0":  ("Premier League", 1),
    "SP1": ("La Liga", 1),
    "D1":  ("Bundesliga", 1),
    "I1":  ("Serie A", 1),
    "F1":  ("Ligue 1", 1),
    "N1":  ("Eredivisie", 1),
    "P1":  ("Primeira Liga", 1),
    "B1":  ("Belgien Pro League", 1),
    "T1":  ("Süper Lig", 1),
    "G1":  ("Griechenland Super League", 1),
    "SC0": ("Scottish Premiership", 1),
    "E1":  ("Championship", 2),
    "D2":  ("2. Bundesliga", 2),
    "I2":  ("Serie B", 2),
    "SP2": ("LaLiga 2", 2),
    "F2":  ("Ligue 2", 2),
}

SAISONS = ["%02d%02d" % (j % 100, (j + 1) % 100) for j in range(5, 24)]

BASE = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"

FIELDS = [
    "match_id", "league", "league_name", "stufe", "season", "season_name",
    "date", "home_team", "away_team", "home_team_raw", "away_team_raw",
    "fthg", "ftag", "ftr", "hthg", "htag",
    "odds_h", "odds_d", "odds_a", "odds_quelle", "faire_heimquote",
]


def iso_date(value):
    teile = (value or "").strip().split("/")
    if len(teile) != 3:
        return ""
    tag, monat, jahr = teile
    if len(jahr) == 2:
        jahr = "20" + jahr
    return "%s-%s-%s" % (jahr, monat.zfill(2), tag.zfill(2))


def quoten(row):
    """B365 bevorzugt, sonst der Marktdurchschnitt. Gibt auch die Quelle.

    Die Spalte muss protokolliert werden: der Marktdurchschnitt hat eine
    andere Margenstruktur als ein einzelner Buchmacher, und die faire
    Quote faellt dadurch minimal anders aus.
    """
    for h, d, a, quelle in (("B365H", "B365D", "B365A", "B365"),
                            ("AvgH", "AvgD", "AvgA", "Avg"),
                            ("BbAvH", "BbAvD", "BbAvA", "BbAv")):
        if all((row.get(x) or "").strip() for x in (h, d, a)):
            return row[h].strip(), row[d].strip(), row[a].strip(), quelle
    return None


def hole(league, season):
    url = BASE.format(season=season, league=league)
    status, txt = common.http_get(url)
    if status != 200 or len(txt) < 200:
        return []
    try:
        roh = list(csv.DictReader(io.StringIO(txt)))
    except Exception as exc:
        warn("%s %s: CSV unlesbar (%s)" % (league, season, exc))
        return []

    name, stufe = LIGEN[league]
    saison_name = "20%s/%s" % (season[:2], season[2:])
    out = []
    for i, r in enumerate(roh, start=2):
        try:
            if not (r.get("HomeTeam") or "").strip():
                continue
            datum = iso_date(r.get("Date"))
            if not datum:
                continue
            q = quoten(r)
            if not q:
                continue          # ohne Quote kein Fall — siehe Bericht
            oh, od, oa, quelle = q
            probs = common.fair_probs(oh, od, oa)
            if not probs:
                continue
            heim_raw = (r.get("HomeTeam") or "").strip()
            gast_raw = (r.get("AwayTeam") or "").strip()
            slug = lambda s: common.normalise_team(s).replace(" ", "-")
            out.append({
                "match_id": "%s-%s-%s-%s-%s" % (league, season, datum,
                                                slug(heim_raw), slug(gast_raw)),
                "league": league, "league_name": name, "stufe": stufe,
                "season": season, "season_name": saison_name, "date": datum,
                "home_team": common.canonical_team(heim_raw),
                "away_team": common.canonical_team(gast_raw),
                "home_team_raw": heim_raw, "away_team_raw": gast_raw,
                "fthg": (r.get("FTHG") or "").strip(),
                "ftag": (r.get("FTAG") or "").strip(),
                "ftr": (r.get("FTR") or "").strip(),
                "hthg": (r.get("HTHG") or "").strip(),
                "htag": (r.get("HTAG") or "").strip(),
                "odds_h": oh, "odds_d": od, "odds_a": oa,
                "odds_quelle": quelle,
                "faire_heimquote": round(1.0 / probs[0], 4),
            })
        except Exception as exc:
            warn("%s %s Zeile %d: %s" % (league, season, i, exc))
    return out


def main():
    alle = []
    ohne_quote = {}
    for league in LIGEN:
        for season in SAISONS:
            zeilen = hole(league, season)
            if zeilen:
                alle.append((league, season, zeilen))
        gesamt = sum(len(z) for l, s, z in alle if l == league)
        log("%-4s %-26s %5d Spiele" % (league, LIGEN[league][0], gesamt))

    flach = [z for _, _, zeilen in alle for z in zeilen]
    if not flach:
        warn("Nichts geladen.")
        return 1

    # Doppelte match_ids koennen bei Datenfehlern der Quelle auftreten.
    gesehen = set()
    eindeutig = []
    for z in flach:
        if z["match_id"] in gesehen:
            warn("Doppelte match_id: %s" % z["match_id"])
            continue
        gesehen.add(z["match_id"])
        eindeutig.append(z)

    kandidaten = [z for z in eindeutig
                  if z["faire_heimquote"] < KANDIDAT_GRENZE]

    common.write_csv(os.path.join(common.DATA_DIR, "erw_matches_all.csv"),
                     eindeutig, FIELDS)
    common.write_csv(os.path.join(common.DATA_DIR, "erw_matches_kandidaten.csv"),
                     kandidaten, FIELDS)
    log("Gesamt: %d Spiele, davon %d mit Heimquote unter %.2f (%.1f %%)"
        % (len(eindeutig), len(kandidaten), KANDIDAT_GRENZE,
           100.0 * len(kandidaten) / len(eindeutig)))
    common.error_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
