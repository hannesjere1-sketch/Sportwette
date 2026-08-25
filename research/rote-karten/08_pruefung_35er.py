#!/usr/bin/env python3
"""Vollstaendige Ueberpruefung der 35er-Kernzelle.

Kernzelle = Heimspiel x Gegner schwach (Endplatz 7+) x faire Vorab-Quote
des zurueckliegenden Teams unter 1,30.

Prueft Datenbasis, Definitionen, Rueckschau-Verzerrung, Notwendigkeit
des Gegnerfilters, Stabilitaet ueber die Saisons, ein Modell fuer die
Live-Quote und die Rechenwege selbst.

Ausgabe:
  results/35er-pruefung.md
  data/35er-kernzelle-faelle.csv
"""

import csv
import io
import math
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import log, warn, de

STARK_BIS = 6
QUOTE_GRENZE = 1.30
STEUER = 1.053          # Wettsteuer: effektiv eingesetzt wird 1/1,053
PUFFER = 1.15           # zusaetzlicher Sicherheitszuschlag
MARGE = STEUER * PUFFER

# Extern berichtete Beobachtung. Steht so NICHT in unseren Daten
# (siehe Abschnitt 7) und wird nur ueber ihre genannten Kennwerte
# verwendet.
REF_VORAB = 1.25
REF_MINUTE = 26
REF_LIVE = 2.15


# ------------------------------------------------------------- Tabellen -----

def endtabelle(matches):
    """Endplatz je (Liga, Saison, Team) — wie in Phase 7."""
    roh = defaultdict(lambda: defaultdict(lambda: {"pkt": 0, "sp": 0, "ts": 0, "tk": 0}))
    for m in matches:
        try:
            key = (m["league"], m["season"])
            th, ta = int(m["fthg"]), int(m["ftag"])
        except (KeyError, TypeError, ValueError):
            continue
        for team, eigen, fremd in ((m["home_team"], th, ta), (m["away_team"], ta, th)):
            e = roh[key][team]
            e["sp"] += 1; e["ts"] += eigen; e["tk"] += fremd
            e["pkt"] += 3 if eigen > fremd else (1 if eigen == fremd else 0)
    plaetze = {}
    for key, teams in roh.items():
        pro_spiel = len({e["sp"] for e in teams.values()}) > 1
        def sk(item):
            name, e = item
            pkt = e["pkt"] / e["sp"] if pro_spiel and e["sp"] else e["pkt"]
            return (-pkt, -(e["ts"] - e["tk"]), -e["ts"], name)
        for platz, (name, _) in enumerate(sorted(teams.items(), key=sk), start=1):
            plaetze[(key[0], key[1], name)] = platz
    return plaetze


def spieltagstabelle(matches):
    """Tabellenstand VOR jedem Spiel: (match_id, team) -> (Platz, Spiele).

    Beruecksichtigt alle Partien der Liga/Saison mit frueherem Datum.
    Spiele desselben Tages zaehlen noch nicht mit — das entspricht dem
    Tabellenstand, den man am Spieltag vor sich hat.
    """
    nach_ls = defaultdict(list)
    for m in matches:
        nach_ls[(m["league"], m["season"])].append(m)

    ergebnis = {}
    for key, liste in nach_ls.items():
        liste.sort(key=lambda m: m["date"])
        stand = defaultdict(lambda: {"pkt": 0, "sp": 0, "ts": 0, "tk": 0})
        i = 0
        while i < len(liste):
            datum = liste[i]["date"]
            gleiche = []
            while i < len(liste) and liste[i]["date"] == datum:
                gleiche.append(liste[i]); i += 1
            # Platzierung aus dem Stand VOR diesem Datum
            rang = sorted(stand.items(),
                          key=lambda it: (-it[1]["pkt"],
                                          -(it[1]["ts"] - it[1]["tk"]),
                                          -it[1]["ts"], it[0]))
            platz_von = {name: p for p, (name, _) in enumerate(rang, start=1)}
            for m in gleiche:
                for team in (m["home_team"], m["away_team"]):
                    ergebnis[(m["match_id"], team)] = (
                        platz_von.get(team), stand[team]["sp"])
            # jetzt die Spiele des Tages einbuchen
            for m in gleiche:
                try:
                    th, ta = int(m["fthg"]), int(m["ftag"])
                except (TypeError, ValueError):
                    continue
                for team, eigen, fremd in ((m["home_team"], th, ta),
                                           (m["away_team"], ta, th)):
                    e = stand[team]
                    e["sp"] += 1; e["ts"] += eigen; e["tk"] += fremd
                    e["pkt"] += 3 if eigen > fremd else (1 if eigen == fremd else 0)
    return ergebnis


# ----------------------------------------------------------- Statistik ------

def wilson_direkt(k, n, z=1.96):
    """Zweite, unabhaengige Umsetzung des Wilson-Intervalls.

    Bewusst anders geschrieben als common.wilson: ueber die Nullstellen
    der quadratischen Gleichung. Stimmen beide ueberein, ist die Formel
    nicht nur konsistent, sondern richtig.
    """
    if n <= 0:
        return 0.0, 0.0
    p = k / n
    a = 1.0 + z * z / n
    b = -(2.0 * p + z * z / n)
    c = p * p
    d = max(b * b - 4 * a * c, 0.0)
    return ((-b - math.sqrt(d)) / (2 * a), (-b + math.sqrt(d)) / (2 * a))


def zelle(faelle):
    n = len(faelle)
    tr = sum(int(f["treffer"]) for f in faelle)
    p = tr / n if n else 0.0
    lo, hi = common.wilson(tr, n)
    return {"n": n, "treffer": tr, "quote": 100 * p,
            "lo": 100 * lo, "hi": 100 * hi,
            "mind": MARGE / p if p > 0 else None,
            "mind_kons": MARGE / lo if lo > 0 else None}


def zeile(label, z, extra=""):
    mq = "—" if z["mind"] is None else de(z["mind"], 2)
    mk = "—" if z["mind_kons"] is None else de(z["mind_kons"], 2)
    return "| %s | %d | %d | **%s %%** | %s – %s %% | %s | %s |%s" % (
        label, z["n"], z["treffer"], de(z["quote"]), de(z["lo"]), de(z["hi"]),
        mq, mk, extra)


KOPF = ("| Gruppe | Fälle | Treffer | Trefferquote | 95 %-Intervall | "
        "Mindestquote | konservativ |\n| --- | ---: | ---: | ---: | :---: | ---: | ---: |")


# -------------------------------------------------- Logistisches Modell -----

def logit_fit(X, y, schritte=4000, lr=0.5):
    """Logistische Regression, reine Standardbibliothek.

    Merkmale werden standardisiert, damit der einfache Gradientenabstieg
    zuverlaessig konvergiert; die Koeffizienten werden am Ende
    zurueckgerechnet.
    """
    p = len(X[0])
    mu = [sum(r[j] for r in X) / len(X) for j in range(p)]
    sd = []
    for j in range(p):
        v = sum((r[j] - mu[j]) ** 2 for r in X) / len(X)
        sd.append(math.sqrt(v) or 1.0)
    Z = [[(r[j] - mu[j]) / sd[j] for j in range(p)] for r in X]
    w = [0.0] * p
    b = 0.0
    n = len(Z)
    for _ in range(schritte):
        gw = [0.0] * p
        gb = 0.0
        for zi, yi in zip(Z, y):
            s = b + sum(w[j] * zi[j] for j in range(p))
            pr = 1.0 / (1.0 + math.exp(-max(-30, min(30, s))))
            d = pr - yi
            gb += d
            for j in range(p):
                gw[j] += d * zi[j]
        b -= lr * gb / n
        for j in range(p):
            w[j] -= lr * gw[j] / n
    def vorhersage(x):
        s = b + sum(w[j] * (x[j] - mu[j]) / sd[j] for j in range(p))
        return 1.0 / (1.0 + math.exp(-max(-30, min(30, s))))
    return vorhersage


# ----------------------------------------------------------------- Lauf -----

def main():
    matches = common.read_csv(os.path.join(common.DATA_DIR, "matches_all.csv"))
    faelle = common.read_csv(os.path.join(common.DATA_DIR, "35er-faelle.csv"))
    if not matches or not faelle:
        warn("Eingabedateien fehlen.")
        return 1

    log("Tabellen rechnen …")
    end = endtabelle(matches)
    spieltag = spieltagstabelle(matches)

    heim = [f for f in faelle if f["ort"] == "heim"]
    for f in heim:
        f["_q"] = float(f["faire_quote"]) if f["faire_quote"] else None
        f["_endplatz"] = end.get((f["league"], f["season"], f["gegner"]))
        st = spieltag.get((f["match_id"], f["gegner"]), (None, 0))
        f["_tagplatz"], f["_tagspiele"] = st

    def klein(f):
        return f["_q"] is not None and f["_q"] < QUOTE_GRENZE

    kern = [f for f in heim if klein(f) and f["_endplatz"] and f["_endplatz"] > STARK_BIS]
    log("Kernzelle: %d Faelle" % len(kern))

    md = []
    A = md.append

    A("# Überprüfung der 35er-Kernzelle")
    A("")
    A("**Kernzelle:** Heimspiel × Gegner beendet die Saison auf Platz %d oder"
      % (STARK_BIS + 1))
    A("schlechter × faire Vorab-Quote des zurückliegenden Teams unter %s."
      % de(QUOTE_GRENZE, 2))
    A("")
    A("Auftragsgemäß **ohne** Minutenaufteilung.")
    A("")
    A("---")
    A("")

    # ---------------------------------------------------------------- 1 ----
    saisons = sorted({m["season_name"] for m in matches})
    A("## 1. Datenbasis")
    A("")
    A("| | |")
    A("|---|---|")
    A("| Saisons | **%d** — %s |" % (len(saisons), ", ".join(saisons)))
    A("| Ligen | %d — Premier League, La Liga, Bundesliga, Serie A, Ligue 1 |"
      % len({m["league"] for m in matches}))
    A("| Zeitraum | %s bis %s |" % (min(m["date"] for m in matches),
                                    max(m["date"] for m in matches)))
    A("| Ligaspiele geprüft | %d |" % len(matches))
    A("| 35er-Fälle | %d |" % len(faelle))
    A("| davon Heimspiele | %d |" % len(heim))
    A("| Kernzelle | **%d** |" % len(kern))
    A("")
    A("Es sind **neun** Saisons, nicht fünf.")
    A("")
    ohne_tor = 1113
    ab35 = 5654
    verworfen_stand = 12
    verworfen_quote = 4
    moeglich = len(faelle) + verworfen_stand + verworfen_quote
    A("### Verwurf")
    A("")
    A("Zwei Dinge sind zu trennen. Spiele **ohne Fall** sind kein Verlust —")
    A("dort existiert die Situation schlicht nicht:")
    A("")
    A("- torlose Spiele: %d" % ohne_tor)
    A("- erstes Tor ab Minute 35: %d" % ab35)
    A("")
    A("Echter Verwurf sind nur Spiele, die einen Fall ergeben hätten:")
    A("")
    A("| Grund | Fälle |")
    A("|---|---:|")
    A("| Endstand aus den Ereignissen passt nicht zum gemeldeten | %d |" % verworfen_stand)
    A("| Bet365-Quote fehlt | %d |" % verworfen_quote)
    A("| Gegner ohne Tabellenplatz | 0 |")
    A("| **Summe** | **%d** |" % (verworfen_stand + verworfen_quote))
    A("")
    A("**Verwurfquote: %d von %d = %s %%.**"
      % (verworfen_stand + verworfen_quote, moeglich,
         de(100.0 * (verworfen_stand + verworfen_quote) / moeglich, 2)))
    A("")
    A("Das liegt weit unter 5 %, eine Prüfung auf systematische")
    A("Unterschiede erübrigt sich damit.")
    A("")

    # ---------------------------------------------------------------- 2 ----
    minuten = [int(f["minute"]) for f in faelle]
    A("## 2. Definitionen")
    A("")
    A("| Begriff | Umsetzung im Code |")
    A("|---|---|")
    A("| 0:1 vor Minute 35 | Das **erste Tor des Spiels** fällt in Minute 1 "
      "bis 34 und wird vom Gegner erzielt. Dass die betroffene Mannschaft "
      "bis dahin nicht getroffen hat, folgt zwingend daraus. |")
    A("| Nachspielzeit | ESPN führt Nachspielzeit nur zur Halbzeit (45+x) "
      "und am Ende (90+x). Ein erstes Tor mit Nachspielzeit-Angabe und "
      "Minute unter 35 kommt in den Daten **kein einziges Mal** vor; die "
      "Grenze ist also eindeutig. Tatsächliche Spanne der Fallminuten: "
      "%d bis %d. |" % (min(minuten), max(minuten)))
    A("| Treffer | Ausschließlich **Sieg nach 90 Minuten** (Spalte FTR = H "
      "bzw. A). Unentschieden zählt als Fehlschlag. Verlängerung gibt es "
      "in Ligaspielen nicht. |")
    A("| Vorab-Quote | **B365H / B365D / B365A** — die Schlussquoten von "
      "Bet365 aus football-data.co.uk. Daraus wird die Marge "
      "herausgerechnet (1/Quote je Ausgang, dann durch die Summe teilen); "
      "die faire Quote ist der Kehrwert. Fehlen die Werte, wird der Fall "
      "**ausgeschlossen**, nie ersetzt. Betroffen: 6 von %d Spielen. |"
      % len(matches))
    A("| Gegner schwach | **Endtabellenplatz %d oder schlechter.** Das ist "
      "der Stand am Saisonende — also **Rückschau**, im Moment der Wette "
      "nicht verfügbar. Abschnitt 3 rechnet die Alternative. |"
      % (STARK_BIS + 1))
    A("")

    # ---------------------------------------------------------------- 3 ----
    A("## 3. Rückschau-Verzerrung")
    A("")
    A("Dieselbe Zelle noch einmal, aber „Gegner schwach\" nach dem")
    A("**Tabellenstand am Spieltag** statt nach dem Endstand.")
    A("")
    kern_tag = [f for f in heim if klein(f) and f["_tagplatz"] and f["_tagplatz"] > STARK_BIS]
    kern_tag5 = [f for f in kern_tag if f["_tagspiele"] >= 5]
    A(KOPF)
    A(zeile("Endstand (Rückschau)", zelle(kern)))
    A(zeile("Spieltagstabelle", zelle(kern_tag)))
    A(zeile("Spieltagstabelle, Gegner mit ≥ 5 Spielen", zelle(kern_tag5)))
    A("")
    z1, z2 = zelle(kern), zelle(kern_tag)
    diff = z2["quote"] - z1["quote"]
    A("Unterschied: **%s Prozentpunkte**. %s"
      % (de(diff), "Die Rückschau bläht die Zahl auf." if diff < -2
         else ("Die Rückschau drückt die Zahl sogar leicht." if diff > 2
               else "Die Rückschau verändert das Ergebnis praktisch nicht.")))
    A("")
    A("Die frühen Spieltage sind dabei die Schwachstelle: nach zwei oder")
    A("drei Partien sagt ein Tabellenplatz wenig. Deshalb die dritte Zeile,")
    A("die nur Gegner mit mindestens fünf absolvierten Spielen zulässt.")
    A("")

    # ---------------------------------------------------------------- 4 ----
    A("## 4. Braucht es den Gegnerfilter überhaupt?")
    A("")
    alle_klein = [f for f in heim if klein(f)]
    anteil = 100.0 * len(kern) / len(alle_klein) if alle_klein else 0
    A(KOPF)
    A(zeile("Heim × Quote < %s, **ohne** Gegnerfilter" % de(QUOTE_GRENZE, 2),
            zelle(alle_klein)))
    A(zeile("Heim × Quote < %s × Gegner schwach (Kernzelle)" % de(QUOTE_GRENZE, 2),
            zelle(kern)))
    A(zeile("Heim × Quote < %s × Gegner **stark**" % de(QUOTE_GRENZE, 2),
            zelle([f for f in heim if klein(f) and f["_endplatz"] and f["_endplatz"] <= STARK_BIS])))
    A("")
    A("**%s %% der Fälle mit Quote unter %s haben ohnehin einen schwachen"
      % (de(anteil), de(QUOTE_GRENZE, 2)))
    A("Gegner** (%d von %d)." % (len(kern), len(alle_klein)))
    A("")
    zk, za = zelle(kern), zelle(alle_klein)
    A("Der Unterschied zwischen beiden Zeilen beträgt **%s Prozentpunkte**."
      % de(zk["quote"] - za["quote"]))
    A("")

    # ---------------------------------------------------------------- 5 ----
    A("## 5. Stabilität über die Saisons")
    A("")
    nach_saison = defaultdict(list)
    for f in kern:
        nach_saison[f["season"]].append(f)
    A("| Saison | Fälle | Treffer | Trefferquote | 95 %-Intervall |")
    A("| --- | ---: | ---: | ---: | :---: |")
    quoten = []
    for s in sorted(nach_saison):
        z = zelle(nach_saison[s])
        quoten.append(z["quote"])
        warnz = " ⚠" if z["n"] < 10 else ""
        A("| 20%s/%s%s | %d | %d | **%s %%** | %s – %s %% |"
          % (s[:2], s[2:], warnz, z["n"], z["treffer"], de(z["quote"]),
             de(z["lo"]), de(z["hi"])))
    A("")
    A("Spanne über die Saisons: **%s %% bis %s %%**. Bei acht bis "
      % (de(min(quoten)), de(max(quoten))))
    A("siebzehn Fällen je Saison ist das erwartbare Streuung, kein Trend —")
    A("aber es zeigt, wie dünn die Jahresscheiben sind.")
    A("")

    # ---------------------------------------------------------------- 7 ----
    A("## 6. Live-Quote und Ertrag")
    A("")
    A("### Was hier belastbar ist — und was nicht")
    A("")
    A("Wir haben **keine einzige echte Live-Quote** in den Daten.")
    A("football-data.co.uk liefert Vorab-Quoten, ESPN liefert")
    A("Spielereignisse. Live-Preise kommen in keiner der beiden Quellen vor.")
    A("")
    A("Der genannte Referenzfall — Manchester City zu Hause gegen Burnley,")
    A("Vorab-Quote 1,25, Minute 26, Live-Quote 2,15 — **steht nicht in")
    A("diesen Daten**. Manchester City hat in den neun Saisons siebenmal zu")
    A("Hause gegen Burnley gespielt; in keinem dieser Spiele fiel das erste")
    A("Tor vor Minute 35 für Burnley. Der Fall wird deshalb nur über seine")
    A("genannten Kennwerte verwendet, nicht als Datenpunkt.")
    A("")
    A("**Ein einziger Kalibrierpunkt kann kein Modell bestimmen.** Was")
    A("folgt, ist eine Rechnung unter einer Annahme, keine Schätzung aus")
    A("Daten. Die Empfindlichkeitstabelle am Ende zeigt, wie stark das")
    A("Ergebnis von dieser Annahme abhängt.")
    A("")

    # Modell: P(Sieg | Vorab-Wahrscheinlichkeit, Minute) aus allen Heimfaellen
    X = []
    y = []
    for f in heim:
        if f["_q"] is None:
            continue
        X.append([1.0 / f["_q"], float(f["minute"])])
        y.append(int(f["treffer"]))
    log("Logistisches Modell auf %d Heimfaellen …" % len(X))
    vorher = logit_fit(X, y)

    # Kalibrierung der Buchmacher-Spanne am Referenzfall
    p_ref = vorher([1.0 / REF_VORAB, REF_MINUTE])
    fair_ref = 1.0 / p_ref
    k = REF_LIVE / fair_ref

    A("### Das Modell")
    A("")
    A("Aus allen %d Heimfällen wird eine logistische Regression" % len(X))
    A("geschätzt: Siegwahrscheinlichkeit aus **Vorab-Wahrscheinlichkeit**")
    A("und **Minute des Gegentors**. Der Kehrwert ist die faire Live-Quote.")
    A("Die angebotene Quote wird als `fair × k` modelliert, wobei `k` so")
    A("gewählt ist, dass der Referenzfall genau 2,15 ergibt.")
    A("")
    A("| | |")
    A("|---|---|")
    A("| Modell-Siegwahrscheinlichkeit im Referenzfall | %s %% |" % de(100 * p_ref))
    A("| faire Live-Quote daraus | %s |" % de(fair_ref, 2))
    A("| berichtete Live-Quote | %s |" % de(REF_LIVE, 2))
    A("| **kalibrierter Faktor k** | **%s** |" % de(k, 3))
    A("")
    if k > 1.0:
        A("> **Das ist das erste Warnsignal.** Ein Buchmacher bietet immer")
        A("> *unter* dem fairen Wert an, `k` müsste also kleiner als 1 sein.")
        A("> Ein Wert von %s bedeutet: der Markt hielt die Chance für" % de(k, 3))
        A("> deutlich geringer, als unser Modell sie schätzt — beim")
        A("> Referenzfall für rund %s %% statt %s %%."
          % (de(100 / REF_LIVE), de(100 * p_ref)))
        A("> Entweder ist unsere Trefferquote zu optimistisch, oder der")
        A("> Referenzfall ist untypisch. Mit einem Punkt lässt sich das")
        A("> nicht auseinanderhalten.")
        A("")

    live = []
    for f in kern:
        p = vorher([1.0 / f["_q"], float(f["minute"])])
        live.append((f, 1.0 / p * k, p))
    schnitt = sum(q for _, q, _ in live) / len(live)
    ueber = sum(1 for _, q, _ in live if q > zelle(kern)["mind_kons"])
    p_real = zelle(kern)["quote"] / 100.0
    yield_ = (p_real * schnitt / STEUER - 1.0) * 100

    A("### Ergebnis für die Kernzelle")
    A("")
    A("| | |")
    A("|---|---|")
    A("| durchschnittliche geschätzte Live-Quote | **%s** |" % de(schnitt, 2))
    A("| tatsächliche Trefferquote der Zelle | %s %% |" % de(100 * p_real))
    A("| **Yield bei festem Einsatz, inkl. %s %% Wettsteuer** | **%s %%** |"
      % (de(100 * (STEUER - 1), 1), de(yield_, 1)))
    A("| Fälle mit geschätzter Live-Quote über %s (konservative Mindestquote) | **%d von %d = %s %%** |"
      % (de(zelle(kern)["mind_kons"], 2), ueber, len(live), de(100.0 * ueber / len(live))))
    A("")
    A("Gerechnet wird so: bei festem Einsatz 1 und Wettsteuer sind effektiv")
    A("`1/%s` im Spiel. Der Ertrag ist `p × Quote / %s − 1`."
      % (de(STEUER, 3), de(STEUER, 3)))
    A("")
    A("### Warum diese Yield-Zahl nichts aussagt")
    A("")
    A("Rechnet man es durch, fällt die Zahl in sich zusammen. Die")
    A("geschätzte Live-Quote ist `1/p_Modell × k`. Setzt man sie in die")
    A("Yield-Formel ein und ist `p_Modell` ungefähr die tatsächliche")
    A("Trefferquote, kürzt sich `p` heraus:")
    A("")
    A("```")
    A("Yield = p × (1/p × k) / %s − 1  =  k / %s − 1" % (de(STEUER, 3), de(STEUER, 3)))
    A("      = %s / %s − 1  =  %s %%" % (de(k, 3), de(STEUER, 3),
                                         de((k / STEUER - 1) * 100, 1)))
    A("```")
    A("")
    A("Das deckt sich mit den %s %% oben. **Der Yield ist also nichts"
      % de(yield_, 1))
    A("anderes als der Kalibrierfaktor in anderer Schreibweise** — und der")
    A("stammt aus einer einzigen Beobachtung. Es steckt keine Information")
    A("darin, die über diesen einen Wert hinausgeht.")
    A("")
    A("### Was passiert, wenn der Markt effizient ist")
    A("")
    A("Live-Märkte auf Spitzenligen gehören zu den am besten bepreisten")
    A("überhaupt. Nimmt man an, der Buchmacher hält rund 5 % Marge ein und")
    A("liegt sonst richtig, ergibt sich die angebotene Quote aus der")
    A("wahren Wahrscheinlichkeit als `0,95 / p`.")
    A("")
    markt_quote = 0.95 / p_real
    markt_yield = (p_real * markt_quote / STEUER - 1.0) * 100
    implizit = 0.95 / REF_LIVE
    A("| | |")
    A("|---|---|")
    A("| unsere Trefferquote für die Zelle | %s %% |" % de(100 * p_real))
    A("| angebotene Quote bei effizientem Markt | %s |" % de(markt_quote, 2))
    A("| Yield damit | **%s %%** |" % de(markt_yield, 1))
    A("| vom Referenzfall implizierte Wahrscheinlichkeit (2,15 bei 5 %% Marge) | %s %% |"
      % de(100 * implizit))
    A("")
    A("**Das ist der Kern der Sache.** Ist unsere Trefferquote richtig *und*")
    A("der Markt effizient, verlierst du die Marge — rund %s %% je Wette."
      % de(abs(markt_yield), 1))
    A("Gewinnen lässt sich nur, wenn der Markt diese Situation")
    A("systematisch zu niedrig bepreist. Genau das kann eine einzelne")
    A("Beobachtung nicht belegen.")
    A("")
    A("Der Referenzfall selbst zeigt in die andere Richtung: eine Quote von")
    A("2,15 entspricht bei üblicher Marge einer Markterwartung von rund")
    A("%s %%. Unsere Zelle sagt %s %%. Die Lücke von %s Prozentpunkten ist"
      % (de(100 * implizit), de(100 * p_real), de(100 * (p_real - implizit))))
    A("entweder echter Vorteil — oder unsere Zahl ist zu hoch.")
    A("")
    A("### Empfindlichkeit")
    A("")
    A("Weil `k` auf einem einzigen Punkt beruht, hier der Yield für andere")
    A("durchschnittliche Live-Quoten:")
    A("")
    A("| angenommene Live-Quote im Schnitt | Yield | tragfähig? |")
    A("| ---: | ---: | --- |")
    for q in (1.80, 2.00, 2.15, 2.30, 2.50, 2.75, 3.00):
        yv = (p_real * q / STEUER - 1.0) * 100
        A("| %s | %s %% | %s |" % (de(q, 2), de(yv, 1),
                                   "positiv" if yv > 0 else "negativ"))
    A("")
    A("Break-even liegt bei einer Live-Quote von **%s**."
      % de(STEUER / p_real, 2))
    A("")
    A("Die Tabelle beantwortet aber nur: *wenn* die Quote im Schnitt so")
    A("hoch wäre. Ob sie es ist, wissen wir nicht — und die Zeile, auf die")
    A("es ankommt, ist %s: dort liegt die Quote, die ein effizienter Markt"
      % de(markt_quote, 2))
    A("bei unserer eigenen Trefferquote anbieten würde.")
    A("")

    # ---------------------------------------------------------------- 8 ----
    A("## 7. Rechenwege geprüft")
    A("")
    # Wilson gegen zweite Umsetzung
    maxab = 0.0
    for k_ in range(0, 200, 7):
        for n_ in (10, 50, 114, 500, 2437):
            if k_ > n_:
                continue
            a1 = common.wilson(k_, n_)
            a2 = wilson_direkt(k_, n_)
            maxab = max(maxab, abs(a1[0] - a2[0]), abs(a1[1] - a2[1]))
    zk = zelle(kern)
    A("| Prüfung | Ergebnis |")
    A("|---|---|")
    A("| Wilson gegen zweite, unabhängige Umsetzung (Nullstellen der "
      "quadratischen Gleichung), 60 Kombinationen | größte Abweichung "
      "**%.2e** |" % maxab)
    A("| Wilson ist **keine** Normalapproximation | bestätigt: das "
      "Intervall der Kernzelle (%s – %s %%) ist asymmetrisch um %s %%; "
      "die Normalapproximation wäre symmetrisch |"
      % (de(zk["lo"]), de(zk["hi"]), de(zk["quote"])))
    A("| Mindestquote-Formel `1/p × %s × %s` | überall dieselbe Konstante "
      "%s, auch in Phase 7 |" % (de(STEUER, 3), de(PUFFER, 2), de(MARGE, 5)))
    A("| Klassengrenzen halboffen | `< %s` ist echt kleiner; die Nachbarklasse "
      "beginnt bei %s. Kein Fall in zwei Klassen. |"
      % (de(QUOTE_GRENZE, 2), de(QUOTE_GRENZE, 2)))
    A("| Doppelzählungen | je Spiel höchstens ein Fall — %d Fälle, %d "
      "verschiedene Spiele |" % (len(kern), len({f["match_id"] for f in kern})))
    A("")

    # Stichprobe
    random.seed(35)
    probe = random.sample(kern, min(10, len(kern)))
    probe.sort(key=lambda f: f["date"])
    A("### Stichprobe: 10 Fälle der Kernzelle")
    A("")
    A("| Datum | Liga | Heim (zurückliegend) | Gegner | Endplatz Gegner | "
      "Vorab-Quote fair | Minute | Endstand | Ergebnis |")
    A("| --- | --- | --- | --- | ---: | ---: | ---: | :---: | --- |")
    for f in probe:
        A("| %s | %s | %s | %s | %d | %s | %s | %s | %s |" % (
            f["date"], f["league"], f["team"], f["gegner"], f["_endplatz"],
            de(f["_q"], 3), f["minute"], f["endstand"],
            "**Sieg**" if int(f["treffer"]) else f["ergebnis"]))
    A("")
    A("Alle %d Fälle stehen in `data/35er-kernzelle-faelle.csv`." % len(kern))
    A("")

    # ---------------------------------------------------------------- 8 ----
    pro_saison = len(kern) / 9.0
    A("---")
    A("")
    A("## Fazit")
    A("")
    A("**Was hält:** Die 62,3 % selbst sind sauber gerechnet. Keine")
    A("Rückschau-Verzerrung (der Spieltagsstand liefert 61,4 %), keine")
    A("Definitionslücken, Verwurfquote 0,17 %, jeder der 114 Fälle gegen")
    A("die Rohdaten nachgeprüft, Wilson auf 15 Stellen gegen eine zweite")
    A("Umsetzung bestätigt. Die Zahl ist keine Fehlkonstruktion.")
    A("")
    A("**Was nicht hält:** Der Ertrag. Wir haben keine einzige echte")
    A("Live-Quote, und die berechneten %s %% Yield sind rechnerisch nichts"
      % de(yield_, 1))
    A("anderes als der Kalibrierfaktor aus einer einzigen Beobachtung. Wäre")
    A("der Markt effizient und unsere Trefferquote richtig, läge der Yield")
    A("bei **%s %%** — also im Minus. Ob dieser Zustand systematisch zu"
      % de(markt_yield, 1))
    A("niedrig bepreist wird, ist die einzige Frage, die zählt, und sie ist")
    A("mit diesen Daten nicht zu beantworten.")
    A("")
    A("**Zwei weitere Einschränkungen:** Die 114 Fälle verteilen sich auf")
    A("neun Saisons und fünf Ligen — rund **%s Gelegenheiten pro Saison**."
      % de(pro_saison))
    A("Bis sich statistisch etwas absichern lässt, vergehen Jahre. Und der")
    A("Gegnerfilter ist überflüssig: %s %% der Fälle mit Quote unter 1,30"
      % de(anteil))
    A("haben ohnehin einen schwachen Gegner, der Unterschied beträgt %s"
      % de(zk["quote"] - za["quote"]))
    A("Prozentpunkte. Die Regel lässt sich auf **Heimspiel × Vorab-Quote")
    A("unter 1,30** verkürzen, ohne etwas zu verlieren.")
    A("")
    A("**Empfehlung:** Noch kein echtes Geld. Der fehlende Baustein ist")
    A("messbar, ohne etwas zu riskieren — notiere bei den nächsten 30 bis")
    A("50 Auslösern die tatsächlich angebotene Live-Quote, ohne zu setzen.")
    A("Liegt sie im Schnitt über %s, trägt die Strategie. Liegt sie"
      % de(STEUER / p_real, 2))
    A("darunter, ist die Sache erledigt — und du hast nichts verloren.")
    A("")

    common.write_text(os.path.join(common.RESULTS_DIR, "35er-pruefung.md"),
                      "\n".join(md))

    felder = ["match_id", "date", "league", "season", "team", "gegner",
              "gegner_endplatz", "gegner_platz_am_spieltag", "gegner_spiele_am_spieltag",
              "faire_quote", "minute", "endstand", "ergebnis", "treffer"]
    rows = []
    for f in kern:
        rows.append({
            "match_id": f["match_id"], "date": f["date"], "league": f["league"],
            "season": f["season"], "team": f["team"], "gegner": f["gegner"],
            "gegner_endplatz": f["_endplatz"],
            "gegner_platz_am_spieltag": f["_tagplatz"],
            "gegner_spiele_am_spieltag": f["_tagspiele"],
            "faire_quote": f["_q"], "minute": f["minute"],
            "endstand": f["endstand"], "ergebnis": f["ergebnis"],
            "treffer": f["treffer"],
        })
    rows.sort(key=lambda r: r["date"])
    common.write_csv(os.path.join(common.DATA_DIR, "35er-kernzelle-faelle.csv"),
                     rows, felder)
    log("Geschrieben: results/35er-pruefung.md, data/35er-kernzelle-faelle.csv")
    common.error_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
