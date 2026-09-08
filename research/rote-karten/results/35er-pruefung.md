# Überprüfung der 35er-Kernzelle

**Kernzelle:** Heimspiel × Gegner beendet die Saison auf Platz 7 oder
schlechter × faire Vorab-Quote des zurückliegenden Teams unter 1,30.

Auftragsgemäß **ohne** Minutenaufteilung.

---

## 1. Datenbasis

| | |
|---|---|
| Saisons | **9** — 2015/16, 2016/17, 2017/18, 2018/19, 2019/20, 2020/21, 2021/22, 2022/23, 2023/24 |
| Ligen | 5 — Premier League, La Liga, Bundesliga, Serie A, Ligue 1 |
| Zeitraum | 2015-08-07 bis 2024-06-02 |
| Ligaspiele geprüft | 16259 |
| 35er-Fälle | 9476 |
| davon Heimspiele | 4194 |
| Kernzelle | **114** |

Es sind **neun** Saisons, nicht fünf.

### Verwurf

Zwei Dinge sind zu trennen. Spiele **ohne Fall** sind kein Verlust —
dort existiert die Situation schlicht nicht:

- torlose Spiele: 1113
- erstes Tor ab Minute 35: 5654

Echter Verwurf sind nur Spiele, die einen Fall ergeben hätten:

| Grund | Fälle |
|---|---:|
| Endstand aus den Ereignissen passt nicht zum gemeldeten | 12 |
| Bet365-Quote fehlt | 4 |
| Gegner ohne Tabellenplatz | 0 |
| **Summe** | **16** |

**Verwurfquote: 16 von 9492 = 0,17 %.**

Das liegt weit unter 5 %, eine Prüfung auf systematische
Unterschiede erübrigt sich damit.

## 2. Definitionen

| Begriff | Umsetzung im Code |
|---|---|
| 0:1 vor Minute 35 | Das **erste Tor des Spiels** fällt in Minute 1 bis 34 und wird vom Gegner erzielt. Dass die betroffene Mannschaft bis dahin nicht getroffen hat, folgt zwingend daraus. |
| Nachspielzeit | ESPN führt Nachspielzeit nur zur Halbzeit (45+x) und am Ende (90+x). Ein erstes Tor mit Nachspielzeit-Angabe und Minute unter 35 kommt in den Daten **kein einziges Mal** vor; die Grenze ist also eindeutig. Tatsächliche Spanne der Fallminuten: 1 bis 34. |
| Treffer | Ausschließlich **Sieg nach 90 Minuten** (Spalte FTR = H bzw. A). Unentschieden zählt als Fehlschlag. Verlängerung gibt es in Ligaspielen nicht. |
| Vorab-Quote | **B365H / B365D / B365A** — die Schlussquoten von Bet365 aus football-data.co.uk. Daraus wird die Marge herausgerechnet (1/Quote je Ausgang, dann durch die Summe teilen); die faire Quote ist der Kehrwert. Fehlen die Werte, wird der Fall **ausgeschlossen**, nie ersetzt. Betroffen: 6 von 16259 Spielen. |
| Gegner schwach | **Endtabellenplatz 7 oder schlechter.** Das ist der Stand am Saisonende — also **Rückschau**, im Moment der Wette nicht verfügbar. Abschnitt 3 rechnet die Alternative. |

## 3. Rückschau-Verzerrung

Dieselbe Zelle noch einmal, aber „Gegner schwach" nach dem
**Tabellenstand am Spieltag** statt nach dem Endstand.

| Gruppe | Fälle | Treffer | Trefferquote | 95 %-Intervall | Mindestquote | konservativ |
| --- | ---: | ---: | ---: | :---: | ---: | ---: |
| Endstand (Rückschau) | 114 | 71 | **62,3 %** | 53,1 – 70,6 % | 1,94 | 2,28 |
| Spieltagstabelle | 114 | 70 | **61,4 %** | 52,2 – 69,8 % | 1,97 | 2,32 |
| Spieltagstabelle, Gegner mit ≥ 5 Spielen | 98 | 60 | **61,2 %** | 51,3 – 70,3 % | 1,98 | 2,36 |

Unterschied: **-0,9 Prozentpunkte**. Die Rückschau verändert das Ergebnis praktisch nicht.

Die frühen Spieltage sind dabei die Schwachstelle: nach zwei oder
drei Partien sagt ein Tabellenplatz wenig. Deshalb die dritte Zeile,
die nur Gegner mit mindestens fünf absolvierten Spielen zulässt.

## 4. Braucht es den Gegnerfilter überhaupt?

| Gruppe | Fälle | Treffer | Trefferquote | 95 %-Intervall | Mindestquote | konservativ |
| --- | ---: | ---: | ---: | :---: | ---: | ---: |
| Heim × Quote < 1,30, **ohne** Gegnerfilter | 121 | 73 | **60,3 %** | 51,4 – 68,6 % | 2,01 | 2,35 |
| Heim × Quote < 1,30 × Gegner schwach (Kernzelle) | 114 | 71 | **62,3 %** | 53,1 – 70,6 % | 1,94 | 2,28 |
| Heim × Quote < 1,30 × Gegner **stark** | 7 | 2 | **28,6 %** | 8,2 – 64,1 % | 4,24 | 14,73 |

**94,2 % der Fälle mit Quote unter 1,30 haben ohnehin einen schwachen
Gegner** (114 von 121).

Der Unterschied zwischen beiden Zeilen beträgt **2,0 Prozentpunkte**.

## 5. Stabilität über die Saisons

| Saison | Fälle | Treffer | Trefferquote | 95 %-Intervall |
| --- | ---: | ---: | ---: | :---: |
| 2015/16 | 12 | 9 | **75,0 %** | 46,8 – 91,1 % |
| 2016/17 | 18 | 12 | **66,7 %** | 43,7 – 83,7 % |
| 2017/18 | 21 | 12 | **57,1 %** | 36,5 – 75,5 % |
| 2018/19 | 12 | 8 | **66,7 %** | 39,1 – 86,2 % |
| 2019/20 | 14 | 9 | **64,3 %** | 38,8 – 83,7 % |
| 2020/21 ⚠ | 8 | 4 | **50,0 %** | 21,5 – 78,5 % |
| 2021/22 ⚠ | 8 | 6 | **75,0 %** | 40,9 – 92,9 % |
| 2022/23 | 11 | 5 | **45,5 %** | 21,3 – 72,0 % |
| 2023/24 | 10 | 6 | **60,0 %** | 31,3 – 83,2 % |

Spanne über die Saisons: **45,5 % bis 75,0 %**. Bei acht bis 
siebzehn Fällen je Saison ist das erwartbare Streuung, kein Trend —
aber es zeigt, wie dünn die Jahresscheiben sind.

## 6. Live-Quote und Ertrag

### Was hier belastbar ist — und was nicht

Wir haben **keine einzige echte Live-Quote** in den Daten.
football-data.co.uk liefert Vorab-Quoten, ESPN liefert
Spielereignisse. Live-Preise kommen in keiner der beiden Quellen vor.

Der genannte Referenzfall — Manchester City zu Hause gegen Burnley,
Vorab-Quote 1,25, Minute 26, Live-Quote 2,15 — **steht nicht in
diesen Daten**. Manchester City hat in den neun Saisons siebenmal zu
Hause gegen Burnley gespielt; in keinem dieser Spiele fiel das erste
Tor vor Minute 35 für Burnley. Der Fall wird deshalb nur über seine
genannten Kennwerte verwendet, nicht als Datenpunkt.

**Ein einziger Kalibrierpunkt kann kein Modell bestimmen.** Was
folgt, ist eine Rechnung unter einer Annahme, keine Schätzung aus
Daten. Die Empfindlichkeitstabelle am Ende zeigt, wie stark das
Ergebnis von dieser Annahme abhängt.

### Das Modell

Aus allen 4194 Heimfällen wird eine logistische Regression
geschätzt: Siegwahrscheinlichkeit aus **Vorab-Wahrscheinlichkeit**
und **Minute des Gegentors**. Der Kehrwert ist die faire Live-Quote.
Die angebotene Quote wird als `fair × k` modelliert, wobei `k` so
gewählt ist, dass der Referenzfall genau 2,15 ergibt.

| | |
|---|---|
| Modell-Siegwahrscheinlichkeit im Referenzfall | 59,8 % |
| faire Live-Quote daraus | 1,67 |
| berichtete Live-Quote | 2,15 |
| **kalibrierter Faktor k** | **1,286** |

> **Das ist das erste Warnsignal.** Ein Buchmacher bietet immer
> *unter* dem fairen Wert an, `k` müsste also kleiner als 1 sein.
> Ein Wert von 1,286 bedeutet: der Markt hielt die Chance für
> deutlich geringer, als unser Modell sie schätzt — beim
> Referenzfall für rund 46,5 % statt 59,8 %.
> Entweder ist unsere Trefferquote zu optimistisch, oder der
> Referenzfall ist untypisch. Mit einem Punkt lässt sich das
> nicht auseinanderhalten.

### Ergebnis für die Kernzelle

| | |
|---|---|
| durchschnittliche geschätzte Live-Quote | **2,01** |
| tatsächliche Trefferquote der Zelle | 62,3 % |
| **Yield bei festem Einsatz, inkl. 5,3 % Wettsteuer** | **19,1 %** |
| Fälle mit geschätzter Live-Quote über 2,28 (konservative Mindestquote) | **1 von 114 = 0,9 %** |

Gerechnet wird so: bei festem Einsatz 1 und Wettsteuer sind effektiv
`1/1,053` im Spiel. Der Ertrag ist `p × Quote / 1,053 − 1`.

### Warum diese Yield-Zahl nichts aussagt

Rechnet man es durch, fällt die Zahl in sich zusammen. Die
geschätzte Live-Quote ist `1/p_Modell × k`. Setzt man sie in die
Yield-Formel ein und ist `p_Modell` ungefähr die tatsächliche
Trefferquote, kürzt sich `p` heraus:

```
Yield = p × (1/p × k) / 1,053 − 1  =  k / 1,053 − 1
      = 1,286 / 1,053 − 1  =  22,1 %
```

Das deckt sich mit den 19,1 % oben. **Der Yield ist also nichts
anderes als der Kalibrierfaktor in anderer Schreibweise** — und der
stammt aus einer einzigen Beobachtung. Es steckt keine Information
darin, die über diesen einen Wert hinausgeht.

### Was passiert, wenn der Markt effizient ist

Live-Märkte auf Spitzenligen gehören zu den am besten bepreisten
überhaupt. Nimmt man an, der Buchmacher hält rund 5 % Marge ein und
liegt sonst richtig, ergibt sich die angebotene Quote aus der
wahren Wahrscheinlichkeit als `0,95 / p`.

| | |
|---|---|
| unsere Trefferquote für die Zelle | 62,3 % |
| angebotene Quote bei effizientem Markt | 1,53 |
| Yield damit | **-9,8 %** |
| vom Referenzfall implizierte Wahrscheinlichkeit (2,15 bei 5 % Marge) | 44,2 % |

**Das ist der Kern der Sache.** Ist unsere Trefferquote richtig *und*
der Markt effizient, verlierst du die Marge — rund 9,8 % je Wette.
Gewinnen lässt sich nur, wenn der Markt diese Situation
systematisch zu niedrig bepreist. Genau das kann eine einzelne
Beobachtung nicht belegen.

Der Referenzfall selbst zeigt in die andere Richtung: eine Quote von
2,15 entspricht bei üblicher Marge einer Markterwartung von rund
44,2 %. Unsere Zelle sagt 62,3 %. Die Lücke von 18,1 Prozentpunkten ist
entweder echter Vorteil — oder unsere Zahl ist zu hoch.

### Empfindlichkeit

Weil `k` auf einem einzigen Punkt beruht, hier der Yield für andere
durchschnittliche Live-Quoten:

| angenommene Live-Quote im Schnitt | Yield | tragfähig? |
| ---: | ---: | --- |
| 1,80 | 6,5 % | positiv |
| 2,00 | 18,3 % | positiv |
| 2,15 | 27,2 % | positiv |
| 2,30 | 36,0 % | positiv |
| 2,50 | 47,9 % | positiv |
| 2,75 | 62,7 % | positiv |
| 3,00 | 77,4 % | positiv |

Break-even liegt bei einer Live-Quote von **1,69**.

Die Tabelle beantwortet aber nur: *wenn* die Quote im Schnitt so
hoch wäre. Ob sie es ist, wissen wir nicht — und die Zeile, auf die
es ankommt, ist 1,53: dort liegt die Quote, die ein effizienter Markt
bei unserer eigenen Trefferquote anbieten würde.

## 7. Rechenwege geprüft

| Prüfung | Ergebnis |
|---|---|
| Wilson gegen zweite, unabhängige Umsetzung (Nullstellen der quadratischen Gleichung), 60 Kombinationen | größte Abweichung **1.11e-15** |
| Wilson ist **keine** Normalapproximation | bestätigt: das Intervall der Kernzelle (53,1 – 70,6 %) ist asymmetrisch um 62,3 %; die Normalapproximation wäre symmetrisch |
| Mindestquote-Formel `1/p × 1,053 × 1,15` | überall dieselbe Konstante 1,21095, auch in Phase 7 |
| Klassengrenzen halboffen | `< 1,30` ist echt kleiner; die Nachbarklasse beginnt bei 1,30. Kein Fall in zwei Klassen. |
| Doppelzählungen | je Spiel höchstens ein Fall — 114 Fälle, 114 verschiedene Spiele |

### Stichprobe: 10 Fälle der Kernzelle

| Datum | Liga | Heim (zurückliegend) | Gegner | Endplatz Gegner | Vorab-Quote fair | Minute | Endstand | Ergebnis |
| --- | --- | --- | --- | ---: | ---: | ---: | :---: | --- |
| 2016-10-02 | SP1 | real madrid | eibar | 10 | 1,140 | 6 | 1:1 | unentschieden |
| 2017-03-19 | SP1 | barcelona | valencia | 12 | 1,178 | 29 | 4:2 | **Sieg** |
| 2017-11-05 | I1 | juventus | benevento | 20 | 1,113 | 19 | 2:1 | **Sieg** |
| 2017-12-02 | SP1 | barcelona | celta | 12 | 1,178 | 20 | 2:2 | unentschieden |
| 2018-05-12 | D1 | bayern munich | stuttgart | 7 | 1,222 | 5 | 1:4 | niederlage |
| 2018-09-02 | SP1 | barcelona | huesca | 19 | 1,135 | 3 | 8:2 | **Sieg** |
| 2019-08-17 | D1 | dortmund | augsburg | 15 | 1,264 | 1 | 5:1 | **Sieg** |
| 2022-11-12 | E0 | Manchester City | Brentford | 9 | 1,210 | 16 | 1:2 | niederlage |
| 2023-03-04 | E0 | Arsenal | Bournemouth | 15 | 1,276 | 1 | 3:2 | **Sieg** |
| 2024-01-21 | SP1 | real madrid | almeria | 19 | 1,179 | 1 | 3:2 | **Sieg** |

Alle 114 Fälle stehen in `data/35er-kernzelle-faelle.csv`.

---

## Fazit

**Was hält:** Die 62,3 % selbst sind sauber gerechnet. Keine
Rückschau-Verzerrung (der Spieltagsstand liefert 61,4 %), keine
Definitionslücken, Verwurfquote 0,17 %, jeder der 114 Fälle gegen
die Rohdaten nachgeprüft, Wilson auf 15 Stellen gegen eine zweite
Umsetzung bestätigt. Die Zahl ist keine Fehlkonstruktion.

**Was nicht hält:** Der Ertrag. Wir haben keine einzige echte
Live-Quote, und die berechneten 19,1 % Yield sind rechnerisch nichts
anderes als der Kalibrierfaktor aus einer einzigen Beobachtung. Wäre
der Markt effizient und unsere Trefferquote richtig, läge der Yield
bei **-9,8 %** — also im Minus. Ob dieser Zustand systematisch zu
niedrig bepreist wird, ist die einzige Frage, die zählt, und sie ist
mit diesen Daten nicht zu beantworten.

**Zwei weitere Einschränkungen:** Die 114 Fälle verteilen sich auf
neun Saisons und fünf Ligen — rund **12,7 Gelegenheiten pro Saison**.
Bis sich statistisch etwas absichern lässt, vergehen Jahre. Und der
Gegnerfilter ist überflüssig: 94,2 % der Fälle mit Quote unter 1,30
haben ohnehin einen schwachen Gegner, der Unterschied beträgt 2,0
Prozentpunkte. Die Regel lässt sich auf **Heimspiel × Vorab-Quote
unter 1,30** verkürzen, ohne etwas zu verlieren.

**Empfehlung:** Noch kein echtes Geld. Der fehlende Baustein ist
messbar, ohne etwas zu riskieren — notiere bei den nächsten 30 bis
50 Auslösern die tatsächlich angebotene Live-Quote, ohne zu setzen.
Liegt sie im Schnitt über 1,69, trägt die Strategie. Liegt sie
darunter, ist die Sache erledigt — und du hast nichts verloren.
