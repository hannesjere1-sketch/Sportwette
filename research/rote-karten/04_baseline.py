#!/usr/bin/env python3
"""Phase 4 — Vergleichsgruppe: dieselben Zustaende, aber OHNE Rote Karte.

Ohne Vergleich sagt eine Zahl wie „22 % Siege" gar nichts. Eine Mannschaft,
die in Minute 20 mit 0:1 hinten liegt, gewinnt auch mit elf Mann selten.
Erst der Abstand zwischen beiden Raten zeigt, was die Rote Karte kostet.

Die Vergleichsgruppe entsteht aus allen Spielen OHNE Rote Karte: fuer jede
Mannschaft und jeden Minuten-Abschnitt wird der Spielstand an einer festen
Referenzminute abgelesen (Mitte des Abschnitts), dazu Staerke vor dem
Anpfiff und Endergebnis.

Verglichen wird dann PAARWEISE: zu jedem echten Rote-Karte-Fall wird die
Siegquote gesucht, die Mannschaften in genau demselben Zustand (Minute,
Spielstand, Staerke, Heim/Auswaerts) mit elf Mann erreicht haben. Sind
davon zu wenige da, wird schrittweise auf eine groebere Ebene
zurueckgefallen — welche das war, steht in der Tabelle.

Eingabe:
  data/matches_all.csv        (Phase 1)
  data/baseline_events.csv    (Phase 2 mit --set baseline)
  data/faelle.csv             (Phase 3)

Ausgabe:
  results/vergleich.md
  data/vergleich.csv
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import log, warn, de

MIN_CASES = 30        # darunter ist die Rote-Karte-Gruppe nicht belastbar
MIN_STRATUM = 20      # so viele Vergleichsspiele braucht eine Ebene
THIN_NOTE = "zu wenig Daten"

# Vergleichsebenen, von fein nach grob. Die erste Ebene mit genug
# Beobachtungen gewinnt.
LEVELS = [
    ("Minute+Stand+Stärke+Ort", ("minute_gruppe", "spielstand", "staerke", "ort")),
    ("Minute+Stand+Stärke", ("minute_gruppe", "spielstand", "staerke")),
    ("Minute+Stand", ("minute_gruppe", "spielstand")),
    ("Stand+Stärke", ("spielstand", "staerke")),
    ("Stand", ("spielstand",)),
    ("gesamt", ()),
]

CSV_FIELDS = ["dimension", "gruppe", "rot_faelle", "rot_siegquote",
              "rot_ci_unten", "rot_ci_oben", "erwartet_ohne_rot",
              "differenz_prozentpunkte", "vergleichsebene",
              "vergleichs_beobachtungen", "hinweis"]


# ------------------------------------------------------- Vergleichsgruppe ---

def build_baseline():
    matches = {m["match_id"]: m for m in common.read_csv(
        os.path.join(common.DATA_DIR, "matches_all.csv"))}
    events = common.read_csv(os.path.join(common.DATA_DIR,
                                          "baseline_events.csv"))
    if not matches:
        warn("matches_all.csv fehlt — bitte 01_fetch_matches.py laufen lassen.")
        return []

    goals = {}
    for row in events:
        try:
            goals.setdefault(row["match_id"], []).append((
                int(row["minute"]), int(row["extra"] or 0),
                int(row["home_score"]), int(row["away_score"])))
        except Exception as exc:
            warn("Baseline-Ereignis uebersprungen: %s" % exc)
    for key in goals:
        goals[key].sort()

    # Ein 0:0 hat keine Tore und taucht deshalb gar nicht in
    # baseline_events.csv auf. Solche Spiele holen wir ueber den
    # Fortschritt dazu, damit sie nicht stillschweigend fehlen.
    import json
    try:
        with open(os.path.join(common.DATA_DIR,
                               "events_progress_baseline.json"),
                  "r", encoding="utf-8") as fh:
            for match_id, entry in json.load(fh).items():
                if entry.get("status") == "ok":
                    goals.setdefault(match_id, [])
    except Exception:
        pass

    covered = [mid for mid in goals if mid in matches]
    if not covered:
        warn("baseline_events.csv fehlt oder passt zu keinem Spiel — bitte "
             "02_fetch_events.py --set baseline laufen lassen.")
        return []

    obs = []
    no_odds = 0
    for match_id in covered:
        match = matches[match_id]
        try:
            if int(match.get("hr") or 0) or int(match.get("ar") or 0):
                continue  # Sicherheitsnetz: hier darf keine Rote Karte rein
            probs = common.fair_probs(match["b365h"], match["b365d"],
                                      match["b365a"])
            if not probs:
                no_odds += 1
                continue
            p_home, _, p_away = probs
            timeline = goals[match_id]
            for side in ("home", "away"):
                if side == "home":
                    prob, venue, won = p_home, "heim", match["ftr"] == "H"
                else:
                    prob, venue, won = p_away, "auswaerts", match["ftr"] == "A"
                drew = match["ftr"] == "D"
                fair_odds = 1.0 / prob if prob > 0 else None
                for bucket, ref in common.BUCKET_REFERENCE_MINUTE.items():
                    h = a = 0
                    for minute, _extra, hs, as_ in timeline:
                        if minute > ref:
                            break
                        h, a = hs, as_
                    gf, ga = (h, a) if side == "home" else (a, h)
                    obs.append({
                        "match_id": match_id, "ort": venue,
                        "minute_gruppe": bucket,
                        "spielstand": common.score_state(gf, ga),
                        "staerke": common.strength_bucket(fair_odds),
                        "ergebnis": "sieg" if won else
                                    ("unentschieden" if drew else "niederlage"),
                    })
        except Exception as exc:
            warn("Spiel %s uebersprungen: %s" % (match_id, exc))

    if no_odds:
        log("Ohne Bet365-Quoten uebersprungen: %d Spiele" % no_odds)
    log("Vergleichsgruppe: %d Spiele ohne Rote Karte, %d Beobachtungen."
        % (len(covered) - no_odds, len(obs)))
    return obs


def build_index(obs):
    """Je Vergleichsebene: Zustand -> [Beobachtungen, Siege]."""
    index = {}
    for name, keys in LEVELS:
        table = {}
        for o in obs:
            key = tuple(o[k] for k in keys)
            entry = table.setdefault(key, [0, 0])
            entry[0] += 1
            if o["ergebnis"] == "sieg":
                entry[1] += 1
        index[name] = (keys, table)
    return index


def expected_rate(case, index):
    """Siegquote, die elf gegen elf in genau diesem Zustand erreichen."""
    for name, _keys in LEVELS:
        keys, table = index[name]
        try:
            key = tuple(case[k] for k in keys)
        except KeyError:
            continue
        n, wins = table.get(key, (0, 0))
        if n >= MIN_STRATUM:
            return 100.0 * wins / n, name, n
    return None, None, 0


# --------------------------------------------------------------- Vergleich --

def compare(red_cases, index, key, order, dimension):
    buckets = {}
    for c in red_cases:
        buckets.setdefault(c[key], []).append(c)

    labels = [l for l in order if l in buckets]
    labels += sorted(l for l in buckets if l not in order)

    rows = []
    for label in labels:
        cases = buckets[label]
        n = len(cases)
        wins = sum(1 for c in cases if c["ergebnis"] == "sieg")
        red_rate = 100.0 * wins / n if n else 0.0
        lo, hi = common.wilson(wins, n)

        rates, levels, sizes = [], [], []
        for c in cases:
            rate, level, size = expected_rate(c, index)
            if rate is None:
                continue
            rates.append(rate)
            levels.append(level)
            sizes.append(size)
        expected = sum(rates) / len(rates) if rates else None

        # Groebste benutzte Ebene nennen — das ist die ehrliche Angabe.
        coarsest = "—"
        if levels:
            order_of_levels = [name for name, _ in LEVELS]
            coarsest = max(levels, key=order_of_levels.index)

        note = []
        if n < MIN_CASES:
            note.append("%s (rot: %d)" % (THIN_NOTE, n))
        if expected is None:
            note.append("keine Vergleichsdaten")

        rows.append({
            "dimension": dimension, "gruppe": label,
            "rot_faelle": n, "rot_siegquote": round(red_rate, 1),
            "rot_ci_unten": round(100.0 * lo, 1),
            "rot_ci_oben": round(100.0 * hi, 1),
            "erwartet_ohne_rot": round(expected, 1) if expected is not None else "",
            "differenz_prozentpunkte": (round(red_rate - expected, 1)
                                        if expected is not None else ""),
            "vergleichsebene": coarsest,
            "vergleichs_beobachtungen": min(sizes) if sizes else 0,
            "hinweis": "; ".join(note),
        })
    return rows


def md_table(rows):
    out = ["| Gruppe | Fälle mit Rot | Sieg mit Rot | 95 %-Intervall | erwartet ohne Rot | Differenz | Vergleichsebene | Hinweis |",
           "| --- | ---: | ---: | :---: | ---: | ---: | --- | --- |"]
    for r in rows:
        diff = r["differenz_prozentpunkte"]
        diff_txt = "—" if diff == "" else "%s%s PP" % (
            "+" if diff > 0 else "", de(diff))
        exp_txt = "—" if r["erwartet_ohne_rot"] == "" else \
            "%s %%" % de(r["erwartet_ohne_rot"])
        out.append("| %s | %d | %s %% | %s – %s %% | %s | %s | %s | %s |" % (
            r["gruppe"], r["rot_faelle"], de(r["rot_siegquote"]),
            de(r["rot_ci_unten"]), de(r["rot_ci_oben"]),
            exp_txt, diff_txt, r["vergleichsebene"], r["hinweis"] or "—"))
    return "\n".join(out)


def main():
    red_cases = common.read_csv(os.path.join(common.DATA_DIR, "faelle.csv"))
    if not red_cases:
        warn("faelle.csv fehlt — bitte zuerst 03_analyse.py laufen lassen.")
        common.error_summary()
        return 1

    obs = build_baseline()
    if not obs:
        common.write_text(
            os.path.join(common.RESULTS_DIR, "vergleich.md"),
            "# Vergleich mit und ohne Rote Karte\n\n"
            "**Noch keine Vergleichsdaten vorhanden.**\n\n"
            "Bitte zuerst laufen lassen:\n\n"
            "```\npython3 02_fetch_events.py --set baseline\n"
            "python3 04_baseline.py\n```\n")
        warn("Ohne Vergleichsdaten geschrieben — siehe results/vergleich.md.")
        common.error_summary()
        return 1

    index = build_index(obs)

    sections = [
        ("Gesamt", compare([dict(c, alle="alle Fälle") for c in red_cases],
                           index, "alle", ["alle Fälle"], "gesamt")),
        ("Nach Minute der Roten Karte",
         compare(red_cases, index, "minute_gruppe", common.MINUTE_ORDER,
                 "minute")),
        ("Nach Spielstand in dem Moment",
         compare(red_cases, index, "spielstand", common.SCORE_ORDER,
                 "spielstand")),
        ("Nach Stärke vor dem Anpfiff",
         compare(red_cases, index, "staerke", common.STRENGTH_ORDER,
                 "staerke")),
        ("Nach Heim oder Auswärts",
         compare(red_cases, index, "ort", common.VENUE_ORDER, "ort")),
    ]

    all_rows = []
    for _, rows in sections:
        all_rows.extend(rows)

    ref = ", ".join("%s → Min. %d" % (k, v)
                    for k, v in common.BUCKET_REFERENCE_MINUTE.items())
    lines = [
        "# Was kostet die Rote Karte wirklich?",
        "",
        "Links die Mannschaft **mit** Roter Karte. Daneben, was Mannschaften",
        "**ohne** Rote Karte in genau derselben Lage erreicht haben. Die",
        "Spalte *Differenz* ist der Abstand in Prozentpunkten (PP) — das ist",
        "der eigentliche Preis der Karte.",
        "",
        "## Wie der Vergleich gebaut ist",
        "",
        "Zu jedem echten Rote-Karte-Fall wird ein Zwilling gesucht: dieselbe",
        "Minute, derselbe Spielstand, dieselbe Stärke, dasselbe Heimrecht —",
        "nur eben elf gegen elf. Der Zwilling kommt aus allen Spielen ohne",
        "Rote Karte, bei denen der Spielstand an einer festen Referenzminute",
        "je Abschnitt abgelesen wird (%s)." % ref,
        "",
        "Gibt es zu einem Zustand weniger als %d Vergleichsspiele, wird eine"
        % MIN_STRATUM,
        "Stufe gröber gesucht — erst ohne Heimrecht, dann ohne Stärke, dann",
        "ohne Minute. Die Spalte *Vergleichsebene* sagt, wie fein es am Ende",
        "wirklich war. Steht dort „gesamt\", ist der Vergleich praktisch",
        "wertlos.",
        "",
        "**Eine ehrliche Einschränkung:** jedes Vergleichsspiel taucht in",
        "mehreren Minuten-Abschnitten auf. Die Beobachtungen sind also nicht",
        "unabhängig voneinander. Deshalb steht auf der Vergleichsseite",
        "bewusst kein Konfidenzintervall — nur links, wo jeder Fall genau",
        "einmal zählt.",
        "",
        "---",
        "",
    ]
    for title, rows in sections:
        lines += ["## %s" % title, "", md_table(rows), ""]

    lines += [
        "---",
        "",
        "## Lesehilfe",
        "",
        "- **Differenz −18 PP** heißt: von 100 vergleichbaren Situationen",
        "  gewinnt die Mannschaft mit Roter Karte 18-mal seltener.",
        "- Eine Differenz nahe 0 heißt: in dieser Lage hätte es auch mit elf",
        "  Mann kaum anders ausgesehen — die Karte war nicht das Entscheidende.",
        "- Gruppen mit dem Hinweis „%s\" bitte nicht interpretieren." % THIN_NOTE,
        "- Für belastbare Zahlen in `01_fetch_matches.py` mehr Saisons und",
        "  Ligen freischalten und Phase 2 bis 4 erneut laufen lassen.",
        "",
    ]

    common.write_csv(os.path.join(common.DATA_DIR, "vergleich.csv"),
                     all_rows, CSV_FIELDS)
    common.write_text(os.path.join(common.RESULTS_DIR, "vergleich.md"),
                      "\n".join(lines))
    log("Geschrieben: data/vergleich.csv, results/vergleich.md")
    common.error_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
