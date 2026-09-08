#!/usr/bin/env python3
"""35er-Faelle nach Staerke des GEGNERS aufschluesseln — nur Heimspiele.

Aufbauend auf 05/06. Fuer jeden Fall wird die Abschlussposition des
Gegners in der jeweiligen Saison bestimmt:

    stark   = Endplatz 1 bis 6
    schwach = Endplatz 7 oder schlechter

Die Abschlusstabellen liegen nicht vor und werden aus den
Ergebnisdaten gerechnet: 3 Punkte fuer einen Sieg, 1 fuer ein
Unentschieden, Tordifferenz als erstes Trennkriterium, danach die
erzielten Tore.

  Achtung: die echten Ligen trennen bei Punktgleichheit teils anders
  (Spanien und Italien zuerst ueber den direkten Vergleich). Bei
  punktgleichen Mannschaften an der Grenze zwischen Platz 6 und 7 kann
  die hier gerechnete Tabelle deshalb von der offiziellen abweichen.
  Wie oft das ueberhaupt vorkommt, weist die Zusammenfassung aus.

  Ligue 1 2019/20 wurde im Maerz 2020 abgebrochen. Dort haben die
  Mannschaften unterschiedlich viele Spiele, weshalb nach Punkten JE
  SPIEL sortiert wird — so hat es auch der Verband entschieden.

Ausgewertet werden ausschliesslich HEIMSPIELE der betroffenen
Mannschaft. Auswaertsspiele bleiben komplett draussen.

Ausgabe:
  data/35er-gegnerstaerke.csv
  results/35er-gegnerstaerke.md
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import log, warn, de

STARK_BIS = 6             # Platz 1 bis 6 gilt als starker Gegner
DUENN = 10                # darunter mit Warnzeichen versehen
MARGE = 1.053 * 1.15      # Buchmacherabschlag mal Sicherheitszuschlag

MINUTE_ORDER = ["1-10", "11-20", "21-34"]

LIGA_NAMEN = {
    "E0": "Premier League", "SP1": "La Liga", "D1": "Bundesliga",
    "I1": "Serie A", "F1": "Ligue 1",
}
LIGA_ORDER = ["E0", "SP1", "D1", "I1", "F1"]

FELDER = [
    "ebene", "liga", "liga_name", "team", "markiert", "gegnerstaerke",
    "minutenfenster", "faelle", "treffer", "trefferquote",
    "ci_unten", "ci_oben", "mindestquote", "mindestquote_konservativ",
    "belastbar",
]


# ------------------------------------------------------- Abschlusstabellen ---

def tabellen(matches):
    """Endplatz je (Liga, Saison, Team). Gibt auch die Grenzfaelle zurueck."""
    roh = defaultdict(lambda: defaultdict(
        lambda: {"pkt": 0, "sp": 0, "ts": 0, "tk": 0}))
    for m in matches:
        try:
            key = (m["league"], m["season"])
            h, a = m["home_team"], m["away_team"]
            th, ta = int(m["fthg"]), int(m["ftag"])
        except (KeyError, TypeError, ValueError):
            continue
        for team, eigen, fremd in ((h, th, ta), (a, ta, th)):
            e = roh[key][team]
            e["sp"] += 1
            e["ts"] += eigen
            e["tk"] += fremd
            e["pkt"] += 3 if eigen > fremd else (1 if eigen == fremd else 0)

    plaetze = {}
    grenzfaelle = []
    for key, teams in roh.items():
        gespielt = {e["sp"] for e in teams.values()}
        # Abgebrochene Saison: unterschiedlich viele Spiele -> Punkte je
        # Spiel, sonst waere die Tabelle schlicht falsch.
        pro_spiel = len(gespielt) > 1
        def schluessel(item):
            name, e = item
            pkt = e["pkt"] / e["sp"] if pro_spiel and e["sp"] else e["pkt"]
            return (-pkt, -(e["ts"] - e["tk"]), -e["ts"], name)
        rang = sorted(teams.items(), key=schluessel)
        if pro_spiel:
            log("  %s-%s: abgebrochene Saison (%s Spiele je Team) — "
                "sortiert nach Punkten je Spiel"
                % (key[0], key[1], "/".join(str(x) for x in sorted(gespielt))))
        for platz, (name, e) in enumerate(rang, start=1):
            plaetze[(key[0], key[1], name)] = platz
        # Entscheidet an der Grenze 6/7 die Tordifferenz statt der Punkte?
        if len(rang) > STARK_BIS:
            sechs, sieben = rang[STARK_BIS - 1][1], rang[STARK_BIS][1]
            p6 = sechs["pkt"] / sechs["sp"] if pro_spiel else sechs["pkt"]
            p7 = sieben["pkt"] / sieben["sp"] if pro_spiel else sieben["pkt"]
            if p6 == p7:
                grenzfaelle.append("%s %s: %s und %s punktgleich"
                                   % (key[0], key[1], rang[STARK_BIS - 1][0],
                                      rang[STARK_BIS][0]))
    return plaetze, grenzfaelle


# -------------------------------------------------------------- Kennzahlen ---

def kennzahlen(ebene, liga, team, markiert, staerke, fenster, faelle):
    n = len(faelle)
    treffer = sum(int(f["treffer"]) for f in faelle)
    q = treffer / n if n else 0.0
    lo, hi = common.wilson(treffer, n)
    return {
        "ebene": ebene,
        "liga": liga,
        "liga_name": LIGA_NAMEN.get(liga, liga),
        "team": team,
        "markiert": markiert,
        "gegnerstaerke": staerke,
        "minutenfenster": fenster,
        "faelle": n,
        "treffer": treffer,
        "trefferquote": round(100.0 * q, 1),
        "ci_unten": round(100.0 * lo, 1),
        "ci_oben": round(100.0 * hi, 1),
        "mindestquote": round(MARGE / q, 2) if q > 0 else None,
        # Mit der Untergrenze des Intervalls statt der Punktschaetzung:
        # was die Quote hergeben muss, wenn die wahre Trefferquote am
        # unteren Rand dessen liegt, was die Daten noch zulassen.
        "mindestquote_konservativ": round(MARGE / lo, 2) if lo > 0 else None,
        "belastbar": "ja" if n >= DUENN else "nein",
    }


def anzeigename():
    zaehler = defaultdict(lambda: defaultdict(int))
    for m in common.read_csv(os.path.join(common.DATA_DIR, "matches_all.csv")):
        zaehler[m["home_team"]][m["home_team_raw"]] += 1
        zaehler[m["away_team"]][m["away_team_raw"]] += 1
    return {k: max(v.items(), key=lambda x: x[1])[0] for k, v in zaehler.items()}


# ----------------------------------------------------------------- Ausgabe ---

def md_tabelle(zeilen, erste="Gruppe", mit_liga=False):
    kopf = "| %s |%s Fälle | Treffer | Trefferquote | 95 %%-Intervall | Mindestquote | konservativ |" % (
        erste, " Liga |" if mit_liga else "")
    trenn = "| --- |%s ---: | ---: | ---: | :---: | ---: | ---: |" % (" --- |" if mit_liga else "")
    out = [kopf, trenn]
    for r in zeilen:
        mq = "—" if r["mindestquote"] is None else de(r["mindestquote"], 2)
        mk = "—" if r["mindestquote_konservativ"] is None else de(r["mindestquote_konservativ"], 2)
        warnz = "" if r["belastbar"] == "ja" else " ⚠"
        stern = " ★" if r["markiert"] == "ja" else ""
        label = r["team"] if r["team"] else r["gegnerstaerke"]
        out.append("| %s%s%s |%s %d | %d | **%s %%** | %s – %s %% | %s | %s |" % (
            label, stern, warnz,
            (" %s |" % r["liga_name"]) if mit_liga else "",
            r["faelle"], r["treffer"], de(r["trefferquote"]),
            de(r["ci_unten"]), de(r["ci_oben"]), mq, mk))
    return "\n".join(out)


def main():
    faelle = common.read_csv(os.path.join(common.DATA_DIR, "35er-faelle.csv"))
    matches = common.read_csv(os.path.join(common.DATA_DIR, "matches_all.csv"))
    if not faelle or not matches:
        warn("data/35er-faelle.csv oder matches_all.csv fehlt.")
        return 1

    log("Abschlusstabellen rechnen …")
    plaetze, grenzfaelle = tabellen(matches)
    log("Tabellen fuer %d Mannschafts-Saisons" % len(plaetze))
    if grenzfaelle:
        log("An der Grenze Platz 6/7 punktgleich in %d von 45 Saisons:" % len(grenzfaelle))
        for g in grenzfaelle:
            log("    " + g)

    namen = anzeigename()

    # Nur Heimspiele, Gegner einordnen.
    heim = []
    ohne_platz = 0
    for f in faelle:
        if f["ort"] != "heim":
            continue
        platz = plaetze.get((f["league"], f["season"], f["gegner"]))
        if platz is None:
            ohne_platz += 1
            continue
        f = dict(f)
        f["gegner_platz"] = platz
        f["gegnerstaerke"] = "stark" if platz <= STARK_BIS else "schwach"
        heim.append(f)
    log("Heimspiele mit 0:1-Rueckstand: %d (ohne Tabellenplatz: %d)"
        % (len(heim), ohne_platz))

    zeilen = []

    # 1) Aggregat ueber alle Teams
    for staerke in ("stark", "schwach"):
        teil = [f for f in heim if f["gegnerstaerke"] == staerke]
        zeilen.append(kennzahlen("gesamt", "", "", "", staerke, "alle", teil))

    # 2) Aggregat nach Minutenfenster
    for staerke in ("stark", "schwach"):
        for fenster in MINUTE_ORDER:
            teil = [f for f in heim
                    if f["gegnerstaerke"] == staerke and f["minute_block"] == fenster]
            zeilen.append(kennzahlen("gesamt_minute", "", "", "", staerke, fenster, teil))

    # 3) Je Mannschaft zwei Zeilen
    nach_team = defaultdict(list)
    for f in heim:
        nach_team[(f["league"], f["team"])].append(f)
    for (liga, team), liste in nach_team.items():
        for staerke in ("stark", "schwach"):
            teil = [f for f in liste if f["gegnerstaerke"] == staerke]
            zeilen.append(kennzahlen("team", liga, namen.get(team, team),
                                     liste[0]["markiert"], staerke, "alle", teil))

    common.write_csv(os.path.join(common.DATA_DIR, "35er-gegnerstaerke.csv"),
                     zeilen, FELDER)

    # ---------------------------------------------------------- Markdown ----
    ges = {r["gegnerstaerke"]: r for r in zeilen if r["ebene"] == "gesamt"}
    stark, schwach = ges["stark"], ges["schwach"]

    md = [
        "# 35er-Strategie nach Gegnerstärke — nur Heimspiele",
        "",
        "Jeder Fall ist ein **Heimspiel**, in dem die Mannschaft das erste",
        "Tor des Spiels vor Minute 35 kassiert hat. Auswärtsspiele sind",
        "vollständig ausgeklammert.",
        "",
        "**stark** = der Gegner beendete die Saison auf Platz 1 bis %d, "
        "**schwach** = Platz %d oder schlechter." % (STARK_BIS, STARK_BIS + 1),
        "",
        "Die Abschlusstabellen sind aus den Ergebnissen gerechnet (3/1/0,",
        "Tordifferenz als erstes Trennkriterium, dann erzielte Tore).",
        "",
        "**Mindestquote** = `1 ÷ Trefferquote × 1,053 × 1,15`.",
        "**Konservativ** rechnet mit der Untergrenze des",
        "95-%-Konfidenzintervalls statt mit der Trefferquote selbst — also",
        "damit, dass die wahre Quote am unteren Rand dessen liegt, was die",
        "Daten noch zulassen.",
        "",
        "⚠ = weniger als %d Fälle." % DUENN,
        "",
        "---",
        "",
        "## Die Kernzahl",
        "",
        md_tabelle([stark, schwach], "Gegner"),
        "",
        "Zu Hause gegen einen **starken** Gegner in Rückstand zu geraten,",
        "endet in **%s %%** der Fälle noch mit einem Sieg — gegen einen"
        % de(stark["trefferquote"]),
        "schwachen Gegner in **%s %%**." % de(schwach["trefferquote"]),
        "",
        "Für die Wette heißt das: gegen starke Gegner braucht es eine Quote",
        "von mindestens **%s**, gegen schwache **%s**."
        % (de(stark["mindestquote"], 2), de(schwach["mindestquote"], 2)),
        "",
        "---",
        "",
        "## Nach Minute des Gegentors",
        "",
        "Verhalten sich frühe Rückstände anders als späte?",
        "",
    ]
    for staerke in ("stark", "schwach"):
        teil = [r for r in zeilen
                if r["ebene"] == "gesamt_minute" and r["gegnerstaerke"] == staerke]
        teil.sort(key=lambda r: MINUTE_ORDER.index(r["minutenfenster"]))
        for r in teil:
            r["team"] = "Minute " + r["minutenfenster"]
        md += ["### Heim gegen %s" % staerke, "",
               md_tabelle(teil, "Minutenfenster"), ""]

    md += ["---", "", "## Je Mannschaft", ""]
    for staerke, titel in (("stark", "Heim gegen starke Gegner (Platz 1–%d)" % STARK_BIS),
                           ("schwach", "Heim gegen schwache Gegner (Platz %d+)" % (STARK_BIS + 1))):
        teil = [r for r in zeilen if r["ebene"] == "team" and r["gegnerstaerke"] == staerke]
        teil.sort(key=lambda r: (-r["trefferquote"], -r["faelle"], r["team"]))
        md += ["### %s" % titel, "",
               "%d Mannschaften, nach Trefferquote absteigend." % len(teil), "",
               md_tabelle(teil, "Mannschaft", mit_liga=True), ""]

    md += [
        "---",
        "",
        "## Einschränkungen",
        "",
        "- Die Abschlusstabellen sind gerechnet, nicht abgeschrieben. Spanien",
        "  und Italien trennen punktgleiche Mannschaften zuerst über den",
        "  direkten Vergleich, hier entscheidet die Tordifferenz. An der",
        "  Grenze zwischen Platz 6 und 7 waren in **%d von 45 Saisons**"
        % len(grenzfaelle),
        "  zwei Mannschaften punktgleich; nur dort kann die Einordnung von",
        "  der offiziellen Tabelle abweichen.",
        "- Der Endplatz ist **im Nachhinein** bekannt, im Moment der Wette",
        "  nicht. Wer die Zahlen live nutzen will, braucht einen Ersatz —",
        "  etwa den Tabellenstand am Spieltag oder die Buchmacherquote vor",
        "  dem Anpfiff.",
        "- Auch hier gilt: die Zahlen sagen, wie oft es gut ausgeht, nicht,",
        "  ob die angebotene Quote reicht.",
        "",
    ]
    common.write_text(os.path.join(common.RESULTS_DIR, "35er-gegnerstaerke.md"),
                      "\n".join(md))
    log("Geschrieben: data/35er-gegnerstaerke.csv, results/35er-gegnerstaerke.md")
    common.error_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
