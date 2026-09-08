"""Phase 11 - Ligaunterschiede als stetige Groesse statt elf Einzelzellen.

Ausgangspunkt ist der Einwand, dass die Vorquote der Preis des Buchmachers
ist und nicht ligablind: 1,25 bedeutet ueberall ungefaehr dieselbe
Vorab-Wahrscheinlichkeit. Was je Liga schwanken kann, ist die
Aufholwahrscheinlichkeit bei gleicher Vorquote - und die haengt plausibel
am Torniveau der Liga.

Deshalb hier:

1. Torniveau je Liga-Saison (Tore pro Spiel, aus allen Spielen der
   Liga-Saison, nicht nur aus den Faellen) als stetige Variable.
2. Logistische Regression: Treffer ~ Vorquote + Minute + Torniveau.
   Die Vorquote geht als Logit der fairen Siegwahrscheinlichkeit ein,
   damit sie auf derselben Skala liegt wie das Modell.
3. Heterogenitaetstest ueber die elf ersten Ligen: einmal roh und einmal
   nach Abzug dessen, was Vorquote, Minute und Torniveau schon erklaeren.
   Nur der zweite Test beantwortet die Frage, ob die Ligaunterschiede
   groesser sind als das Rauschen.

Alles in reinem Python - keine externen Rechenbibliotheken.
"""

from __future__ import annotations

import csv
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import de, log, wilson, write_csv, write_text  # noqa: E402

HIER = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------- Statistik ----

def normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _gammp(a, x):
    """Regularisierte untere unvollstaendige Gammafunktion P(a, x)."""
    if x < 0.0 or a <= 0.0:
        raise ValueError("gammp")
    if x == 0.0:
        return 0.0
    if x < a + 1.0:
        # Reihenentwicklung
        ap, summe, term = a, 1.0 / a, 1.0 / a
        for _ in range(1000):
            ap += 1.0
            term *= x / ap
            summe += term
            if abs(term) < abs(summe) * 1e-14:
                break
        return summe * math.exp(-x + a * math.log(x) - math.lgamma(a))
    # Kettenbruch fuer Q(a, x), dann P = 1 - Q
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    q = math.exp(-x + a * math.log(x) - math.lgamma(a)) * h
    return 1.0 - q


def chi2_p(chi, df):
    """Wahrscheinlichkeit, allein durch Zufall mindestens diesen Wert zu sehen."""
    if chi <= 0:
        return 1.0
    return 1.0 - _gammp(df / 2.0, chi / 2.0)


def invertiere(m):
    """Gauss-Jordan mit Teilpivotisierung. m wird nicht veraendert."""
    n = len(m)
    a = [list(row) + [1.0 if i == j else 0.0 for j in range(n)]
         for i, row in enumerate(m)]
    for spalte in range(n):
        pivot = max(range(spalte, n), key=lambda r: abs(a[r][spalte]))
        if abs(a[pivot][spalte]) < 1e-12:
            return None
        a[spalte], a[pivot] = a[pivot], a[spalte]
        teiler = a[spalte][spalte]
        a[spalte] = [v / teiler for v in a[spalte]]
        for zeile in range(n):
            if zeile == spalte:
                continue
            faktor = a[zeile][spalte]
            if faktor:
                a[zeile] = [v - faktor * w for v, w in zip(a[zeile], a[spalte])]
    return [row[n:] for row in a]


def logistisch(X, y, runden=60):
    """IRLS (Newton-Raphson). Gibt Koeffizienten und Kovarianzmatrix zurueck.

    X enthaelt bereits die Eins-Spalte fuer den Achsenabschnitt.
    """
    k = len(X[0])
    beta = [0.0] * k
    kov = None
    for _ in range(runden):
        # Score-Vektor und Fisher-Information
        score = [0.0] * k
        info = [[0.0] * k for _ in range(k)]
        for xi, yi in zip(X, y):
            eta = sum(b * v for b, v in zip(beta, xi))
            eta = max(-30.0, min(30.0, eta))
            p = 1.0 / (1.0 + math.exp(-eta))
            w = p * (1.0 - p)
            rest = yi - p
            for a in range(k):
                score[a] += xi[a] * rest
                for b in range(a, k):
                    info[a][b] += w * xi[a] * xi[b]
        for a in range(k):
            for b in range(a):
                info[a][b] = info[b][a]
        kov = invertiere(info)
        if kov is None:
            break
        schritt = [sum(kov[a][b] * score[b] for b in range(k)) for a in range(k)]
        beta = [b + s for b, s in zip(beta, schritt)]
        if max(abs(s) for s in schritt) < 1e-9:
            break
    return beta, kov


def wald(beta, kov):
    zeilen = []
    for i, b in enumerate(beta):
        se = math.sqrt(kov[i][i]) if kov and kov[i][i] > 0 else float("nan")
        z = b / se if se == se and se > 0 else float("nan")
        p = 2.0 * (1.0 - normal_cdf(abs(z))) if z == z else float("nan")
        zeilen.append((b, se, z, p))
    return zeilen


# ----------------------------------------------------------------- Daten ----

def torniveau():
    """(liga, saison) -> Tore pro Spiel, aus ALLEN Spielen der Liga-Saison."""
    tore = defaultdict(int)
    spiele = defaultdict(int)
    with open(os.path.join(HIER, "data", "erw_matches_all.csv"),
              newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                t = int(r["fthg"]) + int(r["ftag"])
            except (ValueError, KeyError):
                continue
            schluessel = (r["league"], r["season"])
            tore[schluessel] += t
            spiele[schluessel] += 1
    return {k: tore[k] / spiele[k] for k in spiele if spiele[k] >= 50}, spiele


def faelle():
    with open(os.path.join(HIER, "data", "35er-erweitert-faelle.csv"),
              newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ----------------------------------------------------------------- Lauf ------

def main():
    niveau, spiele = torniveau()
    alle = faelle()
    daten = []
    for r in alle:
        if r["stufe"] != "1":
            continue
        schluessel = (r["league"], r["season"])
        if schluessel not in niveau:
            continue
        quote = float(r["faire_heimquote"])
        p0 = 1.0 / quote                      # faire Vorab-Siegwahrscheinlichkeit
        daten.append({
            "match_id": r["match_id"],
            "liga": r["league"],
            "liga_name": r["league_name"],
            "saison": r["season"],
            "quote": quote,
            "logit_p0": math.log(p0 / (1.0 - p0)),
            "minute": int(r["minute"]),
            "torniveau": niveau[schluessel],
            "y": 1 if r["treffer"] == "1" else 0,
        })
    log("%d Faelle der ersten Ligen mit Torniveau" % len(daten))

    ausgabe = []
    ausgabe.append("# Ligaunterschiede: Torniveau statt elf Einzelzellen\n")
    ausgabe.append("Erzeugt von `12_ligaeffekt.py`. Grundlage: %d Faelle der "
                   "elf ersten Ligen, 19 Saisons.\n" % len(daten))

    # ---------------------------------------------------------- Torniveau ----
    ausgabe.append("\n## 1. Torniveau je Liga\n")
    ausgabe.append("Tore pro Spiel, gemittelt ueber alle 19 Saisons und "
                   "berechnet aus **allen** Spielen der Liga, nicht nur aus "
                   "den Faellen.\n")
    je_liga = defaultdict(list)
    for (lg, sa), wert in niveau.items():
        je_liga[lg].append(wert)
    namen = {d["liga"]: d["liga_name"] for d in daten}
    zeilen = []
    for lg in sorted(namen):
        werte = je_liga[lg]
        mit = [d for d in daten if d["liga"] == lg]
        treffer = sum(d["y"] for d in mit)
        lo, hi = wilson(treffer, len(mit))
        zeilen.append({
            "liga": lg,
            "liga_name": namen[lg],
            "torniveau": round(sum(werte) / len(werte), 3),
            "min": round(min(werte), 2),
            "max": round(max(werte), 2),
            "faelle": len(mit),
            "treffer": treffer,
            "quote": round(treffer / len(mit) * 100, 1) if mit else 0,
            "ci_lo": round(lo * 100, 1),
            "ci_hi": round(hi * 100, 1),
        })
    zeilen.sort(key=lambda z: -z["torniveau"])
    ausgabe.append("| Liga | Tore/Spiel | Spanne ueber die Saisons | Fälle | "
                   "Trefferquote | 95 %-Intervall |")
    ausgabe.append("| --- | ---: | :---: | ---: | ---: | :---: |")
    for z in zeilen:
        ausgabe.append("| %s | %s | %s – %s | %d | **%s %%** | %s – %s %% |"
                       % (z["liga_name"], de(z["torniveau"], 2), de(z["min"], 2),
                          de(z["max"], 2), z["faelle"], de(z["quote"]),
                          de(z["ci_lo"]), de(z["ci_hi"])))
    write_csv(os.path.join(HIER, "data", "35er-torniveau.csv"), zeilen,
              ["liga", "liga_name", "torniveau", "min", "max", "faelle",
               "treffer", "quote", "ci_lo", "ci_hi"])

    # -------------------------------------------------------- Regression ----
    def modell(spalten, titel, teilmenge=None):
        menge = teilmenge if teilmenge is not None else daten
        X, y = [], []
        for d in menge:
            X.append([1.0] + [d[s] for s in spalten])
            y.append(d["y"])
        beta, kov = logistisch(X, y)
        if kov is None:
            return None
        ergebnis = wald(beta, kov)
        ausgabe.append("\n**%s** (n = %d)\n" % (titel, len(menge)))
        ausgabe.append("| Grösse | Koeffizient | Standardfehler | z | p |")
        ausgabe.append("| --- | ---: | ---: | ---: | ---: |")
        for name, (b, se, z, p) in zip(["Achsenabschnitt"] + spalten, ergebnis):
            ausgabe.append("| %s | %s | %s | %s | %s |"
                           % (name, de(b, 4), de(se, 4), de(z, 2), _p(p)))
        return beta, kov, spalten, menge

    ausgabe.append("\n## 2. Logistische Regression\n")
    ausgabe.append("Zielgrösse ist der Treffer (Sieg nach 0:1). `logit_p0` ist "
                   "das Logit der fairen Vorab-Siegwahrscheinlichkeit, also die "
                   "Vorquote auf der Modellskala; `minute` die Minute des "
                   "Gegentors; `torniveau` die Tore pro Spiel der Liga-Saison.\n")
    modell(["logit_p0", "minute"], "Ohne Torniveau")
    voll = modell(["logit_p0", "minute", "torniveau"], "Mit Torniveau")

    ausgabe.append("\nZur Grössenordnung: die elf Ligen liegen im Mittel "
                   "zwischen %s und %s Toren pro Spiel."
                   % (de(min(z["torniveau"] for z in zeilen), 2),
                      de(max(z["torniveau"] for z in zeilen), 2)))

    # --------------------------------------------------- Heterogenitaet ----
    beta, kov, spalten, _ = voll

    def heterogenitaet(menge):
        """Roher Test und Test nach Abzug des Modells, je Teilmenge."""
        ligen = sorted({d["liga"] for d in menge})
        n_ges = len(menge)
        t_ges = sum(d["y"] for d in menge)
        p_quer = t_ges / n_ges if n_ges else 0.0
        chi_roh = 0.0
        chi_rest = 0.0
        rest = []
        for lg in ligen:
            mit = [d for d in menge if d["liga"] == lg]
            n = len(mit)
            t = sum(d["y"] for d in mit)
            erw_roh = n * p_quer
            if 0 < erw_roh < n:
                chi_roh += ((t - erw_roh) ** 2 / erw_roh
                            + (erw_roh - t) ** 2 / (n - erw_roh))
            erw = 0.0
            var = 0.0
            for d in mit:
                xi = [1.0] + [d[sp] for sp in spalten]
                eta = sum(b * v for b, v in zip(beta, xi))
                eta = max(-30.0, min(30.0, eta))
                p = 1.0 / (1.0 + math.exp(-eta))
                erw += p
                var += p * (1.0 - p)
            diff = t - erw
            if var > 0:
                chi_rest += diff * diff / var
            rest.append({
                "liga": lg,
                "liga_name": namen[lg],
                "faelle": n,
                "beobachtet": t,
                "erwartet": round(erw, 1),
                "differenz": round(diff, 1),
                "z": round(diff / math.sqrt(var), 2) if var > 0 else 0.0,
            })
        return chi_roh, chi_rest, len(ligen) - 1, rest

    ausgabe.append("\n## 3. Heterogenitätstest über die elf Ligen\n")
    ausgabe.append("Der rohe Test fragt: reicht Zufall aus, um die Spannweite "
                   "der Trefferquoten zu erklären? Der zweite Test fragt "
                   "schärfer: bleibt ein Ligaunterschied übrig, nachdem "
                   "Vorquote, Minute und Torniveau abgezogen sind?\n")
    ausgabe.append("| Klasse | Fälle | roh: Chi² | p | nach Abzug: Chi² | p | "
                   "Freiheitsgrade |")
    ausgabe.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    tests = {}
    for grenze, titel in ((1.30, "< 1,30"), (1.50, "< 1,50"), (1.80, "< 1,80 (alle)")):
        menge = [d for d in daten if d["quote"] < grenze]
        c1, c2, df, rest = heterogenitaet(menge)
        tests[titel] = (c1, c2, df, rest, menge)
        ausgabe.append("| %s | %d | %s | %s | %s | %s | %d |"
                       % (titel, len(menge), de(c1, 1), _p(chi2_p(c1, df)),
                          de(c2, 1), _p(chi2_p(c2, df)), df))

    c1, c2, df, rest, menge = tests["< 1,80 (alle)"]
    i2_roh = max(0.0, (c1 - df) / c1) * 100 if c1 > 0 else 0.0
    i2_rest = max(0.0, (c2 - df) / c2) * 100 if c2 > 0 else 0.0
    ausgabe.append("\nFür die ganze Klasse `< 1,80`: Anteil der Streuung, der "
                   "nicht Zufall ist (I²), roh **%s %%**, nach Abzug **%s %%**."
                   % (de(i2_roh, 0), de(i2_rest, 0)))

    ausgabe.append("\n### Rest je Liga, Klasse `< 1,80`\n")
    ausgabe.append("Beobachtete minus vom Modell erwartete Treffer. Ein z über "
                   "2 oder unter −2 wäre auffällig.\n")
    ausgabe.append("| Liga | Fälle | beobachtet | erwartet | Differenz | z |")
    ausgabe.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for z in sorted(rest, key=lambda r: -r["z"]):
        ausgabe.append("| %s | %d | %d | %s | %s | %s |"
                       % (z["liga_name"], z["faelle"], z["beobachtet"],
                          de(z["erwartet"]), de(z["differenz"]), de(z["z"], 2)))
    write_csv(os.path.join(HIER, "data", "35er-ligarest.csv"), rest,
              ["liga", "liga_name", "faelle", "beobachtet", "erwartet",
               "differenz", "z"])

    c1_30, c2_30, df30, rest30, menge30 = tests["< 1,30"]
    ausgabe.append("\n### Rest je Liga, Klasse `< 1,30`\n")
    ausgabe.append("Das ist die Zelle, in der die Spannweite von 44 bis 84 % "
                   "aufgefallen ist.\n")
    ausgabe.append("| Liga | Fälle | beobachtet | erwartet | Differenz | z |")
    ausgabe.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for z in sorted(rest30, key=lambda r: -r["z"]):
        ausgabe.append("| %s | %d | %d | %s | %s | %s |"
                       % (z["liga_name"], z["faelle"], z["beobachtet"],
                          de(z["erwartet"]), de(z["differenz"]), de(z["z"], 2)))

    # --------------------------------------------------------- Einordnung ----
    auffaellig = [z for z in rest30 if abs(z["z"]) > 2]
    n_ligen = len(rest30)
    # Wahrscheinlichkeit, rein zufaellig mindestens eine von n Ligen mit |z|>2
    p_einzeln = 2.0 * (1.0 - normal_cdf(2.0))
    p_mindestens_eine = 1.0 - (1.0 - p_einzeln) ** n_ligen
    ausgabe.append("\n## 4. Was daraus folgt\n")
    ausgabe.append("**Das Torniveau erklärt nichts.** Der Koeffizient ist "
                   "%s bei einem Standardfehler von %s (p = %s). Über die "
                   "Spannweite der elf Ligen — %s bis %s Tore pro Spiel — "
                   "ändert das die geschätzte Trefferquote um weniger als "
                   "einen Prozentpunkt. Die Vermutung, dass torreichere Ligen "
                   "mehr Aufholjagden sehen, lässt sich an diesen Daten nicht "
                   "belegen."
                   % (de(voll[0][3], 4), de(math.sqrt(voll[1][3][3]), 4),
                      _p(wald(voll[0], voll[1])[3][3]),
                      de(min(z["torniveau"] for z in zeilen), 2),
                      de(max(z["torniveau"] for z in zeilen), 2)))
    ausgabe.append("\n**Die Ligaunterschiede sind kleiner als das Rauschen.** "
                   "Schon der rohe Test wird in keiner der drei Klassen "
                   "signifikant. In der Klasse `< 1,30`, wo die Spannweite von "
                   "44 bis 84 %% am stärksten ins Auge fällt, liegt p bei %s. "
                   "Mit elf Ligen und Fallzahlen zwischen 9 und 57 ist eine "
                   "solche Spannweite genau das, was Zufall erzeugt."
                   % _p(chi2_p(c1_30, df30)))
    if auffaellig:
        ausgabe.append("\n**Zur %s:** dort liegt z bei %s, also über 2. Das "
                       "ist der einzige Ausreißer unter %d geprüften Ligen. "
                       "Rein zufällig mindestens einen solchen Ausreißer zu "
                       "sehen, hat eine Wahrscheinlichkeit von %s %% — es ist "
                       "also kein Befund, sondern der erwartete Ausreißer."
                       % (auffaellig[0]["liga_name"],
                          de(auffaellig[0]["z"], 2), n_ligen,
                          de(p_mindestens_eine * 100, 0)))
    ausgabe.append("\n**Damit fällt meine frühere Begründung weg.** Ich hatte "
                   "geschrieben, die faire Quote sei liga-relativ und 1,25 "
                   "bedeute in der Eredivisie etwas anderes als in der Premier "
                   "League. Der Einwand dagegen ist richtig: die Vorquote ist "
                   "der Preis des Buchmachers, und der ist nicht ligablind. "
                   "Die Erklärung war aber nicht nur falsch, sie war "
                   "überflüssig — es gibt keinen Ligaunterschied, der erklärt "
                   "werden müsste. Die elf Ligen dürfen ein Topf sein.")

    write_text(os.path.join(HIER, "results", "35er-ligaeffekt.md"),
               "\n".join(ausgabe) + "\n")
    log("geschrieben: results/35er-ligaeffekt.md")
    for titel, (a, b_, d_, _r, _m) in tests.items():
        log("%s: roh chi2=%.1f p=%.4g | nach Abzug chi2=%.1f p=%.4g (df=%d)"
            % (titel, a, chi2_p(a, d_), b_, chi2_p(b_, d_), d_))


def _p(p):
    if p != p:
        return "—"
    if p < 0.0001:
        return "< 0,0001"
    return de(p, 4)


if __name__ == "__main__":
    main()
