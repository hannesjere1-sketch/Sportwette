# Ligaübersicht für die erweiterte Datenbasis

Schritt 1 des Auftrags: Welche Ligen decken **beide** Quellen ab?

**Bedingung:** ohne Vorab-Quote keine Stärkeklasse, ohne Stärkeklasse
kein verwertbarer Fall. Eine Liga kommt nur hinein, wenn
football-data.co.uk Quoten liefert **und** ESPN den Spielverlauf hat.

## Aufgenommen

| Liga | Stufe | Saisons | Spiele | Quotenspalte | ESPN | Kandidaten <1,80 | gesch. Fälle <1,30 | <1,50 | <1,80 |
| --- | ---: | --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| Premier League | 1 | 2005–2024 | 7220 | B365 | `eng.1` | 2013 | ~62 | ~165 | ~334 |
| La Liga | 1 | 2005–2024 | 7220 | B365 | `esp.1` | 1892 | ~57 | ~127 | ~314 |
| Bundesliga | 1 | 2005–2024 | 5814 | B365 | `ger.1` | 1499 | ~33 | ~94 | ~248 |
| Serie A | 1 | 2005–2024 | 7219 | B365 (7× BbAv, Avg) | `ita.1` | 1981 | ~35 | ~132 | ~328 |
| Ligue 1 | 1 | 2005–2024 | 7045 | B365 (3× BbAv, Avg) | `fra.1` | 1475 | ~21 | ~79 | ~244 |
| Eredivisie | 1 | 2005–2024 | 5740 | B365 (1× Avg) | `ned.1` | 1870 | ~59 | ~152 | ~310 |
| Primeira Liga | 1 | 2005–2024 | 5285 | B365 (3× BbAv, Avg) | `por.1` | 1202 | ~51 | ~113 | ~199 |
| Belgien Pro League | 1 | 2005–2024 | 5056 | B365 (7× BbAv, Avg) | `bel.1` | 1390 | ~12 | ~87 | ~230 |
| Süper Lig | 1 | 2005–2024 | 6049 | B365 (25× BbAv, Avg) | `tur.1` | 1322 | ~11 | ~81 | ~219 |
| Griechenland Super League | 1 | 2005–2024 | 4665 | B365 (71× BbAv, Avg) | `gre.1` | 1357 | ~44 | ~109 | ~225 |
| Scottish Premiership | 1 | 2005–2024 | 4283 | B365 (2× Avg) | `sco.1` | 929 | ~38 | ~82 | ~154 |
| Championship | 2 | 2005–2024 | 10486 | B365 | `eng.2` | 1476 | ~1 | ~34 | ~245 |
| 2. Bundesliga | 2 | 2005–2024 | 5814 | B365 (4× BbAv, Avg) | `ger.2` | 950 | ~0 | ~24 | ~157 |
| Serie B | 2 | 2005–2024 | 8231 | B365 (40× BbAv, Avg) | `ita.2` | 1031 | ~5 | ~22 | ~171 |
| LaLiga 2 | 2 | 2005–2024 | 8757 | B365 (21× BbAv, Avg) | `esp.2` | 941 | ~1 | ~17 | ~156 |
| Ligue 2 | 2 | 2005–2024 | 7119 | B365 (9× Avg) | `fra.2` | 737 | ~0 | ~11 | ~122 |
| **Summe** | | | **106003** | | | **22065** | **~438** | **~1338** | **~3662** |

Die geschätzte Fallzahl ist die Kandidatenzahl mal der **gemessenen**
Ausbeute aus den bisherigen fünf Ligen: von den Spielen mit Heimquote
unter 1,30 werden 13,9 % zu einem Fall, unter 1,50 sind es 14,4 %,
unter 1,80 dann 16,6 %. Die übrigen scheitern daran, dass das erste
Tor nicht vor Minute 35 fällt, nicht vom Gegner kommt oder gar keines
fällt.

## Nicht aufgenommen — und warum

| Liga | Grund |
|---|---|
| Schweiz Super League | **ESPN führt sie nicht.** Unter 218 Wettbewerben gibt es keinen einzigen Eintrag mit dem Präfix `sui.`. Ohne Torminuten kein Fall. |
| Österreich Bundesliga | Steht bei football-data nur in der Zusatzdatei `AUT.csv`, und die führt **`AvgCH`** statt `B365H` — den Marktdurchschnitt statt eines einzelnen Buchmachers. Andere Margenstruktur, andere faire Quote. |
| Dänemark Superliga | wie Österreich (`DNK.csv`, nur `AvgCH`) |
| Norwegen Eliteserien | wie Österreich (`NOR.csv`, nur `AvgCH`), zusätzlich **Kalenderjahr-Saison** statt Herbst–Frühjahr |
| Schweden Allsvenskan | wie Norwegen (`SWE.csv`) |

Zu den vier Zusatzdatei-Ligen: sie **wären** technisch nutzbar, ich
habe sie bewusst weggelassen. Der Grund ist die Quotenspalte. Die
gesamte Stärkeklassifikation hängt an der fairen Quote, und die aus
einem Marktdurchschnitt gerechnete Quote ist nicht dieselbe Größe wie
die aus Bet365 gerechnete — der Durchschnitt hat eine engere Marge und
verschiebt die Klassengrenzen. Bei einer Kernzelle, deren Grenze bei
exakt 1,30 liegt, ist das kein Detail. Zusammen brächten die vier
Ligen ohnehin nur rund 12.700 Spiele, also ein Achtel der
aufgenommenen Menge.

Wenn du sie doch willst, ist der saubere Weg, sie **getrennt**
auszuwerten und erst zusammenzuführen, wenn die Trefferquoten
nachweislich vergleichbar sind — genau so, wie du es für die zweiten
Ligen vorgegeben hast.

## Was in den aufgenommenen Ligen zur Quotenspalte zu sagen ist

`B365H/B365D/B365A` wo vorhanden, das ist bei 20 der 19 Saisons je
Liga der Fall. In wenigen alten Saisons einzelner Ligen fehlt Bet365
für einzelne Partien; dort greift ersatzweise `AvgH` bzw. `BbAvH`.
Die Spalte ist je Spiel in `odds_quelle` protokolliert und wird im
Ergebnisbericht ausgewiesen.

## Zweite Ligen: erste Beobachtung

Die fünf zweiten Ligen liefern zusammen rund **40.400 Spiele**, aber
für die Kernzelle unter 1,30 nur geschätzte **7 Fälle**. Der Grund
liegt auf der Hand: In der Championship oder der Serie B gibt es kaum
Heimmannschaften, die mit einer fairen Quote unter 1,30 antreten.
Erst ab `< 1,80` tragen sie nennenswert bei (~850 Fälle).

Sie werden auftragsgemäß **getrennt ausgewertet** und nur
zusammengeführt, wenn die Trefferquoten vergleichbar sind.
