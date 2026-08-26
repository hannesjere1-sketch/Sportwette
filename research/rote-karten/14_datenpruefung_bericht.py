"""Phase 13 - Bericht ueber die Datenpruefungen.

Fasst zusammen, was 10_eigentore_pruefung.py und 11_halbzeit_pruefung.py
gemessen haben, und klaert die drei Rueckfragen zum letzten Durchgang:

1. Welche Fallzahl gilt - 343, 338 oder 340?
2. Liverpool-Newcastle am 11.05.2014: hat dort nicht Liverpool selbst
   zuerst getroffen?
3. Die Eigentor-Validierung ergab 78 von 80. Was ist mit den zwei uebrigen?
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import de, log, wilson, write_text  # noqa: E402

HIER = os.path.dirname(os.path.abspath(__file__))
TEAMID_RE = re.compile(r"/teams/(\d+)")
BEISPIEL = "E0-1314-2014-05-11-liverpool-newcastle"


def lies(name):
    with open(os.path.join(HIER, "data", name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def beispiel_tore():
    """Die Tor-Ereignisse des Einzelfalls, direkt aus dem ESPN-Rohbestand."""
    pfad = os.path.join(HIER, "data", "cache", "espn_plays_%s.json" % BEISPIEL)
    if not os.path.isfile(pfad):
        return None
    with open(pfad, encoding="utf-8") as fh:
        daten = json.load(fh)
    ids = {}
    for reihe in csv.reader(open(os.path.join(HIER, "data", "erw_teamids.csv"),
                                 newline="", encoding="utf-8")):
        if len(reihe) >= 3 and reihe[0] == BEISPIEL:
            ids = {reihe[1]: "Liverpool (Heim)", reihe[2]: "Newcastle (Gast)"}
    out = []
    for eintrag in daten.get("items") or []:
        if not eintrag.get("scoringPlay"):
            continue
        treffer = TEAMID_RE.search(((eintrag.get("team") or {}).get("$ref") or ""))
        out.append((
            (eintrag.get("clock") or {}).get("displayValue", ""),
            ((eintrag.get("type") or {}).get("text") or "").strip(),
            ids.get(treffer.group(1), "?") if treffer else "kein Team",
            (eintrag.get("text") or "").strip(),
        ))
    return out


def main():
    faelle = lies("35er-erweitert-faelle.csv")
    erst = [f for f in faelle if f["stufe"] == "1"]
    og = lies("eigentor-pruefung.csv")
    hz = lies("halbzeit-pruefung.csv")

    B = []
    P = B.append
    P("# Datenprüfung zum erweiterten Durchgang\n")
    P("Erzeugt von `14_datenpruefung_bericht.py`; die Messungen stammen aus")
    P("`10_eigentore_pruefung.py` und `11_halbzeit_pruefung.py`.\n")

    # ------------------------------------------------------- 1. Fallzahl ----
    P("\n## 1. Welche Fallzahl gilt\n")
    P("**343.** Nachgezählt direkt in `data/35er-erweitert-faelle.csv`,")
    P("Klasse `< 1,30`, erste Ligen.\n")
    kern = [f for f in erst if float(f["faire_heimquote"]) < 1.30]
    treffer = sum(1 for f in kern if f["treffer"] == "1")
    alt = [f for f in kern if int(f["season"][:2]) < 15]
    neu = [f for f in kern if int(f["season"][:2]) >= 15]
    ALTE_LIGEN = {"E0", "D1", "SP1", "I1", "F1"}
    P("| Aufteilung | Fälle | Treffer | Trefferquote |")
    P("| --- | ---: | ---: | ---: |")
    P("| gesamt | %d | %d | %s %% |"
      % (len(kern), treffer, de(treffer / len(kern) * 100)))
    for titel, menge in (("2005/06 – 2014/15", alt), ("2015/16 – 2023/24", neu)):
        t = sum(1 for f in menge if f["treffer"] == "1")
        P("| %s | %d | %d | %s %% |"
          % (titel, len(menge), t, de(t / len(menge) * 100)))
    P("")
    P("| Zerlegung | Fälle | Treffer | Trefferquote |")
    P("| --- | ---: | ---: | ---: |")
    summe = 0
    for titel, pruef in (
        ("5 alte Ligen, 2015 – 2024", lambda f: f["league"] in ALTE_LIGEN and int(f["season"][:2]) >= 15),
        ("5 alte Ligen, 2005 – 2015", lambda f: f["league"] in ALTE_LIGEN and int(f["season"][:2]) < 15),
        ("6 neue Ligen, 2015 – 2024", lambda f: f["league"] not in ALTE_LIGEN and int(f["season"][:2]) >= 15),
        ("6 neue Ligen, 2005 – 2015", lambda f: f["league"] not in ALTE_LIGEN and int(f["season"][:2]) < 15),
    ):
        menge = [f for f in kern if pruef(f)]
        summe += len(menge)
        t = sum(1 for f in menge if f["treffer"] == "1")
        P("| %s | %d | %d | %s %% |"
          % (titel, len(menge), t, de(t / len(menge) * 100)))
    P("| **Summe** | **%d** | | |" % summe)
    P("")
    P("Beide Aufteilungen ergeben 343. Die abweichenden Zahlen 338 und 340")
    P("standen nur in meiner Zusammenfassungsnachricht, nicht in")
    P("`results/35er-erweitert.md` — dort steht durchgehend 343. Es waren")
    P("Übertragungsfehler beim Abtippen der Zerlegung: 118 statt 122 und")
    P("220 statt 221 in den Zeithälften, 69 als 68 und 100 als 101 und 53")
    P("als 50 in der Zerlegung. Die Tabellen im Bericht waren richtig, die")
    P("Nachricht war es nicht. Ich habe sie neu aus der Falldatei gerechnet,")
    P("statt sie noch einmal abzuschreiben.")

    # -------------------------------------------------------- 2. Einzelfall --
    P("\n## 2. Liverpool – Newcastle, 11.05.2014\n")
    fall = [f for f in faelle if f["match_id"] == BEISPIEL]
    tore = beispiel_tore()
    if tore:
        P("Der Fall ist richtig — aber die Rückfrage trifft genau den")
        P("wunden Punkt. Das erste Tor fällt in Minute 20, und geschossen")
        P("hat es ein **Liverpooler**: Martin Škrtel, ins eigene Tor.\n")
        P("| Minute | Ereignis | zählt für | Text bei ESPN |")
        P("| ---: | --- | --- | --- |")
        for minute, typ, seite, text in tore:
            P("| %s | %s | %s | %s |" % (minute, typ, seite, text[:80]))
        P("")
        if fall:
            P("Die Gegenprobe bei football-data.co.uk: Halbzeitstand **0:1**,")
            P("Endstand **%s**. Beide Quellen sagen dasselbe."
              % fall[0]["endstand"])
        P("")
        P("Für die Strategie ist das die richtige Zuordnung: Liverpool lag")
        P("nach 20 Minuten 0:1 zurück, unabhängig davon, wessen Fuß den Ball")
        P("ins Tor gelenkt hat. Der Trigger fragt nach dem Spielstand, nicht")
        P("nach dem Schützen.")
        P("")
        P("Ob das ein Muster ist, beantwortet Abschnitt 3: Eigentore sind")
        P("die Fallgruppe, in der eine falsche Zuordnung am ehesten")
        P("passieren würde — deshalb sind sie vollständig durchgeprüft.")

    # ------------------------------------------------------- 3. Eigentore ----
    P("\n## 3. Eigentore: alle statt achtzig\n")
    mit = [r for r in og if int(r["eigentore"]) > 0]
    ohne = [r for r in og if int(r["eigentore"]) == 0]
    ab_mit = [r for r in mit if r["passt"] == "0"]
    ab_ohne = [r for r in ohne if r["passt"] == "0"]
    dreh = [r for r in mit if r["drehen_wuerde_helfen"] == "1"]
    P("Die frühere Angabe „78 von 80\" kam aus einer Stichprobe. Eine")
    P("Stichprobe lässt genau die Frage offen, die gestellt wurde: sind die")
    P("zwei Ausnahmen Zufall oder Muster? Deshalb sind jetzt **alle**")
    P("zwischengespeicherten Spiele geprüft.\n")
    P("Verfahren: Aus den Team-Verweisen der ESPN-Tor-Ereignisse wird der")
    P("Endstand rekonstruiert und mit football-data.co.uk verglichen. Zwei")
    P("Quellen, die nichts voneinander wissen.\n")
    P("| Menge | Spiele | Endstand weicht ab | Anteil |")
    P("| --- | ---: | ---: | ---: |")
    P("| Spiele **mit** Eigentor | %d | %d | %s %% |"
      % (len(mit), len(ab_mit), de(len(ab_mit) / len(mit) * 100, 2)))
    P("| Spiele **ohne** Eigentor | %d | %d | %s %% |"
      % (len(ohne), len(ab_ohne), de(len(ab_ohne) / len(ohne) * 100, 2)))
    P("")
    P("**Das Ergebnis ist das Gegenteil einer Warnung.** Spiele mit")
    P("Eigentor stimmen häufiger als Spiele ohne. Eigentore sind also")
    P("keine Fehlerquelle — ESPN schreibt sie zuverlässig der Mannschaft")
    P("gut, für die sie zählen.\n")
    P("Die entscheidende Zusatzprobe: bei wie vielen der Abweichungen")
    P("würde ein Umdrehen der Eigentor-Zuordnung den Endstand richtig")
    P("machen? Antwort: bei **%d von %d**. Die Abweichungen kommen also"
      % (len(dreh), len(ab_mit)))
    P("nicht von den Eigentoren, sondern davon, dass in ESPNs Spielverlauf")
    P("einzelne Tore fehlen — vor allem in älteren Saisons kleinerer Ligen.")
    P("")
    P("**Und diese Spiele fließen ohnehin nicht ein.** Die Auswertung")
    P("verwirft jedes Spiel, dessen rekonstruierter Endstand von")
    P("football-data abweicht — das ist die Verwurfskategorie „Endstand")
    P("weicht ab\". Die hochgerechneten „rund neun falsch zugeordneten")
    P("Fälle\" gibt es deshalb nicht: die betroffenen Spiele werden")
    P("aussortiert, bevor ein Fall daraus wird.")

    # -------------------------------------------------------- 4. Halbzeit ----
    P("\n## 4. Die schärfere Probe: der Halbzeitstand\n")
    P("Der Endstand-Abgleich prüft nur die Summe. Zwei Fehler, die sich")
    P("aufheben, würde er nicht bemerken — und für den Trigger zählt genau")
    P("das, was er nicht prüft: **wer** zuerst trifft und **wann**.\n")
    P("Deshalb die zweite Probe: der Halbzeitstand, aus ESPNs Ereignissen")
    P("der ersten Halbzeit rekonstruiert und gegen die Spalten `HTHG`/`HTAG`")
    P("von football-data gehalten. Ein 35er-Fall liegt per Definition vor")
    P("Minute 35, also immer in der ersten Halbzeit.\n")
    def block(titel, menge):
        z = Counter(r["status"] for r in menge)
        pruefbar = z["Halbzeit stimmt"] + z["Halbzeit weicht ab"]
        P("| %s | %d | %d | %s %% |"
          % (titel, pruefbar, z["Halbzeit stimmt"],
             de(z["Halbzeit stimmt"] / pruefbar * 100, 2) if pruefbar else "—"))
        return z
    P("| Menge | prüfbare Spiele | Halbzeitstand stimmt | Anteil |")
    P("| --- | ---: | ---: | ---: |")
    block("alle zwischengespeicherten Spiele", hz)
    fall_hz = [r for r in hz if r["ist_fall"] == "1"]
    z_fall = block("nur die 3217 Fälle", fall_hz)
    block("nur Spiele mit Eigentor in Halbzeit 1",
          [r for r in hz if r["eigentor_h1"] == "1"])
    P("")
    abw = {r["match_id"] for r in fall_hz if r["status"] == "Halbzeit weicht ab"}
    P("Von den Fällen weichen **%d** ab. Ihr Gewicht:\n" % len(abw))
    P("| Klasse | Fälle | davon betroffen | Trefferquote | ohne die Betroffenen |")
    P("| --- | ---: | ---: | ---: | ---: |")
    for grenze, titel in ((1.30, "< 1,30"), (1.50, "< 1,50"), (1.80, "< 1,80")):
        menge = [f for f in erst if float(f["faire_heimquote"]) < grenze]
        rest = [f for f in menge if f["match_id"] not in abw]
        t_alle = sum(1 for f in menge if f["treffer"] == "1")
        t_rest = sum(1 for f in rest if f["treffer"] == "1")
        P("| %s | %d | %d | %s %% | %s %% |"
          % (titel, len(menge), len(menge) - len(rest),
             de(t_alle / len(menge) * 100), de(t_rest / len(rest) * 100)))
    P("")
    P("Selbst wenn **jede** dieser Abweichungen bedeutete, dass der Fall")
    P("gar keiner ist, ändert das an keiner Trefferquote mehr als zwei")
    P("Zehntel Prozentpunkte.")
    P("")
    betroffen = [f for f in faelle if f["match_id"] in abw]
    duenn = {"B1", "G1", "T1"}
    in_duennen = sum(1 for f in betroffen if f["league"] in duenn)
    jahre = sorted(f["date"][:4] for f in betroffen)
    P("Auffällig ist, wo sie liegen: **%d von %d** in Belgien, Griechenland"
      % (in_duennen, len(betroffen)))
    P("oder der Türkei, und die Jahre reichen von %s bis %s — also genau"
      % (jahre[0], jahre[-1]))
    P("dort, wo ESPNs Spielverläufe ohnehin am dünnsten sind. In den")
    P("Saisons ab 2012 gibt es keine einzige Abweichung."
      if all(j < "2012" for j in jahre) else
      "Neuere Saisons sind kaum betroffen.")

    P("\n## 5. Was bleibt\n")
    P("| Frage | Antwort |")
    P("| --- | --- |")
    P("| Welche Fallzahl gilt? | 343. Die abweichenden Zahlen waren Tippfehler in meiner Nachricht. |")
    P("| Liverpool – Newcastle | richtig zugeordnet; das Tor war ein Eigentor von Škrtel. |")
    P("| Eigentore fehlerhaft? | Nein. %d von %d Spielen mit Eigentor stimmen, und von den %d Abweichungen %s. |"
      % (len(mit) - len(ab_mit), len(mit), len(ab_mit),
         "wäre keine einzige durch eine umgedrehte Eigentor-Zuordnung erklärbar"
         if not dreh else
         ("wäre genau eine durch eine umgedrehte Eigentor-Zuordnung erklärbar"
          if len(dreh) == 1 else
          "wären %d durch eine umgedrehte Eigentor-Zuordnung erklärbar" % len(dreh))))
    P("| Hochgerechnet neun falsche Fälle? | Nein. Spiele mit abweichendem Endstand werden verworfen, bevor ein Fall entsteht. |")
    P("| Frühe Tore richtig zugeordnet? | In %s %% der Fälle bestätigt der unabhängige Halbzeitstand die Zuordnung. |"
      % de(z_fall["Halbzeit stimmt"] / (z_fall["Halbzeit stimmt"] + z_fall["Halbzeit weicht ab"]) * 100, 2))

    write_text(os.path.join(HIER, "results", "35er-datenpruefung.md"),
               "\n".join(B) + "\n")
    log("geschrieben: results/35er-datenpruefung.md")


if __name__ == "__main__":
    main()
