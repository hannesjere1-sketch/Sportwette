"""Phase 12 - Trigger-Liste fuer die ganze Klasse < 1,80.

Der Auftrag: keine Festlegung auf eine Variante, sondern eine Liste ueber
alle elf ersten Ligen fuer die ganze Klasse unter 1,80 - mit Liga,
Vorquote und Torniveau je Fall, ausgelegt zum Mitschreiben der echten
Live-Quote.

Was diese Liste kann und was nicht:

* Die historischen Faelle stehen vollstaendig drin. Was in ihnen NICHT
  steht und auch nicht rekonstruierbar ist, ist die Live-Quote, die der
  Buchmacher in Minute X tatsaechlich angeboten hat. Die Spalten dafuer
  bleiben leer - sie sind zum Ausfuellen ab jetzt da, nicht zum
  Nachtragen von 2009.
* Zu jedem Fall steht die vom Modell geschaetzte Siegwahrscheinlichkeit
  und die Quote, ab der sich die Wette bei deutscher Wettsteuer lohnt.
  Das ist der Wert, gegen den die mitgeschriebene Live-Quote zu halten
  ist. Fuer die historischen Zeilen ist diese Schaetzung im Stichprobe
  drin, an der sie gelernt wurde - sie ist dort eine Beschreibung, keine
  Vorhersage. Fuer neue Spiele ist sie eine echte Vorhersage.

Ausserdem entsteht ein leeres Erfassungsblatt fuer kuenftige Spiele.
"""

from __future__ import annotations

import csv
import math
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import de, log, wilson, write_csv, write_text  # noqa: E402

HIER = os.path.dirname(os.path.abspath(__file__))
STEUER = 1.053          # deutsche Wettsteuer: 5,3 % vom Einsatz
GRENZE = 1.80


def torniveau():
    tore = defaultdict(int)
    spiele = defaultdict(int)
    with open(os.path.join(HIER, "data", "erw_matches_all.csv"),
              newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                t = int(r["fthg"]) + int(r["ftag"])
            except (ValueError, KeyError):
                continue
            tore[(r["league"], r["season"])] += t
            spiele[(r["league"], r["season"])] += 1
    return {k: tore[k] / spiele[k] for k in spiele if spiele[k] >= 50}


def main():
    # Die Regression steht in 12_ligaeffekt.py; von dort wird sie geladen,
    # damit es nur eine Fassung davon gibt.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ligaeffekt", os.path.join(HIER, "12_ligaeffekt.py"))
    lig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lig)

    niveau = torniveau()
    with open(os.path.join(HIER, "data", "35er-erweitert-faelle.csv"),
              newline="", encoding="utf-8") as fh:
        alle = list(csv.DictReader(fh))

    faelle = []
    for r in alle:
        if r["stufe"] != "1":
            continue
        quote = float(r["faire_heimquote"])
        if quote >= GRENZE:
            continue
        schluessel = (r["league"], r["season"])
        p0 = 1.0 / quote
        faelle.append({
            "roh": r,
            "logit_p0": math.log(p0 / (1.0 - p0)),
            "minute": int(r["minute"]),
            "torniveau": niveau.get(schluessel),
            "y": 1 if r["treffer"] == "1" else 0,
        })
    log("%d Faelle in der Klasse < %s" % (len(faelle), GRENZE))

    # Modell auf Vorquote und Minute. Das Torniveau bleibt draussen, weil
    # es in 12_ligaeffekt.py keinen messbaren Beitrag geliefert hat; es
    # steht in der Liste trotzdem als Spalte, damit man selbst nachsehen kann.
    X = [[1.0, f["logit_p0"], f["minute"]] for f in faelle]
    y = [f["y"] for f in faelle]
    beta, kov = lig.logistisch(X, y)
    fehler = lig.wald(beta, kov)
    log("Modell: b0=%.6f  logit_p0=%.6f  minute=%.6f" % tuple(beta))

    zeilen = []
    for f in faelle:
        eta = beta[0] + beta[1] * f["logit_p0"] + beta[2] * f["minute"]
        eta = max(-30.0, min(30.0, eta))
        p = 1.0 / (1.0 + math.exp(-eta))
        r = f["roh"]
        zeilen.append({
            "datum": r["date"],
            "liga": r["league_name"],
            "liga_code": r["league"],
            "saison": r["season"],
            "team": r["team"],
            "gegner": r["gegner"],
            "vorquote_fair": round(float(r["faire_heimquote"]), 4),
            "torniveau_liga_saison": round(f["torniveau"], 3) if f["torniveau"] else "",
            "minute_gegentor": f["minute"],
            "modell_p_sieg": round(p, 4),
            "modell_faire_quote": round(1.0 / p, 2),
            "lohnt_ab_quote": round(STEUER / p, 2),
            "live_quote_notiert": "",
            "einsatz": "",
            "notiert_am": "",
            "bemerkung": "",
            "endstand": r["endstand"],
            "ergebnis": r["ergebnis"],
            "treffer": r["treffer"],
        })
    zeilen.sort(key=lambda z: (z["datum"], z["liga_code"]))

    spalten = ["datum", "liga", "liga_code", "saison", "team", "gegner",
               "vorquote_fair", "torniveau_liga_saison", "minute_gegentor",
               "modell_p_sieg", "modell_faire_quote", "lohnt_ab_quote",
               "live_quote_notiert", "einsatz", "notiert_am", "bemerkung",
               "endstand", "ergebnis", "treffer"]
    write_csv(os.path.join(HIER, "data", "35er-triggerliste.csv"), zeilen, spalten)
    log("geschrieben: data/35er-triggerliste.csv (%d Zeilen)" % len(zeilen))

    # Leeres Erfassungsblatt fuer kuenftige Spiele
    vorlage_spalten = ["datum", "liga", "team", "gegner", "vorquote_angeboten",
                       "vorquote_fair", "minute_gegentor", "live_quote_angeboten",
                       "lohnt_ab_quote", "gewettet", "einsatz", "endstand",
                       "treffer", "bemerkung"]
    write_csv(os.path.join(HIER, "data", "35er-livequoten-erfassung.csv"),
              [], vorlage_spalten)
    log("geschrieben: data/35er-livequoten-erfassung.csv (leere Vorlage)")

    # ------------------------------------------------------------ Bericht ----
    t = sum(z["treffer"] == "1" for z in zeilen)
    lo, hi = wilson(t, len(zeilen))
    je_saison = Counter(z["saison"] for z in zeilen)
    je_liga = Counter(z["liga"] for z in zeilen)
    schnitt = len(zeilen) / len(je_saison)

    b = []
    b.append("# Trigger-Liste, Klasse `< 1,80`, elf erste Ligen\n")
    b.append("Erzeugt von `13_triggerliste.py`.\n")
    b.append("\n## Was in der Liste steht\n")
    b.append("`data/35er-triggerliste.csv` enthält **alle %d Fälle** der Klasse "
             "`< 1,80` über elf erste Ligen und neunzehn Saisons — ohne "
             "Vorauswahl nach Trefferquote, ohne Gegnerfilter, ohne "
             "Ligaauswahl.\n" % len(zeilen))
    b.append("\n| Spalte | Bedeutung |")
    b.append("| --- | --- |")
    for name, sinn in [
        ("datum, liga, saison, team, gegner", "das Spiel; `team` ist immer die Heimmannschaft"),
        ("vorquote_fair", "faire Vorab-Siegquote der Heimmannschaft, Buchmacher-Marge herausgerechnet"),
        ("torniveau_liga_saison", "Tore pro Spiel dieser Liga in dieser Saison"),
        ("minute_gegentor", "Minute des ersten Tors — es ist immer ein Gegentor"),
        ("modell_p_sieg", "vom Modell geschätzte Siegwahrscheinlichkeit ab diesem Moment"),
        ("modell_faire_quote", "`1 / modell_p_sieg` — die Quote, bei der es ein Nullsummenspiel wäre"),
        ("lohnt_ab_quote", "`1,053 / modell_p_sieg` — ab hier trägt die Wette die deutsche Wettsteuer"),
        ("live_quote_notiert, einsatz, notiert_am, bemerkung", "**leer, zum Ausfüllen**"),
        ("endstand, ergebnis, treffer", "wie das Spiel ausging"),
    ]:
        b.append("| `%s` | %s |" % (name, sinn))

    b.append("\n## Warum die Live-Quote leer bleibt\n")
    b.append("Weder football-data.co.uk noch ESPN führen Quoten während des "
             "Spiels. Die Live-Quote von 2009 ist nicht rekonstruierbar und "
             "wird es auch nicht. Die vier leeren Spalten sind deshalb kein "
             "Versäumnis, sondern der eigentliche Zweck der Liste: sie zeigt, "
             "wie ein Fall aussieht, und gibt die Zahl vor, gegen die die "
             "notierte Live-Quote zu halten ist.\n")
    b.append("Für laufende Spiele liegt daneben `data/35er-livequoten-"
             "erfassung.csv` — dieselbe Struktur, nur leer, mit einer Spalte "
             "für die angebotene Vorquote und einer für die angebotene "
             "Live-Quote.\n")

    b.append("\n## Wie oft das vorkommt\n")
    b.append("| Grösse | Wert |")
    b.append("| --- | ---: |")
    b.append("| Fälle insgesamt | %d |" % len(zeilen))
    b.append("| Saisons | %d |" % len(je_saison))
    b.append("| Auslöser pro Saison über elf Ligen | %s |" % de(schnitt, 1))
    b.append("| davon gewonnen | %d (%s %%) |" % (t, de(t / len(zeilen) * 100, 1)))
    b.append("| 95 %%-Intervall | %s – %s %% |" % (de(lo * 100, 1), de(hi * 100, 1)))
    b.append("| Quote, ab der es sich im Mittel lohnt | %s |"
             % de(STEUER / (t / len(zeilen)), 2))

    b.append("\n### Fälle je Liga\n")
    b.append("| Liga | Fälle | pro Saison |")
    b.append("| --- | ---: | ---: |")
    for liga, anz in je_liga.most_common():
        saisons = len({z["saison"] for z in zeilen if z["liga"] == liga})
        b.append("| %s | %d | %s |" % (liga, anz, de(anz / saisons, 1)))

    # ------------------------------------------------------- Eichung ----
    nach_p = sorted(zeilen, key=lambda z: z["modell_p_sieg"])
    gruppen = 8
    gross = len(nach_p) // gruppen
    # -------------------------------------------- Modell zum Nachrechnen ----
    b.append("\n## Das Modell zum Nachrechnen\n")
    b.append("Damit sich `lohnt_ab_quote` im Erfassungsblatt selbst rechnen "
             "lässt, hier die vollständigen Koeffizienten. Es ist das Modell "
             "mit zwei Grössen — **ohne** Torniveau, weil das nichts beiträgt "
             "(siehe `results/35er-ligaeffekt.md`).\n")
    b.append("| Grösse | Koeffizient | Standardfehler | z | p |")
    b.append("| --- | ---: | ---: | ---: | ---: |")
    for name, (bb, se, z, pw) in zip(
            ["Achsenabschnitt", "logit_p0", "minute"], fehler):
        b.append("| %s | %s | %s | %s | %s |"
                 % (name, de(bb, 6), de(se, 6), de(z, 2),
                    "< 0,0001" if pw < 0.0001 else de(pw, 4)))
    b.append("")
    b.append("### Schritt für Schritt von der bet365-Quote zur Mindestquote\n")
    b.append("Die Vorquote im Modell ist **nicht** die rohe bet365-Quote, "
             "sondern die margenbereinigte. Die Umrechnung braucht alle drei "
             "Quoten des Spiels, nicht nur die Heimquote.\n")
    b.append("1. **Marge herausrechnen.** Kehrwerte aller drei Quoten "
             "addieren:\n")
    b.append("   `S = 1/Heim + 1/Unentschieden + 1/Auswärts`\n")
    b.append("   Bei bet365 liegt `S` typisch zwischen 1,05 und 1,11 — das ist "
             "die Marge.\n")
    b.append("2. **Faire Siegwahrscheinlichkeit:**\n")
    b.append("   `p0 = (1/Heimquote) / S`   und   `faire Heimquote = 1 / p0`\n")
    b.append("3. **Auf die Modellskala bringen:**\n")
    b.append("   `logit_p0 = ln( p0 / (1 − p0) )`\n")
    b.append("4. **Modell anwenden**, mit der Minute des Gegentors:\n")
    b.append("   `eta = %s + %s × logit_p0 − %s × Minute`"
             % (de(beta[0], 6), de(beta[1], 6), de(abs(beta[2]), 6)))
    b.append("   `p = 1 / (1 + e^−eta)`\n")
    b.append("5. **Mindestquote:** `lohnt_ab_quote = 1,053 / p`. Die 1,053 ist "
             "die deutsche Wettsteuer von 5,3 % auf den Einsatz.\n")

    beispiel = None
    for z in zeilen:
        if 1.20 < z["vorquote_fair"] < 1.30:
            beispiel = z
            break
    if beispiel:
        p0 = 1.0 / beispiel["vorquote_fair"]
        lp = math.log(p0 / (1.0 - p0))
        eta = beta[0] + beta[1] * lp + beta[2] * beispiel["minute_gegentor"]
        b.append("**Beispiel** (%s, %s gegen %s):\n"
                 % (beispiel["datum"], beispiel["team"], beispiel["gegner"]))
        b.append("| Schritt | Wert |")
        b.append("| --- | ---: |")
        b.append("| faire Heimquote (Spalte `vorquote_fair`) | %s |"
                 % de(beispiel["vorquote_fair"], 4))
        b.append("| `p0` | %s |" % de(p0, 6))
        b.append("| `logit_p0` | %s |" % de(lp, 6))
        b.append("| Minute des Gegentors | %d |" % beispiel["minute_gegentor"])
        b.append("| `eta` | %s |" % de(eta, 6))
        b.append("| `p` | %s |" % de(1.0 / (1.0 + math.exp(-eta)), 4))
        b.append("| `lohnt_ab_quote` | %s |" % de(beispiel["lohnt_ab_quote"], 2))
        b.append("")
    b.append("Eine Warnung dazu: die Standardfehler oben gelten für die "
             "Koeffizienten, nicht für die vorhergesagte Wahrscheinlichkeit. "
             "`p` ist eine Schätzung mit eigener Unsicherheit, und "
             "`lohnt_ab_quote` erbt sie. Die Zahl ist ein Anhaltspunkt, keine "
             "Schwelle auf zwei Nachkommastellen.")

    b.append("\n## Stimmt die Modellschätzung?\n")
    b.append("Die Fälle nach geschätzter Siegwahrscheinlichkeit sortiert und in "
             "acht gleich grosse Gruppen geteilt. Läge das Modell daneben, "
             "würden geschätzte und tatsächliche Spalte auseinanderlaufen. "
             "Die Schätzung ist an denselben Fällen gelernt — das ist eine "
             "Beschreibung der Daten, keine Bewährungsprobe an neuen.\n")
    b.append("| Gruppe | Fälle | Vorquote (Mittel) | Minute (Mittel) | "
             "geschätzt | tatsächlich | 95 %-Intervall |")
    b.append("| --- | ---: | ---: | ---: | ---: | ---: | :---: |")
    for i in range(gruppen):
        von = i * gross
        bis = (i + 1) * gross if i < gruppen - 1 else len(nach_p)
        teil = nach_p[von:bis]
        n = len(teil)
        tr = sum(z["treffer"] == "1" for z in teil)
        glo, ghi = wilson(tr, n)
        b.append("| %d | %d | %s | %s | %s %% | %s %% | %s – %s %% |"
                 % (i + 1, n,
                    de(sum(z["vorquote_fair"] for z in teil) / n, 2),
                    de(sum(z["minute_gegentor"] for z in teil) / n, 0),
                    de(sum(z["modell_p_sieg"] for z in teil) / n * 100, 1),
                    de(tr / n * 100, 1),
                    de(glo * 100, 1), de(ghi * 100, 1)))

    b.append("\n## Wozu das Mitschreiben dient\n")
    b.append("Die Trefferquote allein sagt nichts darüber, ob sich eine Wette "
             "lohnt. Entscheidend ist allein der Abstand zwischen unserer "
             "Trefferquote und der Wahrscheinlichkeit, die in der angebotenen "
             "Live-Quote schon eingepreist ist. Diesen Abstand kennen wir "
             "bisher in keinem einzigen Fall, weil uns die eine Zahl fehlt, "
             "die man nicht rekonstruieren kann.\n")
    b.append("Deshalb ist die nächste Arbeit nicht eine weitere Auswertung, "
             "sondern das Sammeln echter Live-Quoten. Bei rund %s Auslösern "
             "pro Saison über elf Ligen kommen genug zusammen, um nach einer "
             "Saison zu sehen, ob es einen Abstand gibt — und in welche "
             "Richtung." % de(schnitt, 0))

    write_text(os.path.join(HIER, "results", "35er-triggerliste.md"),
               "\n".join(b) + "\n")
    log("geschrieben: results/35er-triggerliste.md")


if __name__ == "__main__":
    main()
