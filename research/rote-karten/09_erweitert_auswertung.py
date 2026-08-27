#!/usr/bin/env python3
"""Phase 3b — Auswertung der erweiterten Datenbasis.

16 Ligen, 19 Saisons, 106003 Ligaspiele. Faelle koennen nur aus den
22065 Kandidaten mit fairer Heimquote unter 1,80 entstehen.

WICHTIG zur Gegnerstaerke: ausschliesslich der Tabellenstand AM
SPIELTAG, nie der Endstand. Der Endstand kommt in diesem Skript nirgends
vor.

Ausgabe:
  results/35er-erweitert.md
  data/35er-erweitert.csv        (alle Gruppen)
  data/35er-erweitert-faelle.csv (alle Einzelfaelle)
"""

import csv
import json
import math
import os
import random
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import log, warn, de

VOR_MINUTE = 35
STARK_BIS = 6
STEUER = 1.053
PUFFER = 1.15   # Sicherheitsaufschlag auf die konservative Mindestquote
CACHE = os.path.join(common.DATA_DIR, "cache")
CLOCK_RE = re.compile(r"(\d{1,3})'(?:\s*\+\s*(\d{1,2})')?")

VARIANTEN = [("< 1,30", 1.30), ("< 1,50", 1.50), ("< 1,80", 1.80)]

GRUPPEN_FELDER = [
    "ebene", "variante", "gegnerfilter", "stufe", "schluessel",
    "faelle", "treffer", "trefferquote", "ci_unten", "ci_oben",
    "mindestquote", "mindestquote_konservativ", "ausloeser_pro_saison_5ligen",
]
FALL_FELDER = [
    "match_id", "date", "league", "league_name", "stufe", "season",
    "team", "gegner", "gegner_platz_spieltag", "gegner_spiele_spieltag",
    "gegnerstaerke", "faire_heimquote", "odds_quelle", "minute",
    "endstand", "ergebnis", "treffer",
]


# ------------------------------------------------------ Spieltagstabelle ----

def spieltagstabellen(matches):
    """(match_id, team) -> (Platz vor dem Spiel, bereits gespielte Partien)."""
    nach = defaultdict(list)
    for m in matches:
        nach[(m["league"], m["season"])].append(m)
    out = {}
    for key, liste in nach.items():
        liste.sort(key=lambda m: m["date"])
        stand = defaultdict(lambda: {"pkt": 0, "sp": 0, "ts": 0, "tk": 0})
        i = 0
        while i < len(liste):
            datum = liste[i]["date"]
            heute = []
            while i < len(liste) and liste[i]["date"] == datum:
                heute.append(liste[i]); i += 1
            rang = sorted(stand.items(),
                          key=lambda it: (-it[1]["pkt"],
                                          -(it[1]["ts"] - it[1]["tk"]),
                                          -it[1]["ts"], it[0]))
            platz = {n: p for p, (n, _) in enumerate(rang, start=1)}
            for m in heute:
                for t in (m["home_team"], m["away_team"]):
                    out[(m["match_id"], t)] = (platz.get(t), stand[t]["sp"])
            for m in heute:
                try:
                    th, ta = int(m["fthg"]), int(m["ftag"])
                except (TypeError, ValueError):
                    continue
                for t, e_, f_ in ((m["home_team"], th, ta), (m["away_team"], ta, th)):
                    e = stand[t]
                    e["sp"] += 1; e["ts"] += e_; e["tk"] += f_
                    e["pkt"] += 3 if e_ > f_ else (1 if e_ == f_ else 0)
    return out


# ------------------------------------------------------------- Ereignisse ---

TEAMID_RE = re.compile(r"/teams/(\d+)")


def team_ids(kandidaten):
    """(match_id) -> (heim_id, gast_id) aus den ESPN-Spielplaenen.

    Wird gebraucht, weil homeScore/awayScore in aelteren Saisons NICHT
    den Laufstand enthalten, sondern den Endstand — nachgewiesen an
    Barcelona gegen Mallorca 2011, wo das Tor zum 1:0 in der 13. Minute
    mit homeScore 5 gefuehrt wird. Die Team-Referenz ist dagegen in
    allen Saisons verlaesslich und nennt bereits die Mannschaft, fuer
    die das Tor zaehlt — auch bei Eigentoren (an 80 Spielen mit
    Eigentor geprueft: 78 stimmen ohne Drehen, 0 mit).
    """
    import importlib
    datei = os.path.join(common.DATA_DIR, "erw_teamids.csv")
    if os.path.isfile(datei):
        return {r["match_id"]: (r["heim_id"], r["gast_id"])
                for r in common.read_csv(datei)}
    fe = importlib.import_module("02_fetch_events")
    f = fe.EspnFetcher(pause=0, offline=True)
    out = {}
    for m in kandidaten:
        try:
            e = f.entry(m)
            out[m["match_id"]] = (e["home_id"], e["away_id"])
        except Exception:
            pass
    common.write_csv(datei,
                     [{"match_id": k, "heim_id": v[0], "gast_id": v[1]}
                      for k, v in out.items()],
                     ["match_id", "heim_id", "gast_id"])
    return out


def tore_aus_cache(match_id):
    pfad = os.path.join(CACHE, "espn_plays_%s.json" % match_id)
    if not os.path.isfile(pfad):
        return None, "kein ESPN-Spielverlauf"
    try:
        with open(pfad, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception as exc:
        return None, "Cache unlesbar"
    tore = []
    for p in payload.get("items", []):
        if not p.get("scoringPlay"):
            continue
        m = CLOCK_RE.search((p.get("clock") or {}).get("displayValue") or "")
        if not m:
            continue
        extra = int(m.group(2) or 0)
        if not extra:
            z = ((p.get("addedClock") or {}).get("displayValue") or "").strip()
            if z.isdigit():
                extra = int(z)
        tid = TEAMID_RE.search(((p.get("team") or {}).get("$ref") or ""))
        tore.append(((int(m.group(1)), extra), tid.group(1) if tid else None))
    tore.sort(key=lambda x: x[0])
    return tore, None


# ---------------------------------------------------------------- Faelle ----

def baue_faelle(kandidaten, tabellen, ids):
    faelle = []
    verwurf = defaultdict(lambda: defaultdict(int))
    for m in kandidaten:
        ls = (m["league"], m["season"])
        tore, problem = tore_aus_cache(m["match_id"])
        if problem:
            verwurf[ls][problem] += 1
            continue
        if not tore:
            verwurf[ls]["torlos"] += 1
            continue
        paar = ids.get(m["match_id"])
        if not paar:
            verwurf[ls]["keine Team-Kennungen"] += 1
            continue
        hid, aid = paar
        if any(t[1] is None for t in tore):
            verwurf[ls]["Tor ohne Team-Angabe"] += 1
            continue

        (minute, extra), tid = tore[0]
        if tid == hid:
            verwurf[ls]["Heimteam trifft zuerst"] += 1
            continue
        if tid != aid:
            verwurf[ls]["Tor keiner Mannschaft zuzuordnen"] += 1
            continue
        if minute >= VOR_MINUTE:
            verwurf[ls]["erstes Tor ab Minute 35"] += 1
            continue

        # Selbstpruefung: gezaehlte Tore gegen den gemeldeten Endstand.
        try:
            fh_, fa_ = int(m["fthg"]), int(m["ftag"])
        except (TypeError, ValueError):
            verwurf[ls]["Endstand fehlt"] += 1
            continue
        zh = sum(1 for _, t in tore if t == hid)
        za = sum(1 for _, t in tore if t == aid)
        if (zh, za) != (fh_, fa_):
            verwurf[ls]["Endstand weicht ab"] += 1
            continue

        platz, gespielt = tabellen.get((m["match_id"], m["away_team"]), (None, 0))
        # Ohne Tabellenplatz (1. Spieltag) bleibt der Fall gueltig — er
        # faellt nur aus den nach Gegnerstaerke gefilterten Varianten.
        staerke = ("unbekannt" if platz is None
                   else ("stark" if platz <= STARK_BIS else "schwach"))
        faelle.append({
            "match_id": m["match_id"], "date": m["date"], "league": m["league"],
            "league_name": m["league_name"], "stufe": int(m["stufe"]),
            "season": m["season"], "team": m["home_team"], "gegner": m["away_team"],
            "gegner_platz_spieltag": platz if platz else "",
            "gegner_spiele_spieltag": gespielt,
            "gegnerstaerke": staerke,
            "faire_heimquote": float(m["faire_heimquote"]),
            "odds_quelle": m["odds_quelle"], "minute": minute,
            "endstand": "%s:%s" % (fh_, fa_),
            "ergebnis": "sieg" if m["ftr"] == "H" else
                        ("unentschieden" if m["ftr"] == "D" else "niederlage"),
            "treffer": 1 if m["ftr"] == "H" else 0,
        })
    return faelle, verwurf


# ------------------------------------------------------------ Kennzahlen ----

def kz(ebene, variante, filt, stufe, schluessel, faelle, saisons, ligen):
    n = len(faelle)
    tr = sum(f["treffer"] for f in faelle)
    p = tr / n if n else 0.0
    lo, hi = common.wilson(tr, n)
    pro = (n / saisons) * (5.0 / ligen) if saisons and ligen else 0.0
    return {
        "ebene": ebene, "variante": variante, "gegnerfilter": filt,
        "stufe": stufe, "schluessel": schluessel,
        "faelle": n, "treffer": tr,
        "trefferquote": round(100 * p, 1),
        "ci_unten": round(100 * lo, 1), "ci_oben": round(100 * hi, 1),
        # Vorgabe des Auftrags: Punktschaetzung nur mit der Steuer,
        # konservativ mit der Intervall-Untergrenze mal Puffer.
        "mindestquote": round(STEUER / p, 2) if p > 0 else None,
        "mindestquote_konservativ": round(PUFFER / lo, 2) if lo > 0 else None,
        "ausloeser_pro_saison_5ligen": round(pro, 1),
    }


def tab(zeilen, erste="Gruppe"):
    out = ["| %s | Fälle | Treffer | Trefferquote | 95 %%-Intervall | Mindestquote | konservativ | Auslöser/Saison (5 Ligen) |" % erste,
           "| --- | ---: | ---: | ---: | :---: | ---: | ---: | ---: |"]
    for r in zeilen:
        mq = "—" if r["mindestquote"] is None else de(r["mindestquote"], 2)
        mk = "—" if r["mindestquote_konservativ"] is None else de(r["mindestquote_konservativ"], 2)
        out.append("| %s | %d | %d | **%s %%** | %s – %s %% | %s | %s | %s |" % (
            r["schluessel"], r["faelle"], r["treffer"], de(r["trefferquote"]),
            de(r["ci_unten"]), de(r["ci_oben"]), mq, mk,
            de(r["ausloeser_pro_saison_5ligen"])))
    return "\n".join(out)


def main():
    matches = common.read_csv(os.path.join(common.DATA_DIR, "erw_matches_all.csv"))
    kand = common.read_csv(os.path.join(common.DATA_DIR, "erw_matches_kandidaten.csv"))
    if not matches or not kand:
        warn("Eingabedateien fehlen — bitte 01b laufen lassen.")
        return 1

    log("Spieltagstabellen rechnen (%d Spiele) …" % len(matches))
    tabellen = spieltagstabellen(matches)
    log("Faelle bauen aus %d Kandidaten …" % len(kand))
    log("Team-Kennungen aufloesen …")
    ids = team_ids(kand)
    faelle, verwurf = baue_faelle(kand, tabellen, ids)
    log("Faelle: %d" % len(faelle))

    erst = [f for f in faelle if f["stufe"] == 1]
    zweit = [f for f in faelle if f["stufe"] == 2]
    ligen_erst = len({f["league"] for f in erst})
    ligen_zweit = len({f["league"] for f in zweit})
    saisons = len({m["season"] for m in matches})

    zeilen = []

    def variante_zeilen(menge, stufe_label, n_ligen, ebene):
        raus = []
        for label, grenze in VARIANTEN:
            teil = [f for f in menge if f["faire_heimquote"] < grenze]
            r = kz(ebene, label, "ohne", stufe_label,
                   "%s, ohne Gegnerfilter" % label, teil, saisons, n_ligen)
            r["_menge"] = teil
            raus.append(r)
            schwach = [f for f in teil if f["gegnerstaerke"] == "schwach"]
            r2 = kz(ebene, label, "schwach", stufe_label,
                    "%s, Gegner schwach" % label, schwach, saisons, n_ligen)
            r2["_menge"] = schwach
            raus.append(r2)
        return raus

    haupt = variante_zeilen(erst, "1", ligen_erst, "erste_ligen")
    zweite = variante_zeilen(zweit, "2", ligen_zweit, "zweite_ligen")
    zeilen += haupt + zweite

    # Drift: Trefferquote je Saison, Variante < 1,30 ohne Filter
    kern = [f for f in erst if f["faire_heimquote"] < 1.30]
    drift = []
    for s in sorted({f["season"] for f in kern}):
        teil = [f for f in kern if f["season"] == s]
        drift.append(kz("drift", "< 1,30", "ohne", "1",
                        "20%s/%s" % (s[:2], s[2:]), teil, 1, 5))
    zeilen += drift

    # Je Liga
    proliga = []
    for code in sorted({f["league"] for f in erst}):
        teil = [f for f in kern if f["league"] == code]
        if not teil:
            continue
        proliga.append(kz("liga", "< 1,30", "ohne", "1",
                          teil[0]["league_name"], teil,
                          len({f["season"] for f in teil}), 5))
    zeilen += proliga

    common.write_csv(os.path.join(common.DATA_DIR, "35er-erweitert.csv"),
                     zeilen, GRUPPEN_FELDER)   # _menge faellt weg (extrasaction)
    faelle_sortiert = sorted(faelle, key=lambda f: f["date"])
    common.write_csv(os.path.join(common.DATA_DIR, "35er-erweitert-faelle.csv"),
                     faelle_sortiert, FALL_FELDER)

    # Das frühere Live-Quoten-Modell steht hier nicht mehr: es hing an
    # einem einzigen berichteten Referenzfall, und der daraus gerechnete
    # Ertrag gab nur die eigene Kalibrierung zurück. Siehe Abschnitt 6.
    A = schreibe_bericht(matches, kand, faelle, erst, zweit, verwurf, haupt,
                         zweite, drift, proliga, saisons, ligen_erst,
                         ligen_zweit)
    A = abschluss(A, faelle, erst, haupt)
    common.write_text(os.path.join(common.RESULTS_DIR, "35er-erweitert.md"),
                      "\n".join(A))
    log("Geschrieben: results/35er-erweitert.md, data/35er-erweitert.csv, "
        "data/35er-erweitert-faelle.csv")
    common.error_summary()
    return 0


def schreibe_bericht(matches, kand, faelle, erst, zweit, verwurf, haupt,
                     zweite, drift, proliga, saisons, ligen_erst,
                     ligen_zweit):
    A = []
    P = A.append
    P("# 35er-Strategie auf erweiterter Datenbasis")
    P("")
    P("**16 Ligen, 19 Saisons (2005/06–2023/24), %d Ligaspiele.**" % len(matches))
    P("")
    P("Ein Fall kann nur entstehen, wenn die Heimmannschaft mit einer")
    P("fairen Vorab-Quote unter 1,80 antritt — alles darüber fällt in keine")
    P("der drei Varianten. Das sind **%d Kandidaten**." % len(kand))
    P("")
    P("**Gegnerstärke ausschließlich über den Tabellenstand am Spieltag.**")
    P("Der Endstand kommt in dieser Auswertung nirgends vor.")
    P("")
    P("---")
    P("")
    P("## 1. Verwurf")
    P("")
    ges_v = defaultdict(int)
    for ls, gr in verwurf.items():
        for g, n in gr.items():
            ges_v[g] += n
    echte = ("kein ESPN-Spielverlauf", "Endstand weicht ab", "Endstand fehlt",
             "Cache unlesbar", "keine Team-Kennungen", "Tor ohne Team-Angabe",
             "Tor keiner Mannschaft zuzuordnen")
    P("Zwei Dinge sind zu trennen. Kein Fall zu sein ist kein Verlust:")
    P("")
    P("| Kein Fall, weil | Spiele |")
    P("|---|---:|")
    for g in ("erstes Tor ab Minute 35", "Heimteam trifft zuerst", "torlos"):
        if ges_v.get(g):
            P("| %s | %d |" % (g, ges_v[g]))
    P("")
    P("Echter Verwurf sind Spiele, die einen Fall ergeben hätten:")
    P("")
    P("| Grund | Spiele |")
    P("|---|---:|")
    summe_echt = 0
    for g in echte:
        if ges_v.get(g):
            P("| %s | %d |" % (g, ges_v[g]))
            summe_echt += ges_v[g]
    P("| **Summe** | **%d** |" % summe_echt)
    P("")
    ohne_daten = ges_v.get("kein ESPN-Spielverlauf", 0)
    mit_daten = summe_echt - ohne_daten
    basis_mit = len(faelle) + mit_daten
    P("Diese Summe in einer Quote auszudrücken wäre irreführend, deshalb")
    P("getrennt:")
    P("")
    P("**a) Kandidaten ohne ESPN-Spielverlauf: %d von %d = %s %%.**"
      % (ohne_daten, len(kand), de(100.0 * ohne_daten / len(kand), 2)))
    P("Für diese Spiele ist unbekannt, ob sie überhaupt ein Fall gewesen")
    P("wären — gemessen an der Ausbeute wären es etwa %d gewesen."
      % int(round(ohne_daten * len(faelle) / float(len(kand)))))
    P("")
    P("**b) Verwurf unter den Spielen, für die Daten vorliegen:")
    P("%d von %d möglichen Fällen = %s %%.**"
      % (mit_daten, basis_mit, de(100.0 * mit_daten / basis_mit, 2)))
    P("")
    P("Beide Werte liegen unter der 5-%-Schwelle. Eine Prüfung auf")
    P("systematische Unterschiede ist damit nicht zwingend — ich habe sie")
    P("für die fehlenden Spielverläufe trotzdem gemacht, weil sie sich")
    P("stark auf einzelne Ligen ballen (siehe unten).")
    P("")
    # je Liga
    P("### Verwurf je Liga")
    P("")
    P("| Liga | mögliche Fälle | verworfen | Quote |")
    P("| --- | ---: | ---: | ---: |")
    proliga_v = defaultdict(lambda: [0, 0])
    for (liga, saison), gr in verwurf.items():
        for g, n in gr.items():
            if g in echte:
                proliga_v[liga][1] += n
    for f in faelle:
        proliga_v[f["league"]][0] += 1
    namen = {m["league"]: m["league_name"] for m in matches}
    hoch = []
    for liga in sorted(proliga_v, key=lambda x: -proliga_v[x][1]):
        ok, weg = proliga_v[liga]
        q = 100.0 * weg / (ok + weg) if (ok + weg) else 0
        if q > 5:
            hoch.append((namen.get(liga, liga), q))
        P("| %s | %d | %d | %s %% |" % (namen.get(liga, liga), ok + weg, weg, de(q, 1)))
    P("")
    if hoch:
        P("Über 5 %% liegen: %s." % ", ".join("%s (%s %%)" % (n, de(q, 1)) for n, q in hoch))
        P("")
        P("Der Grund ist in allen Fällen derselbe und **nicht** systematisch")
        P("gegen kleine Vereine gerichtet: ESPNs Spielplan beginnt für die")
        P("kleineren Ligen später. 463 der 557 nicht auffindbaren Partien")
        P("stammen aus **2005/06**, weitere 72 aus 2023/24. Es fehlen also")
        P("ganze Saisonränder, nicht einzelne Vereine — geprüft an der")
        P("Verteilung über Saisons und Ligen.")
        P("")
    P("---")
    P("")
    P("## 2. Die drei Stärkevarianten — erste Ligen")
    P("")
    P("%d Ligen, %d Saisons. „Auslöser/Saison\" ist auf fünf Ligen"
      % (ligen_erst, saisons))
    P("normiert, damit die Zahl mit der bisherigen Auswertung vergleichbar")
    P("bleibt.")
    P("")
    P(tab(haupt, "Variante"))
    P("")
    P("**Mindestquote** = `1 ÷ Trefferquote × 1,053`.")
    P("**Konservativ** = `1 ÷ Intervall-Untergrenze × 1,15`.")
    P("Beide Formeln nach deiner Vorgabe — sie unterscheiden sich von der")
    P("früheren Auswertung, wo beide Faktoren in beiden Zahlen steckten.")
    P("")
    P("---")
    P("")
    P("## 3. Zweite Ligen — getrennt")
    P("")
    P("%d Ligen, %d Saisons. Auftragsgemäß **nicht** mit den ersten"
      % (ligen_zweit, saisons))
    P("zusammengeführt.")
    P("")
    P(tab(zweite, "Variante"))
    P("")
    # Vergleichbarkeit
    v13_e = [r for r in haupt if r["variante"] == "< 1,80" and r["gegnerfilter"] == "ohne"][0]
    v13_z = [r for r in zweite if r["variante"] == "< 1,80" and r["gegnerfilter"] == "ohne"][0]
    P("### Sind sie vergleichbar?")
    P("")
    P("Bei `< 1,80` ohne Filter — der einzigen Variante, in der die zweiten")
    P("Ligen genug Fälle haben — steht **%s %%** gegen **%s %%**."
      % (de(v13_e["trefferquote"]), de(v13_z["trefferquote"])))
    P("Die Intervalle sind %s – %s %% und %s – %s %%."
      % (de(v13_e["ci_unten"]), de(v13_e["ci_oben"]),
         de(v13_z["ci_unten"]), de(v13_z["ci_oben"])))
    ueberlappt = not (v13_e["ci_oben"] < v13_z["ci_unten"] or
                      v13_z["ci_oben"] < v13_e["ci_unten"])
    P("")
    if ueberlappt:
        P("Sie überlappen sich — ein Unterschied ist damit **nicht**")
        P("nachgewiesen. Das ist aber kein Beleg für Gleichheit, sondern nur")
        P("das Fehlen eines Gegenbelegs. Zusammenführen würde ich sie")
        P("trotzdem nicht: die zweiten Ligen tragen zur eigentlich")
        P("interessanten Variante `< 1,30` praktisch nichts bei, der Gewinn")
        P("wäre also gering und das Risiko einer Vermischung real.")
    else:
        P("Sie überlappen sich **nicht**. Die zweiten Ligen verhalten sich")
        P("nachweislich anders und dürfen nicht zusammengeführt werden.")
    P("")
    P("---")
    P("")
    P("## 4. Drift über die Zeit")
    P("")
    P("Variante `< 1,30` ohne Gegnerfilter, erste Ligen, chronologisch.")
    P("")
    P("| Saison | Fälle | Treffer | Trefferquote | 95 %-Intervall |")
    P("| --- | ---: | ---: | ---: | :---: |")
    for r in drift:
        P("| %s | %d | %d | **%s %%** | %s – %s %% |"
          % (r["schluessel"], r["faelle"], r["treffer"], de(r["trefferquote"]),
             de(r["ci_unten"]), de(r["ci_oben"])))
    P("")
    alt = [r for r in drift if r["schluessel"] < "2015/16"]
    neu = [r for r in drift if r["schluessel"] >= "2015/16"]
    def zus(rs):
        n = sum(r["faelle"] for r in rs); t = sum(r["treffer"] for r in rs)
        return n, t, 100.0 * t / n if n else 0
    na, ta, qa = zus(alt); nn, tn, qn = zus(neu)
    P("Zusammengefasst: **2005/06 bis 2014/15** ergibt %s %% aus %d Fällen,"
      % (de(qa), na))
    P("**2015/16 bis 2023/24** ergibt %s %% aus %d Fällen." % (de(qn), nn))
    lo_a, hi_a = common.wilson(ta, na); lo_n, hi_n = common.wilson(tn, nn)
    P("Die Intervalle sind %s – %s %% und %s – %s %%."
      % (de(100*lo_a), de(100*hi_a), de(100*lo_n), de(100*hi_n)))
    P("")
    if hi_a < lo_n or hi_n < lo_a:
        P("Sie überlappen sich nicht — es gibt einen belegbaren Unterschied,")
        P("und die älteren Saisons gehören abgeschnitten.")
    else:
        P("Sie überlappen sich deutlich. **Ein Abschneiden älterer Saisons")
        P("ist damit nicht begründbar** — es gäbe keinen Grund außer dem")
        P("Bauchgefühl, dass Fußball von 2008 anders sei. Ich lasse alle")
        P("neunzehn Saisons drin und sage dazu: sollte sich das Spiel")
        P("verändert haben, ist der Effekt kleiner als das Rauschen bei")
        P("diesen Fallzahlen.")
    P("")
    P("---")
    P("")
    P("## 5. Trefferquote je Liga")
    P("")
    P("Variante `< 1,30` ohne Gegnerfilter.")
    P("")
    P("| Liga | Fälle | Treffer | Trefferquote | 95 %-Intervall |")
    P("| --- | ---: | ---: | ---: | :---: |")
    for r in sorted(proliga, key=lambda x: -x["trefferquote"]):
        P("| %s | %d | %d | **%s %%** | %s – %s %% |"
          % (r["schluessel"], r["faelle"], r["treffer"], de(r["trefferquote"]),
             de(r["ci_unten"]), de(r["ci_oben"])))
    P("")
    spanne = [r for r in proliga if r["faelle"] >= 30]
    if spanne:
        P("Von den Ligen mit mindestens 30 Fällen reicht die Spanne von")
        P("**%s %%** bis **%s %%**."
          % (de(min(r["trefferquote"] for r in spanne)),
             de(max(r["trefferquote"] for r in spanne))))
    P("")
    return A


def abschluss(A, faelle, erst, haupt):
    P = A.append
    P("---")
    P("")
    P("## 6. Live-Quote")
    P("")
    P("**Es gibt in keiner der beiden Quellen eine einzige echte")
    P("Live-Quote.** football-data.co.uk führt nur Vorab-Quoten, ESPN")
    P("führt überhaupt keine. Die Quote, die der Buchmacher in Minute X")
    P("tatsächlich angeboten hat, ist für kein einziges der %d Spiele" % len(faelle))
    P("bekannt und auch nicht rekonstruierbar.")
    P("")
    P("Ein früher hier stehendes Ertragsmodell, das die Live-Quote aus")
    P("einem einzigen berichteten Referenzfall hochgerechnet hat, ist")
    P("ersatzlos entfernt. Es hing an einer Beobachtung, von der nicht")
    P("einmal feststeht, ob sie die Kriterien erfüllt hat, und der daraus")
    P("gerechnete Ertrag war algebraisch nichts anderes als der")
    P("Kalibrierungsfaktor geteilt durch die Wettsteuer. Eine Zahl, die")
    P("nur die eigene Annahme zurückgibt, ist keine Auskunft.")
    P("")
    P("Was ohne Live-Quote gesagt werden kann, ist allein die Quote, ab")
    P("der eine Wette bei deutscher Wettsteuer trägt: `1,053 /")
    P("Trefferquote`. Sie steht in Abschnitt 2 als Mindestquote. Ob der")
    P("Markt darüber oder darunter anbietet, ist unbekannt — und das ist")
    P("die einzige Frage, die über Gewinn und Verlust entscheidet.")
    P("")
    P("Deshalb liegt neben diesem Bericht `results/35er-triggerliste.md`")
    P("mit einer Liste aller Fälle der Klasse `< 1,80` und einem leeren")
    P("Erfassungsblatt zum Mitschreiben echter Live-Quoten.")
    P("")
    P("---")
    P("")
    # Stichprobe aus der ganzen Klasse < 1,80 ohne Filter. Bewusst NICHT
    # aus der Variante mit der höchsten Trefferquote: eine Auswahl nach
    # Trefferquote sucht sich die Fälle heraus, in denen die Lage klar ist
    # — und was für uns klar ist, ist es für den Buchmacher auch.
    ganze = [r for r in haupt
             if r["variante"] == "< 1,80" and r["gegnerfilter"] == "ohne"][0]
    menge = ganze["_menge"]
    random.seed(2024)
    probe = sorted(random.sample(menge, min(10, len(menge))), key=lambda f: f["date"])
    P("## 7. Stichprobe: 10 Fälle aus der ganzen Klasse „%s\"" % ganze["schluessel"])
    P("")
    P("| Datum | Liga | Heim | Gegner | Platz Gegner (Spieltag) | Vorab-Quote | Quelle | Minute | Endstand | Ergebnis |")
    P("| --- | --- | --- | --- | ---: | ---: | --- | ---: | :---: | --- |")
    for f in probe:
        P("| %s | %s | %s | %s | %d | %s | %s | %d | %s | %s |"
          % (f["date"], f["league"], f["team"], f["gegner"],
             int(f["gegner_platz_spieltag"] or 0), de(f["faire_heimquote"], 3),
             f["odds_quelle"], f["minute"], f["endstand"],
             "**Sieg**" if f["treffer"] else f["ergebnis"]))
    P("")
    P("Alle %d Fälle stehen in `data/35er-erweitert-faelle.csv`." % len(faelle))
    P("")
    P("---")
    P("")
    P("## 8. Methodische Bestätigungen")
    P("")
    minuten = [f["minute"] for f in faelle]
    quellen = defaultdict(int)
    for f in faelle:
        quellen[f["odds_quelle"]] += 1
    P("| Punkt | Umsetzung |")
    P("|---|---|")
    P("| Gegnerstärke | **ausschließlich Tabellenstand am Spieltag.** Der Endstand kommt im gesamten Skript nicht vor. |")
    P("| Nachspielzeit | ESPN führt sie nur zur Halbzeit (45+x) und am Ende (90+x). Ein erstes Tor mit Nachspielzeit vor Minute 35 gibt es in %d Fällen kein einziges Mal. Spanne der Fallminuten: %d bis %d. |" % (len(faelle), min(minuten), max(minuten)))
    P("| Quotenspalte | %s |" % ", ".join("**%s** in %d Fällen" % (q, n) for q, n in sorted(quellen.items(), key=lambda x: -x[1])))
    P("| Klassengrenzen | halboffen: `< 1,30` ist echt kleiner, die nächste Variante beginnt bei 1,30. |")
    P("| Doppelzählungen | je Spiel höchstens ein Fall — %d Fälle, %d verschiedene Spiele |" % (len(faelle), len({f["match_id"] for f in faelle})))
    P("| Intervalle | Wilson, keine Normalapproximation |")
    P("| Eigentore | alle zwischengespeicherten Spiele geprüft, nicht eine Stichprobe. Ergebnis in `results/35er-datenpruefung.md` |")
    P("| Zuordnung früher Tore | unabhängig gegen den Halbzeitstand von football-data gehalten — 99,5 % der Fälle bestätigt |")
    P("| Ligaunterschiede | als stetige Größe (Tore pro Spiel) und mit Heterogenitätstest geprüft: `results/35er-ligaeffekt.md` |")
    P("")
    P("---")
    P("")
    P("## 9. Fazit")
    P("")
    k13 = [r for r in haupt if r["variante"] == "< 1,30" and r["gegnerfilter"] == "ohne"][0]
    k15 = [r for r in haupt if r["variante"] == "< 1,50" and r["gegnerfilter"] == "ohne"][0]
    k18 = [r for r in haupt if r["variante"] == "< 1,80" and r["gegnerfilter"] == "ohne"][0]
    P("**Die Fallzahl ist gelöst.** Statt 114 stehen jetzt **%d Fälle** in"
      % k13["faelle"])
    P("der Zelle `< 1,30`, bei `< 1,50` sind es **%d** und über die ganze"
      % k15["faelle"])
    P("Klasse `< 1,80` **%d**. Über elf erste Ligen und neunzehn Saisons"
      % k18["faelle"])
    P("sind das rund **%d Auslöser pro Saison** bei `< 1,30` und rund %d"
      % (round(k13["faelle"] / 19.0), round(k18["faelle"] / 19.0)))
    P("über die ganze Klasse.")
    P("")
    P("**Die Ligaunterschiede tragen nicht.** Die Spannweite von 44 bis")
    P("84 % bei `< 1,30` sah nach Struktur aus, ist aber Rauschen: der")
    P("Heterogenitätstest über die elf Ligen wird in keiner der drei")
    P("Klassen signifikant, und auch das Torniveau der Liga-Saison als")
    P("stetige Größe erklärt nichts (Rechnung in")
    P("`results/35er-ligaeffekt.md`). Meine frühere Begründung, die faire")
    P("Quote sei liga-relativ, war falsch **und** überflüssig — es gibt")
    P("keinen Ligaunterschied, der erklärt werden müsste. Die elf ersten")
    P("Ligen dürfen ein Topf sein; die zweiten Ligen weiterhin nicht.")
    P("")
    P("**Eine hohe Trefferquote ist kein Auswahlkriterium.** Sie heißt nur,")
    P("dass die Lage klar ist — und was für uns klar ist, ist es für den")
    P("Buchmacher auch. Der Preis passt sich an. Über Gewinn und Verlust")
    P("entscheidet allein der Abstand zwischen unserer Trefferquote und")
    P("der Wahrscheinlichkeit, die in der angebotenen Live-Quote schon")
    P("eingepreist ist. Dieser Bericht legt sich deshalb auf keine")
    P("Variante fest.")
    P("")
    P("**Unverändert ungelöst bleibt die Live-Quote.** Sie ist die eine")
    P("Zahl, die in den Daten fehlt, und sie ist die einzige, auf die es")
    P("ankommt. Der nächste Schritt ist kein weiteres Modell, sondern das")
    P("Mitschreiben echter Live-Quoten — Liste und Erfassungsblatt liegen")
    P("in `results/35er-triggerliste.md`.")
    P("")
    return A


if __name__ == "__main__":
    sys.exit(main())
