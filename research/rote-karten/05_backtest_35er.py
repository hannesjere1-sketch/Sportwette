#!/usr/bin/env python3
"""Backtest der 35er-Strategie auf dem vorhandenen ESPN-Cache.

FALLDEFINITION
--------------
Ein Spiel zaehlt fuer eine Mannschaft, wenn

  * das ERSTE Tor des Spiels vor Minute 35 faellt, und
  * der Gegner es erzielt.

Aus Sicht dieser Mannschaft steht es dann 0:1, und sie hat bis dahin
selbst nicht getroffen — das folgt zwingend daraus, dass es das erste
Tor des Spiels war. Staende wie 1:1 oder 2:1 koennen also nie ein Fall
sein.

  Treffer      = diese Mannschaft gewinnt am Ende
  Fehlschlag   = Unentschieden oder Niederlage

Je Spiel kann es hoechstens einen Fall geben: nur eine Mannschaft kann
das erste Tor kassieren.

DATENQUELLE
-----------
Ausschliesslich der bereits geholte ESPN-Cache unter data/cache/ und die
Endergebnisse aus data/matches_all.csv. Es werden keine neuen Abrufe
gemacht — fehlende Spiele werden gemeldet, nicht nachgeladen.

Nur Ligaspiele: matches_all.csv enthaelt ausschliesslich die Liga-CSVs
von football-data.co.uk, Pokal- und Europapokalspiele sind gar nicht
erst darin.

AUSGABE
-------
  data/35er-backtest.json   alle Gruppen als JSON
  data/35er-faelle.csv      jeder Einzelfall zum Nachpruefen
  results/35er.md           lesbare Zusammenfassung
"""

import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import log, warn, de

# ------------------------------------------------------------- Einstellungen -

VOR_MINUTE = 35           # das Tor muss VOR dieser Minute fallen
MARGE = 1.05              # Aufschlag auf die noetige Mindestquote
MIN_FAELLE = 30           # darunter: nicht belastbar
THIN = "zu wenig Daten"

MINUTE_BLOECKE = [(1, 10, "1-10"), (11, 20, "11-20"), (21, 34, "21-34")]
BLOCK_ORDER = [b[2] for b in MINUTE_BLOECKE]

# Die 13 im Portal markierten Clubs, von Hand auf die Namen in
# matches_all.csv abgebildet. Bewusst keine automatische Zuordnung:
# "FC Bayern München (F)" wuerde sonst auf die Maennermannschaft
# fallen, und "Paris Saint-Germain" kommt gegen "paris sg" ueber keine
# vernuenftige Aehnlichkeitsschwelle.
MARKIERT = {
    "AC Milan": "milan",
    "Arsenal": "Arsenal",
    "Borussia Dortmund": "dortmund",
    "FC Barcelona": "barcelona",
    "FC Bayern München": "bayern munich",
    "FC Bayern München (F)": None,   # Frauen-Bundesliga, siehe README
    "Inter": "inter",
    "Liverpool FC": "Liverpool",
    "Manchester City": "Manchester City",
    "Olympique de Marseille": "marseille",
    "Paris Saint-Germain": "paris sg",
    "Real Madrid": "real madrid",
    "SSC Napoli": "napoli",
}
MARKIERTE_NAMEN = set(v for v in MARKIERT.values() if v)

CACHE_DIR = os.path.join(common.DATA_DIR, "cache")
CLOCK_RE = re.compile(r"(\d{1,3})'(?:\s*\+\s*(\d{1,2})')?")

FALL_FELDER = [
    "match_id", "league", "season", "date", "team", "gegner", "ort",
    "minute", "minute_block", "faire_quote", "staerke", "markiert",
    "endstand", "ergebnis", "treffer",
]


# ------------------------------------------------------------------ Helfer ---

def tor_minute(play):
    """Minute und Nachspielzeit eines Ereignisses."""
    m = CLOCK_RE.search(((play.get("clock") or {}).get("displayValue") or ""))
    if not m:
        return None, 0
    minute = int(m.group(1))
    extra = int(m.group(2) or 0)
    if not extra:
        zusatz = ((play.get("addedClock") or {}).get("displayValue") or "").strip()
        if zusatz.isdigit():
            extra = int(zusatz)
    return minute, extra


def minute_block(minute):
    for lo, hi, label in MINUTE_BLOECKE:
        if lo <= minute <= hi:
            return label
    return None


def lies_tore(match_id):
    """Alle Tore eines Spiels aus dem Cache, nach Minute sortiert.

    Die Cache-Dateien sind rund 380 KB gross und enthalten den ganzen
    Spielverlauf mit Paessen und Zweikaempfen. Bei 16000 Spielen lohnt
    es sich, jede Datei genau EINMAL zu lesen und daraus sowohl das
    erste Tor als auch den Endstand abzuleiten.
    """
    pfad = os.path.join(CACHE_DIR, "espn_plays_%s.json" % match_id)
    if not os.path.isfile(pfad):
        return None, "nicht im Cache"
    try:
        with open(pfad, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception as exc:
        return None, "Cache unlesbar (%s)" % exc

    tore = []
    for play in payload.get("items", []):
        if not play.get("scoringPlay"):
            continue
        minute, extra = tor_minute(play)
        if minute is None:
            continue
        tore.append((minute, extra, play.get("homeScore"), play.get("awayScore")))
    tore.sort()
    return tore, None


def erstes_tor(tore):
    """(minute, extra, seite) des ersten Tores — oder (None, Grund).

    Die Seite wird am laufenden Spielstand abgelesen, den ESPN an jedes
    Tor schreibt. Damit ist auch bei Eigentoren klar, wem das Tor
    gutgeschrieben wurde.
    """
    if not tore:
        return None, "torlos"
    minute, extra, hs, as_ = tore[0]
    # Nach dem ersten Tor MUSS es 1:0 oder 0:1 stehen. Alles andere
    # heisst, dass Reihenfolge oder Spielstand nicht stimmen — dann
    # lieber verwerfen als falsch zaehlen.
    if (hs, as_) == (1, 0):
        return (minute, extra, "home"), None
    if (hs, as_) == (0, 1):
        return (minute, extra, "away"), None
    return None, "erster Spielstand unplausibel (%s:%s)" % (hs, as_)


def endstand_stimmt(tore, match):
    """Selbstpruefung: nachgezaehlter Endstand gegen den gemeldeten."""
    fh_, fa_ = int(match["fthg"]), int(match["ftag"])
    if not tore:
        return fh_ == 0 and fa_ == 0
    letzte = tore[-1]
    return (letzte[2], letzte[3]) == (fh_, fa_)


# ------------------------------------------------------------------ Faelle ---

def sammle_faelle():
    matches = common.read_csv(os.path.join(common.DATA_DIR, "matches_all.csv"))
    if not matches:
        warn("matches_all.csv fehlt — bitte 01_fetch_matches.py laufen lassen.")
        return [], {}

    faelle = []
    grund = {}
    for match in matches:
        try:
            tore, problem = lies_tore(match["match_id"])
            if problem:
                grund[problem] = grund.get(problem, 0) + 1
                continue
            treffer, problem = erstes_tor(tore)
            if problem:
                grund[problem] = grund.get(problem, 0) + 1
                continue
            minute, extra, seite = treffer

            # Nachspielzeit der ersten Halbzeit liegt bei Minute 45 und
            # damit ohnehin ausserhalb; ein Tor "34+1" gibt es nicht.
            if minute >= VOR_MINUTE:
                grund["erstes Tor ab Minute %d" % VOR_MINUTE] = \
                    grund.get("erstes Tor ab Minute %d" % VOR_MINUTE, 0) + 1
                continue
            block = minute_block(minute)
            if block is None:
                grund["Minute ausserhalb der Bloecke"] = grund.get("Minute ausserhalb der Bloecke", 0) + 1
                continue

            if not endstand_stimmt(tore, match):
                grund["Endstand weicht ab"] = grund.get("Endstand weicht ab", 0) + 1
                continue

            probs = common.fair_probs(match["b365h"], match["b365d"], match["b365a"])
            if not probs:
                grund["Quoten fehlen"] = grund.get("Quoten fehlen", 0) + 1
                continue
            p_home, _, p_away = probs

            # Das Tor fiel fuer "seite" — betroffen ist die andere Seite.
            if seite == "home":
                team, gegner, ort = match["away_team"], match["home_team"], "auswaerts"
                prob, gewonnen = p_away, match["ftr"] == "A"
            else:
                team, gegner, ort = match["home_team"], match["away_team"], "heim"
                prob, gewonnen = p_home, match["ftr"] == "H"

            faire_quote = 1.0 / prob if prob > 0 else None
            faelle.append({
                "match_id": match["match_id"],
                "league": match["league"],
                "season": match["season"],
                "date": match["date"],
                "team": team,
                "gegner": gegner,
                "ort": ort,
                "minute": minute,
                "minute_block": block,
                "faire_quote": round(faire_quote, 3) if faire_quote else "",
                "staerke": common.strength_bucket(faire_quote),
                "markiert": "ja" if team in MARKIERTE_NAMEN else "nein",
                "endstand": "%s:%s" % (match["fthg"], match["ftag"]),
                "ergebnis": "sieg" if gewonnen else
                            ("unentschieden" if match["ftr"] == "D" else "niederlage"),
                "treffer": 1 if gewonnen else 0,
            })
        except Exception as exc:
            warn("%s uebersprungen: %s" % (match.get("match_id"), exc))

    log("Spiele geprueft: %d" % len(matches))
    for k in sorted(grund, key=lambda x: -grund[x]):
        log("  ohne Fall (%s): %d" % (k, grund[k]))
    log("Faelle: %d" % len(faelle))
    return faelle, grund


# ---------------------------------------------------------------- Auswertung -

def kennzahlen(label, faelle):
    n = len(faelle)
    treffer = sum(f["treffer"] for f in faelle)
    quote = treffer / n if n else 0.0
    lo, hi = common.wilson(treffer, n)
    return {
        "gruppe": label,
        "n": n,
        "treffer": treffer,
        "trefferquote": round(100.0 * quote, 1),
        "ci_unten": round(100.0 * lo, 1),
        "ci_oben": round(100.0 * hi, 1),
        # Bei dieser Trefferquote muss die Wettquote mindestens so hoch
        # sein, damit unterm Strich etwas uebrig bleibt — inklusive 5 %
        # Sicherheitsaufschlag.
        "mindestquote": round(MARGE / quote, 2) if quote > 0 else None,
        "hinweis": THIN if n < MIN_FAELLE else "",
    }


def gruppiere(faelle, key, order=None):
    eimer = {}
    for f in faelle:
        eimer.setdefault(f[key], []).append(f)
    labels = [l for l in (order or []) if l in eimer]
    labels += sorted(l for l in eimer if l not in labels)
    return [kennzahlen(l, eimer[l]) for l in labels]


# ------------------------------------------------------------------ Ausgabe --

def md_tabelle(zeilen, spalte="Gruppe"):
    out = ["| %s | n | Treffer | Trefferquote | 95 %%-Intervall | Mindestquote | Hinweis |" % spalte,
           "| --- | ---: | ---: | ---: | :---: | ---: | --- |"]
    for r in zeilen:
        mq = "—" if r["mindestquote"] is None else de(r["mindestquote"], 2)
        out.append("| %s | %d | %d | %s %% | %s – %s %% | %s | %s |" % (
            r["gruppe"], r["n"], r["treffer"], de(r["trefferquote"]),
            de(r["ci_unten"]), de(r["ci_oben"]), mq, r["hinweis"] or "—"))
    return "\n".join(out)


def baue_markdown(faelle, gesamt, gruppen, umfang):
    g = gesamt[0]
    lines = [
        "# Backtest der 35er-Strategie",
        "",
        "**Ein Fall entsteht, wenn das erste Tor des Spiels vor Minute %d"
        % VOR_MINUTE + " fällt und der Gegner es erzielt.**",
        "Aus Sicht der betroffenen Mannschaft steht es dann 0:1 — dass sie",
        "bis dahin selbst nicht getroffen hat, folgt zwingend daraus, dass es",
        "das *erste* Tor war. Stände wie 1:1 oder 2:1 können also nie ein",
        "Fall sein. Treffer heißt: diese Mannschaft gewinnt am Ende.",
        "Unentschieden zählt als Fehlschlag.",
        "",
        "Grundlage sind **%d Ligaspiele** aus %d Ligen und %d Saisons (%s)."
        % (umfang["spiele"], len(umfang["ligen"]), len(umfang["saisons"]),
           ", ".join(umfang["saisons"])),
        "Pokal- und Europapokalspiele sind nicht enthalten.",
        "",
        "## Das Wichtigste zuerst",
        "",
        "| | |",
        "|---|---|",
        "| Fälle | **%d** |" % g["n"],
        "| Treffer | %d |" % g["treffer"],
        "| Trefferquote | **%s %%** (%s – %s %%) |"
        % (de(g["trefferquote"]), de(g["ci_unten"]), de(g["ci_oben"])),
        "| Benötigte Mindestquote | **%s** |" % de(g["mindestquote"], 2),
        "",
        "Die Mindestquote ist `1 ÷ Trefferquote × 1,05`. Liegt die Quote,",
        "die dir im Moment des Gegentors angeboten wird, darunter, verlierst",
        "du auf Dauer Geld — egal wie richtig sich die Wette anfühlt.",
        "",
        "---",
        "",
    ]
    for titel, hinweis, zeilen, spalte in gruppen:
        lines += ["## %s" % titel, ""]
        if hinweis:
            lines += [hinweis, ""]
        lines += [md_tabelle(zeilen, spalte), ""]
    lines += [
        "---",
        "",
        "## Wie das zu lesen ist",
        "",
        "- Das **95-%-Intervall** (Wilson) sagt, wie sicher die Quote ist.",
        "  Ein breites Intervall heißt: zu wenig Fälle.",
        "- Gruppen mit weniger als %d Fällen sind als „%s\" markiert."
        % (MIN_FAELLE, THIN),
        "- Die **Mindestquote** enthält 5 % Aufschlag. Ohne diesen Puffer",
        "  wäre man exakt bei null und jede Ungenauigkeit ginge zu Lasten",
        "  des Kontos.",
        "",
        "## Was dieser Backtest nicht sagt",
        "",
        "Er sagt, wie oft die Situation gut ausgeht — **nicht, ob sich die",
        "Wette lohnt.** Das entscheidet sich allein daran, welche Quote im",
        "Moment des Gegentors tatsächlich angeboten wird. Der Buchmacher",
        "sieht dasselbe Tor und rechnet es sofort ein.",
        "",
        "Ebenfalls nicht enthalten: Wetten, die gar nicht zustande kommen,",
        "weil die Partie nicht live angeboten wird oder der Markt im Moment",
        "des Tores geschlossen ist.",
        "",
    ]
    return "\n".join(lines)


def main():
    faelle, gruende = sammle_faelle()
    if not faelle:
        warn("Keine Faelle — nichts geschrieben.")
        common.error_summary()
        return 1

    matches = common.read_csv(os.path.join(common.DATA_DIR, "matches_all.csv"))
    umfang = {
        "spiele": len(matches),
        "ligen": sorted({m["league"] for m in matches}),
        "saisons": sorted({m["season_name"] for m in matches}),
        "faelle": len(faelle),
    }

    gesamt = [kennzahlen("alle Fälle", faelle)]
    nach_team = sorted(gruppiere(faelle, "team"), key=lambda r: -r["n"])
    markiert = gruppiere(faelle, "markiert", ["ja", "nein"])
    for r in markiert:
        r["gruppe"] = ("die 12 markierten Clubs" if r["gruppe"] == "ja"
                       else "alle anderen Mannschaften")
    nach_block = gruppiere(faelle, "minute_block", BLOCK_ORDER)
    nach_ort = gruppiere(faelle, "ort", ["heim", "auswaerts"])
    nach_staerke = gruppiere(faelle, "staerke", common.STRENGTH_ORDER)

    ergebnis = {
        "erzeugt": datetime.now().isoformat(timespec="seconds"),
        "quelle": "ESPN-Cache in data/cache, Endergebnisse aus data/matches_all.csv",
        "definition": {
            "fall": "erstes Tor des Spiels vor Minute %d, erzielt vom Gegner" % VOR_MINUTE,
            "treffer": "die betroffene Mannschaft gewinnt am Ende",
            "fehlschlag": "Unentschieden oder Niederlage",
            "mindestquote": "1 / Trefferquote * %s" % MARGE,
            "nur_ligaspiele": True,
        },
        "umfang": umfang,
        "ausgeschlossen": gruende,
        "gruppen": {
            "gesamt": gesamt,
            "team": nach_team,
            "markierte_clubs": markiert,
            "minutenblock": nach_block,
            "ort": nach_ort,
            "staerke": nach_staerke,
        },
    }

    common.write_text(os.path.join(common.DATA_DIR, "35er-backtest.json"),
                      json.dumps(ergebnis, indent=1, ensure_ascii=False))
    common.write_csv(os.path.join(common.DATA_DIR, "35er-faelle.csv"),
                     faelle, FALL_FELDER)

    gruppen = [
        ("Die markierten Clubs gegen alle anderen",
         "Die Frage, auf die es für dein Portal ankommt.\n\n"
         "> **Es sind 12 der 13 Clubs, nicht 13.** Die Frauenmannschaft des "
         "FC Bayern München spielt in der Frauen-Bundesliga, und die deckt "
         "weder football-data.co.uk noch ESPN ab (siehe README). Sie kommt "
         "in diesen Daten überhaupt nicht vor — die Zahlen unten gelten "
         "ausschließlich für die zwölf Männermannschaften.",
         markiert, "Gruppe"),
        ("Nach Minute des Gegentors",
         "Je früher das Tor, desto mehr Zeit bleibt zum Ausgleichen — "
         "aber desto länger kann auch noch mehr schiefgehen.",
         nach_block, "Minutenblock"),
        ("Heim oder auswärts", "", nach_ort, "Ort"),
        ("Nach Stärke vor dem Anpfiff",
         "Faire Siegquote der betroffenen Mannschaft, nachdem die "
         "Buchmacher-Marge herausgerechnet wurde. Kleine Quote = großer Favorit.",
         nach_staerke, "Stärke"),
        ("Nach Mannschaft",
         "Alle %d Mannschaften, nach Fallzahl sortiert. Die vollständige "
         "Liste steht auch in `data/35er-backtest.json`." % len(nach_team),
         nach_team, "Mannschaft"),
    ]
    common.write_text(os.path.join(common.RESULTS_DIR, "35er.md"),
                      baue_markdown(faelle, gesamt, gruppen, umfang))

    log("Geschrieben: data/35er-backtest.json, data/35er-faelle.csv, results/35er.md")
    common.error_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
