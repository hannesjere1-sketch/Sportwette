#!/usr/bin/env python3
"""Phase 3 — Basisraten: Wie oft gewinnt ein Team in Unterzahl trotzdem?

Verbindet die Rote-Karte-Ereignisse (Phase 2) mit den Endergebnissen
(Phase 1) und rechnet fuer jede Gruppe aus, wie das Spiel ausgegangen ist.

Wichtig zur Staerke der Mannschaften: aus den Bet365-Schlussquoten wird
ZUERST die Buchmacher-Marge herausgerechnet (1/Quote je Ausgang
aufsummieren, dann jeden Wert durch die Summe teilen). Sonst haetten wir
statt einer Wahrscheinlichkeit nur die Preisliste des Buchmachers.

Ausgabe:
  data/basisraten.csv
  results/basisraten.md
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import log, warn, de

MIN_CASES = 30            # darunter: "zu wenig Daten"
THIN_NOTE = "zu wenig Daten"

CSV_FIELDS = ["dimension", "gruppe", "faelle", "siege", "unentschieden",
              "niederlagen", "siegquote", "ci_unten", "ci_oben", "hinweis"]


# --------------------------------------------------------------- Faelle -----

def build_cases():
    matches = {m["match_id"]: m for m in common.read_csv(
        os.path.join(common.DATA_DIR, "matches_with_reds.csv"))}
    events = common.read_csv(os.path.join(common.DATA_DIR,
                                          "red_card_events.csv"))
    if not matches:
        warn("matches_with_reds.csv fehlt — bitte 01_fetch_matches.py laufen lassen.")
        return []
    if not events:
        warn("red_card_events.csv fehlt oder ist leer — bitte "
             "02_fetch_events.py laufen lassen.")
        return []

    cases = []
    skipped = {"kein Spiel": 0, "Spielstand-Abweichung": 0,
               "nicht die erste Rote": 0, "Quoten fehlen": 0,
               "Minute unbrauchbar": 0}

    for ev in events:
        try:
            match = matches.get(ev["match_id"])
            if not match:
                skipped["kein Spiel"] += 1
                continue
            if ev.get("score_check") != "ok":
                # Nachgezaehlter Endstand passt nicht zum gemeldeten —
                # lieber verwerfen als falsch zaehlen.
                skipped["Spielstand-Abweichung"] += 1
                continue
            if str(ev.get("is_first_red")) != "1":
                # Nur die erste Rote des Spiels: sonst waere es 9 gegen 11
                # oder 10 gegen 10, ein ganz anderer Zustand.
                skipped["nicht die erste Rote"] += 1
                continue

            probs = common.fair_probs(match["b365h"], match["b365d"],
                                      match["b365a"])
            if not probs:
                skipped["Quoten fehlen"] += 1
                continue
            p_home, p_draw, p_away = probs

            side = ev["red_side"]
            if side == "home":
                team_prob, venue = p_home, "heim"
                won = match["ftr"] == "H"
            else:
                team_prob, venue = p_away, "auswaerts"
                won = match["ftr"] == "A"
            drew = match["ftr"] == "D"

            minute = int(ev["red_minute"])
            bucket = common.minute_bucket(minute)
            if bucket is None:
                skipped["Minute unbrauchbar"] += 1
                continue

            fair_odds = 1.0 / team_prob if team_prob > 0 else None
            cases.append({
                "match_id": ev["match_id"],
                "team": ev["red_team"],
                "gegner": ev["opponent_team"],
                "minute": minute,
                "minute_gruppe": bucket,
                "spielstand": common.score_state(
                    int(ev["goals_for_at_red"]), int(ev["goals_against_at_red"])),
                "ort": venue,
                "faire_quote": fair_odds,
                "staerke": common.strength_bucket(fair_odds),
                "ergebnis": "sieg" if won else ("unentschieden" if drew else "niederlage"),
            })
        except Exception as exc:
            warn("Fall %s uebersprungen: %s" % (ev.get("match_id"), exc))

    for reason, count in skipped.items():
        if count:
            log("Aussortiert (%s): %d" % (reason, count))
    log("Verwertbare Faelle: %d" % len(cases))
    return cases


# --------------------------------------------------------------- Gruppen ----

def summarise(label, dimension, cases):
    n = len(cases)
    wins = sum(1 for c in cases if c["ergebnis"] == "sieg")
    draws = sum(1 for c in cases if c["ergebnis"] == "unentschieden")
    losses = n - wins - draws
    rate = wins / n if n else 0.0
    lo, hi = common.wilson(wins, n)
    return {
        "dimension": dimension, "gruppe": label, "faelle": n,
        "siege": wins, "unentschieden": draws, "niederlagen": losses,
        "siegquote": round(100.0 * rate, 1),
        "ci_unten": round(100.0 * lo, 1), "ci_oben": round(100.0 * hi, 1),
        "hinweis": THIN_NOTE if n < MIN_CASES else "",
    }


def group_by(cases, key, order, dimension):
    rows = []
    buckets = {}
    for c in cases:
        buckets.setdefault(c[key], []).append(c)
    labels = [l for l in order if l in buckets]
    labels += sorted(l for l in buckets if l not in order)
    for label in labels:
        rows.append(summarise(label, dimension, buckets[label]))
    return rows


# ------------------------------------------------------------- Ausgabe ------

def md_table(rows):
    out = ["| Gruppe | Fälle | Sieg | Unent. | Nied. | Siegquote | 95 %-Intervall | Hinweis |",
           "| --- | ---: | ---: | ---: | ---: | ---: | :---: | --- |"]
    for r in rows:
        interval = "%s – %s %%" % (de(r["ci_unten"]), de(r["ci_oben"]))
        out.append("| %s | %d | %d | %d | %d | %s %% | %s | %s |" % (
            r["gruppe"], r["faelle"], r["siege"], r["unentschieden"],
            r["niederlagen"], de(r["siegquote"]), interval,
            r["hinweis"] or "—"))
    return "\n".join(out)


def build_markdown(cases, sections, combo_rows):
    total = summarise("alle Fälle", "gesamt", cases)
    lines = [
        "# Basisraten: Sieg trotz Roter Karte",
        "",
        "Ausgewertet wird immer aus Sicht der Mannschaft, die die Rote Karte",
        "bekommen hat — also die Mannschaft, die ab dieser Minute nur noch",
        "zehn Spieler auf dem Platz hat. Gezählt wird ausschließlich das",
        "Endergebnis (1X2), keine Quotenbewegung.",
        "",
        "**Was in der Auswertung landet:** nur die *erste* Rote Karte eines",
        "Spiels (bei der zweiten wäre es 9 gegen 11 oder 10 gegen 10 — ein",
        "anderer Zustand), und nur Spiele, bei denen der aus den Ereignissen",
        "nachgezählte Endstand zum gemeldeten Endstand passt.",
        "",
        "**Stärke** ist die faire Siegquote der betroffenen Mannschaft *vor*",
        "dem Anpfiff: aus den Bet365-Schlussquoten, nachdem die",
        "Buchmacher-Marge herausgerechnet wurde.",
        "",
        "**Das 95-%-Intervall** (Wilson) sagt, wie sicher die Quote ist. Ein",
        "breites Intervall heißt: zu wenig Fälle, um daraus etwas zu schließen.",
        "Gruppen mit weniger als %d Fällen sind mit „%s\" markiert — die "
        "sind als Zahl nicht belastbar." % (MIN_CASES, THIN_NOTE),
        "",
        "---",
        "",
        "## Gesamt",
        "",
        md_table([total]),
        "",
    ]
    for title, note, rows in sections:
        lines += ["## %s" % title, ""]
        if note:
            lines += [note, ""]
        lines += [md_table(rows), ""]
    if combo_rows:
        lines += [
            "## Minute × Spielstand kombiniert",
            "",
            "Die eigentlich interessante Kreuztabelle. Genau hier wird die",
            "Datenmenge schnell dünn — bitte auf die Hinweis-Spalte achten.",
            "",
            md_table(combo_rows),
            "",
        ]
    thin = sum(1 for r in [total] + [x for _, _, rr in sections for x in rr]
               if r["hinweis"])
    lines += [
        "---",
        "",
        "## Einordnung",
        "",
        "- Auswertbare Fälle insgesamt: **%d**" % len(cases),
        "- Gruppen mit zu wenig Daten: **%d**" % thin,
        "- Nächster Schritt für belastbare Zahlen: in `01_fetch_matches.py`",
        "  weitere Saisons und Ligen freischalten (Konstanten `SEASONS` und",
        "  `LEAGUES` ganz oben) und Phase 2 erneut laufen lassen.",
        "",
    ]
    return "\n".join(lines)


def main():
    cases = build_cases()
    if not cases:
        warn("Keine auswertbaren Fälle — nichts geschrieben.")
        common.error_summary()
        return 1

    sections = [
        ("Nach Minute der Roten Karte",
         "Je früher die Karte, desto länger muss die Mannschaft in Unterzahl "
         "durchhalten.",
         group_by(cases, "minute_gruppe", common.MINUTE_ORDER, "minute")),
        ("Nach Spielstand in dem Moment",
         "Aus Sicht der Mannschaft mit der Roten Karte.",
         group_by(cases, "spielstand", common.SCORE_ORDER, "spielstand")),
        ("Nach Heim oder Auswärts", "",
         group_by(cases, "ort", common.VENUE_ORDER, "ort")),
        ("Nach Stärke vor dem Anpfiff",
         "Faire Siegquote ohne Buchmacher-Marge. Kleine Quote = großer Favorit.",
         group_by(cases, "staerke", common.STRENGTH_ORDER, "staerke")),
    ]

    combo = {}
    for c in cases:
        combo.setdefault("%s / %s" % (c["minute_gruppe"], c["spielstand"]), []).append(c)
    combo_rows = [summarise(k, "minute_x_spielstand", v)
                  for k, v in sorted(combo.items())]

    all_rows = [summarise("alle Fälle", "gesamt", cases)]
    for _, _, rows in sections:
        all_rows.extend(rows)
    all_rows.extend(combo_rows)

    common.write_csv(os.path.join(common.DATA_DIR, "basisraten.csv"),
                     all_rows, CSV_FIELDS)
    common.write_text(os.path.join(common.RESULTS_DIR, "basisraten.md"),
                      build_markdown(cases, sections, combo_rows))

    # Einzelfaelle mitschreiben — praktisch zum Nachpruefen von Hand.
    common.write_csv(
        os.path.join(common.DATA_DIR, "faelle.csv"), cases,
        ["match_id", "team", "gegner", "minute", "minute_gruppe",
         "spielstand", "ort", "faire_quote", "staerke", "ergebnis"])

    log("Geschrieben: data/basisraten.csv, data/faelle.csv, results/basisraten.md")
    common.error_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
