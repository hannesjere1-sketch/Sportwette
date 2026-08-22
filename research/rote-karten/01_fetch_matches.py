#!/usr/bin/env python3
"""Phase 1 — Spiele mit Roten Karten von football-data.co.uk holen.

Laedt je Liga und Saison eine CSV, behaelt nur die Spalten, die wir
brauchen, und schreibt zwei Dateien:

  data/matches_all.csv        alle Spiele (Basis fuer die Vergleichsgruppe)
  data/matches_with_reds.csv  nur Spiele mit mindestens einer Roten Karte

Zum Erweitern nur LEAGUES und SEASONS unten aendern.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import log, warn

# ------------------------------------------------------------- Einstellungen -
# START bewusst klein: Premier League, Saison 2023/24.
# Erweitern = einfach weitere Eintraege hinzufuegen.

LEAGUES = {
    "E0": "Premier League",
    # "D1":  "Bundesliga",
    # "SP1": "La Liga",
    # "I1":  "Serie A",
    # "F1":  "Ligue 1",
}

SEASONS = {
    "2324": "2023/24",
    # "2425": "2024/25",
    # "2223": "2022/23",
}

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"

# Spalten, die wir aus den 100+ Spalten der Quelle behalten.
# B365H/B365D/B365A sind die Schlussquoten — unser Mass fuer die
# Staerke der Mannschaften VOR dem Anpfiff.
KEEP = {
    "Date": "date",
    "Time": "time",
    "HomeTeam": "home_team_raw",
    "AwayTeam": "away_team_raw",
    "FTHG": "fthg",
    "FTAG": "ftag",
    "FTR": "ftr",
    "HTHG": "hthg",
    "HTAG": "htag",
    "HR": "hr",
    "AR": "ar",
    "B365H": "b365h",
    "B365D": "b365d",
    "B365A": "b365a",
}

FIELDS = [
    "match_id", "league", "league_name", "season", "season_name",
    "date", "time", "home_team", "away_team",
    "home_team_raw", "away_team_raw",
    "fthg", "ftag", "ftr", "hthg", "htag", "hr", "ar",
    "b365h", "b365d", "b365a",
]


def to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def iso_date(value):
    """football-data schreibt TT/MM/JJJJ (aeltere Saisons TT/MM/JJ)."""
    parts = (value or "").strip().split("/")
    if len(parts) != 3:
        return ""
    day, month, year = parts
    if len(year) == 2:
        year = "20" + year
    return "%s-%s-%s" % (year, month.zfill(2), day.zfill(2))


def make_match_id(league, season, date, home, away):
    slug = lambda s: common.normalise_team(s).replace(" ", "-")
    return "%s-%s-%s-%s-%s" % (league, season, date, slug(home), slug(away))


def parse_csv_text(text):
    """CSV-Text in Zeilen-Dicts. Robust gegen defekte Zeilen."""
    import csv
    import io
    # football-data liefert gelegentlich Latin-1-Zeichen und Leerzeilen
    # am Ende — beides faengt der DictReader ab.
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def fetch_one(league, season):
    url = BASE_URL.format(season=season, league=league)
    log("Lade %s %s: %s" % (league, season, url))
    status, text = common.http_get(url)
    if status != 200:
        warn("%s %s: HTTP %s (%s)" % (league, season, status, text[:120]))
        return []
    try:
        raw_rows = parse_csv_text(text)
    except Exception as exc:
        warn("%s %s: CSV nicht lesbar (%s)" % (league, season, exc))
        return []

    rows = []
    for i, raw in enumerate(raw_rows, start=2):  # Zeile 1 ist die Kopfzeile
        try:
            if not (raw.get("HomeTeam") or "").strip():
                continue  # Leerzeile am Dateiende
            date = iso_date(raw.get("Date"))
            if not date:
                warn("%s %s Zeile %d: Datum unlesbar (%r)"
                     % (league, season, i, raw.get("Date")))
                continue
            home_raw = (raw.get("HomeTeam") or "").strip()
            away_raw = (raw.get("AwayTeam") or "").strip()
            row = {
                "match_id": make_match_id(league, season, date, home_raw, away_raw),
                "league": league,
                "league_name": LEAGUES[league],
                "season": season,
                "season_name": SEASONS[season],
                "home_team": common.canonical_team(home_raw),
                "away_team": common.canonical_team(away_raw),
            }
            for src, dst in KEEP.items():
                row[dst] = (raw.get(src) or "").strip()
            row["date"] = date  # ISO, nicht die Rohform TT/MM/JJJJ
            row["hr"] = to_int(row["hr"])
            row["ar"] = to_int(row["ar"])
            rows.append(row)
        except Exception as exc:
            # Ein kaputtes Spiel darf den Lauf nicht killen.
            warn("%s %s Zeile %d uebersprungen: %s" % (league, season, i, exc))
    log("  %d Spiele gelesen" % len(rows))
    return rows


def main():
    all_rows = []
    for season in SEASONS:
        for league in LEAGUES:
            try:
                all_rows.extend(fetch_one(league, season))
            except Exception as exc:
                warn("%s %s komplett fehlgeschlagen: %s" % (league, season, exc))

    if not all_rows:
        warn("Keine Spiele geladen — nichts geschrieben.")
        common.error_summary()
        return 1

    # Doppelte match_ids koennen bei Datenfehlern der Quelle auftreten.
    seen = set()
    unique = []
    for row in all_rows:
        if row["match_id"] in seen:
            warn("Doppelte match_id uebersprungen: %s" % row["match_id"])
            continue
        seen.add(row["match_id"])
        unique.append(row)

    reds = [r for r in unique if r["hr"] > 0 or r["ar"] > 0]

    common.write_csv(os.path.join(common.DATA_DIR, "matches_all.csv"),
                     unique, FIELDS)
    common.write_csv(os.path.join(common.DATA_DIR, "matches_with_reds.csv"),
                     reds, FIELDS)

    log("Gesamt: %d Spiele, davon %d mit Roter Karte (%.1f %%)"
        % (len(unique), len(reds), 100.0 * len(reds) / len(unique)))
    log("Geschrieben: data/matches_all.csv, data/matches_with_reds.csv")
    common.error_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
