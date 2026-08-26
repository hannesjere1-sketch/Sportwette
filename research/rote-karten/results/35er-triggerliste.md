# Trigger-Liste, Klasse `< 1,80`, elf erste Ligen

Erzeugt von `13_triggerliste.py`.


## Was in der Liste steht

`data/35er-triggerliste.csv` enthält **alle 2472 Fälle** der Klasse `< 1,80` über elf erste Ligen und neunzehn Saisons — ohne Vorauswahl nach Trefferquote, ohne Gegnerfilter, ohne Ligaauswahl.


| Spalte | Bedeutung |
| --- | --- |
| `datum, liga, saison, team, gegner` | das Spiel; `team` ist immer die Heimmannschaft |
| `vorquote_fair` | faire Vorab-Siegquote der Heimmannschaft, Buchmacher-Marge herausgerechnet |
| `torniveau_liga_saison` | Tore pro Spiel dieser Liga in dieser Saison |
| `minute_gegentor` | Minute des ersten Tors — es ist immer ein Gegentor |
| `modell_p_sieg` | vom Modell geschätzte Siegwahrscheinlichkeit ab diesem Moment |
| `modell_faire_quote` | `1 / modell_p_sieg` — die Quote, bei der es ein Nullsummenspiel wäre |
| `lohnt_ab_quote` | `1,053 / modell_p_sieg` — ab hier trägt die Wette die deutsche Wettsteuer |
| `live_quote_notiert, einsatz, notiert_am, bemerkung` | **leer, zum Ausfüllen** |
| `endstand, ergebnis, treffer` | wie das Spiel ausging |

## Warum die Live-Quote leer bleibt

Weder football-data.co.uk noch ESPN führen Quoten während des Spiels. Die Live-Quote von 2009 ist nicht rekonstruierbar und wird es auch nicht. Die vier leeren Spalten sind deshalb kein Versäumnis, sondern der eigentliche Zweck der Liste: sie zeigt, wie ein Fall aussieht, und gibt die Zahl vor, gegen die die notierte Live-Quote zu halten ist.

Für laufende Spiele liegt daneben `data/35er-livequoten-erfassung.csv` — dieselbe Struktur, nur leer, mit einer Spalte für die angebotene Vorquote und einer für die angebotene Live-Quote.


## Wie oft das vorkommt

| Grösse | Wert |
| --- | ---: |
| Fälle insgesamt | 2472 |
| Saisons | 19 |
| Auslöser pro Saison über elf Ligen | 130,1 |
| davon gewonnen | 1138 (46,0 %) |
| 95 %-Intervall | 44,1 – 48,0 % |
| Quote, ab der es sich im Mittel lohnt | 2,29 |

### Fälle je Liga

| Liga | Fälle | pro Saison |
| --- | ---: | ---: |
| Serie A | 323 | 17,0 |
| Premier League | 313 | 16,5 |
| Eredivisie | 312 | 16,4 |
| La Liga | 303 | 15,9 |
| Bundesliga | 268 | 14,1 |
| Ligue 1 | 244 | 12,8 |
| Belgien Pro League | 167 | 11,9 |
| Süper Lig | 167 | 10,4 |
| Primeira Liga | 139 | 7,7 |
| Scottish Premiership | 127 | 6,7 |
| Griechenland Super League | 109 | 7,3 |

## Stimmt die Modellschätzung?

Die Fälle nach geschätzter Siegwahrscheinlichkeit sortiert und in acht gleich grosse Gruppen geteilt. Läge das Modell daneben, würden geschätzte und tatsächliche Spalte auseinanderlaufen. Die Schätzung ist an denselben Fällen gelernt — das ist eine Beschreibung der Daten, keine Bewährungsprobe an neuen.

| Gruppe | Fälle | Vorquote (Mittel) | Minute (Mittel) | geschätzt | tatsächlich | 95 %-Intervall |
| --- | ---: | ---: | ---: | ---: | ---: | :---: |
| 1 | 309 | 1,73 | 26 | 30,6 % | 33,7 % | 28,6 – 39,1 % |
| 2 | 309 | 1,69 | 18 | 35,2 % | 35,9 % | 30,8 – 41,4 % |
| 3 | 309 | 1,66 | 14 | 38,0 % | 35,3 % | 30,2 – 40,8 % |
| 4 | 309 | 1,61 | 13 | 41,1 % | 42,1 % | 36,7 – 47,6 % |
| 5 | 309 | 1,52 | 15 | 45,2 % | 45,3 % | 39,8 – 50,9 % |
| 6 | 309 | 1,44 | 14 | 50,6 % | 44,3 % | 38,9 – 49,9 % |
| 7 | 309 | 1,35 | 13 | 57,9 % | 62,1 % | 56,6 – 67,4 % |
| 8 | 309 | 1,23 | 11 | 69,7 % | 69,6 % | 64,2 – 74,4 % |

## Wozu das Mitschreiben dient

Die Trefferquote allein sagt nichts darüber, ob sich eine Wette lohnt. Entscheidend ist allein der Abstand zwischen unserer Trefferquote und der Wahrscheinlichkeit, die in der angebotenen Live-Quote schon eingepreist ist. Diesen Abstand kennen wir bisher in keinem einzigen Fall, weil uns die eine Zahl fehlt, die man nicht rekonstruieren kann.

Deshalb ist die nächste Arbeit nicht eine weitere Auswertung, sondern das Sammeln echter Live-Quoten. Bei rund 130 Auslösern pro Saison über elf Ligen kommen genug zusammen, um nach einer Saison zu sehen, ob es einen Abstand gibt — und in welche Richtung.
