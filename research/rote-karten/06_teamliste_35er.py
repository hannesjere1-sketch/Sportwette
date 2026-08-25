#!/usr/bin/env python3
"""Teamliste zum 35er-Backtest: je Liga, sortiert nach Trefferquote.

Liest nur data/35er-faelle.csv (aus Phase 5) und braucht Sekunden.

Je Mannschaft:
  * Faelle gesamt  = Spiele mit 0:1 Rueckstand durch das erste Tor
    des Spiels vor Minute 35
  * Trefferquote   = Anteil davon, den die Mannschaft noch gewinnt
  * dasselbe getrennt fuer Heim- und Auswaertsspiele

Ausgabe:
  data/35er-teams.csv      alle Zahlen zum Weiterrechnen
  results/35er-teams.md    lesbare Liste, nach Liga gegliedert
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import log, warn, de

MIN_FAELLE = 30
MARGE = 1.05

LIGA_NAMEN = {
    "E0": "Premier League (England)",
    "SP1": "La Liga (Spanien)",
    "D1": "Bundesliga (Deutschland)",
    "I1": "Serie A (Italien)",
    "F1": "Ligue 1 (Frankreich)",
}
LIGA_ORDER = ["E0", "SP1", "D1", "I1", "F1"]

FELDER = [
    "liga", "liga_name", "team", "markiert",
    "faelle", "treffer", "trefferquote", "ci_unten", "ci_oben", "mindestquote",
    "heim_faelle", "heim_treffer", "heim_quote",
    "auswaerts_faelle", "auswaerts_treffer", "auswaerts_quote",
    "belastbar",
]


def anzeigename():
    """Kanonischer Name -> die Schreibweise aus den Rohdaten.

    Intern heisst der FC Bayern "bayern munich", weil die Normalisierung
    alles kleinschreibt, was nicht in der Alias-Tabelle steht. Fuer eine
    Liste zum Anschauen nehmen wir die Schreibweise, die
    football-data.co.uk verwendet.
    """
    zaehler = defaultdict(lambda: defaultdict(int))
    for m in common.read_csv(os.path.join(common.DATA_DIR, "matches_all.csv")):
        zaehler[m["home_team"]][m["home_team_raw"]] += 1
        zaehler[m["away_team"]][m["away_team_raw"]] += 1
    return {kanon: max(roh.items(), key=lambda x: x[1])[0]
            for kanon, roh in zaehler.items()}


def quote(treffer, n):
    return 100.0 * treffer / n if n else 0.0


def main():
    faelle = common.read_csv(os.path.join(common.DATA_DIR, "35er-faelle.csv"))
    if not faelle:
        warn("data/35er-faelle.csv fehlt — bitte 05_backtest_35er.py laufen lassen.")
        return 1

    namen = anzeigename()

    # Eine Mannschaft kann in mehreren Ligen auftauchen (Wechsel gibt es
    # nicht, aber sicher ist sicher) — deshalb Liga UND Team als Schluessel.
    eimer = defaultdict(list)
    for f in faelle:
        eimer[(f["league"], f["team"])].append(f)

    zeilen = []
    for (liga, team), liste in eimer.items():
        heim = [x for x in liste if x["ort"] == "heim"]
        aus = [x for x in liste if x["ort"] == "auswaerts"]
        n = len(liste)
        treffer = sum(int(x["treffer"]) for x in liste)
        q = quote(treffer, n)
        lo, hi = common.wilson(treffer, n)
        h_tr = sum(int(x["treffer"]) for x in heim)
        a_tr = sum(int(x["treffer"]) for x in aus)
        zeilen.append({
            "liga": liga,
            "liga_name": LIGA_NAMEN.get(liga, liga),
            "team": namen.get(team, team),
            "markiert": liste[0]["markiert"],
            "faelle": n,
            "treffer": treffer,
            "trefferquote": round(q, 1),
            "ci_unten": round(100.0 * lo, 1),
            "ci_oben": round(100.0 * hi, 1),
            "mindestquote": round(MARGE / (q / 100.0), 2) if q > 0 else None,
            "heim_faelle": len(heim),
            "heim_treffer": h_tr,
            "heim_quote": round(quote(h_tr, len(heim)), 1),
            "auswaerts_faelle": len(aus),
            "auswaerts_treffer": a_tr,
            "auswaerts_quote": round(quote(a_tr, len(aus)), 1),
            "belastbar": "ja" if n >= MIN_FAELLE else "nein",
        })

    # Nach Liga gegliedert, innerhalb der Liga nach Trefferquote fallend.
    zeilen.sort(key=lambda r: (LIGA_ORDER.index(r["liga"]) if r["liga"] in LIGA_ORDER else 99,
                               -r["trefferquote"], -r["faelle"]))
    common.write_csv(os.path.join(common.DATA_DIR, "35er-teams.csv"), zeilen, FELDER)

    # ---- Markdown ----
    aus = [
        "# 35er-Strategie: alle Mannschaften",
        "",
        "Je Mannschaft die Spiele, in denen sie das **erste Tor des Spiels",
        "vor Minute 35 kassiert** hat (Rückstand 0:1), und wie oft sie",
        "danach noch gewonnen hat. Nach Liga gegliedert, innerhalb der Liga",
        "nach Trefferquote sortiert.",
        "",
        "**Mindestquote** = `1 ÷ Trefferquote × 1,05` — darunter lohnt die",
        "Wette langfristig nicht. **★** markiert die Clubs aus deinem Portal.",
        "",
        "Zeilen mit weniger als %d Fällen sind grau hinterlegt gemeint:" % MIN_FAELLE,
        "die Trefferquote ist dort Zufall, keine Eigenschaft der Mannschaft.",
        "",
    ]
    gesamt_n = sum(r["faelle"] for r in zeilen)
    gesamt_t = sum(r["treffer"] for r in zeilen)
    aus += ["Insgesamt **%d Fälle**, davon **%d Treffer** (%s %%).\n"
            % (gesamt_n, gesamt_t, de(quote(gesamt_t, gesamt_n))), "---", ""]

    for liga in LIGA_ORDER:
        teil = [r for r in zeilen if r["liga"] == liga]
        if not teil:
            continue
        n = sum(r["faelle"] for r in teil)
        t = sum(r["treffer"] for r in teil)
        aus += [
            "## %s" % LIGA_NAMEN[liga],
            "",
            "%d Mannschaften, %d Fälle, Trefferquote der Liga: **%s %%**"
            % (len(teil), n, de(quote(t, n))),
            "",
            "| # | Mannschaft | Fälle | Treffer | Trefferquote | 95 %-Intervall | Mindest-quote | Heim (Fälle) | Heim-Quote | Ausw. (Fälle) | Ausw.-Quote |",
            "| ---: | --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for i, r in enumerate(teil, start=1):
            stern = " ★" if r["markiert"] == "ja" else ""
            dünn = "" if r["belastbar"] == "ja" else " ⚠"
            mq = "—" if r["mindestquote"] is None else de(r["mindestquote"], 2)
            aus.append("| %d | %s%s%s | %d | %d | **%s %%** | %s – %s %% | %s | %d | %s %% | %d | %s %% |" % (
                i, r["team"], stern, dünn, r["faelle"], r["treffer"],
                de(r["trefferquote"]), de(r["ci_unten"]), de(r["ci_oben"]), mq,
                r["heim_faelle"], de(r["heim_quote"]),
                r["auswaerts_faelle"], de(r["auswaerts_quote"])))
        aus += ["", "⚠ = weniger als %d Fälle, Quote nicht belastbar." % MIN_FAELLE, ""]

    aus += [
        "---",
        "",
        "## Warum die Spitzenwerte trügen",
        "",
        "Die Mannschaften ganz oben in jeder Liga sind fast durchweg die",
        "Titelanwärter — sie geraten selten in Rückstand, und wenn doch,",
        "drehen sie das Spiel oft. Genau deshalb ist ihre Quote hoch **und**",
        "ihre Fallzahl niedrig. Beides zusammen heißt: das 95-%-Intervall",
        "ist breit, und der wahre Wert liegt womöglich deutlich darunter.",
        "",
        "Verlässlicher als die Einzelwerte ist die Stärkeklasse in",
        "`results/35er.md`: Favoriten mit einer fairen Quote unter 1,50",
        "kommen auf 53,4 % über 412 Fälle — das ist dieselbe Aussage, nur",
        "auf einer Fallzahl, die trägt.",
        "",
    ]
    common.write_text(os.path.join(common.RESULTS_DIR, "35er-teams.md"), "\n".join(aus))
    log("Geschrieben: data/35er-teams.csv, results/35er-teams.md (%d Mannschaften)"
        % len(zeilen))
    common.error_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
