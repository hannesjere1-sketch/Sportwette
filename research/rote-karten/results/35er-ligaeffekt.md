# Ligaunterschiede: Torniveau statt elf Einzelzellen

Erzeugt von `12_ligaeffekt.py`. Grundlage: 2472 Faelle der elf ersten Ligen, 19 Saisons.


## 1. Torniveau je Liga

Tore pro Spiel, gemittelt ueber alle 19 Saisons und berechnet aus **allen** Spielen der Liga, nicht nur aus den Faellen.

| Liga | Tore/Spiel | Spanne ueber die Saisons | Fälle | Trefferquote | 95 %-Intervall |
| --- | ---: | :---: | ---: | ---: | :---: |
| Eredivisie | 3,08 | 2,84 – 3,47 | 312 | **49,0 %** | 43,5 – 54,6 % |
| Bundesliga | 2,96 | 2,74 – 3,22 | 268 | **44,8 %** | 38,9 – 50,8 % |
| Belgien Pro League | 2,81 | 2,51 – 3,04 | 167 | **41,9 %** | 34,7 – 49,5 % |
| Premier League | 2,73 | 2,45 – 3,28 | 313 | **46,3 %** | 40,9 – 51,9 % |
| Süper Lig | 2,71 | 2,41 – 3,05 | 167 | **51,5 %** | 44,0 – 59,0 % |
| Serie A | 2,69 | 2,51 – 3,05 | 323 | **44,0 %** | 38,7 – 49,4 % |
| La Liga | 2,67 | 2,46 – 2,94 | 303 | **47,5 %** | 42,0 – 53,1 % |
| Scottish Premiership | 2,64 | 2,40 – 2,94 | 127 | **40,9 %** | 32,8 – 49,6 % |
| Primeira Liga | 2,51 | 2,23 – 2,87 | 139 | **54,0 %** | 45,7 – 62,0 % |
| Ligue 1 | 2,51 | 2,13 – 2,81 | 244 | **40,2 %** | 34,2 – 46,4 % |
| Griechenland Super League | 2,33 | 2,13 – 2,96 | 109 | **48,6 %** | 39,4 – 57,9 % |

## 2. Logistische Regression

Zielgrösse ist der Treffer (Sieg nach 0:1). `logit_p0` ist das Logit der fairen Vorab-Siegwahrscheinlichkeit, also die Vorquote auf der Modellskala; `minute` die Minute des Gegentors; `torniveau` die Tore pro Spiel der Liga-Saison.


**Ohne Torniveau** (n = 2472)

| Grösse | Koeffizient | Standardfehler | z | p |
| --- | ---: | ---: | ---: | ---: |
| Achsenabschnitt | -0,7407 | 0,1096 | -6,76 | < 0,0001 |
| logit_p0 | 1,2101 | 0,1075 | 11,25 | < 0,0001 |
| minute | -0,0179 | 0,0045 | -4,01 | < 0,0001 |

**Mit Torniveau** (n = 2472)

| Grösse | Koeffizient | Standardfehler | z | p |
| --- | ---: | ---: | ---: | ---: |
| Achsenabschnitt | -1,1418 | 0,4664 | -2,45 | 0,0143 |
| logit_p0 | 1,2024 | 0,1079 | 11,14 | < 0,0001 |
| minute | -0,0177 | 0,0045 | -3,97 | < 0,0001 |
| torniveau | 0,1470 | 0,1660 | 0,89 | 0,3759 |

Zur Grössenordnung: die elf Ligen liegen im Mittel zwischen 2,33 und 3,08 Toren pro Spiel.

## 3. Heterogenitätstest über die elf Ligen

Der rohe Test fragt: reicht Zufall aus, um die Spannweite der Trefferquoten zu erklären? Der zweite Test fragt schärfer: bleibt ein Ligaunterschied übrig, nachdem Vorquote, Minute und Torniveau abgezogen sind?

| Klasse | Fälle | roh: Chi² | p | nach Abzug: Chi² | p | Freiheitsgrade |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| < 1,30 | 343 | 14,9 | 0,1366 | 14,4 | 0,1557 | 10 |
| < 1,50 | 1050 | 10,8 | 0,3733 | 7,6 | 0,6717 | 10 |
| < 1,80 (alle) | 2472 | 13,8 | 0,1821 | 8,4 | 0,5914 | 10 |

Für die ganze Klasse `< 1,80`: Anteil der Streuung, der nicht Zufall ist (I²), roh **28 %**, nach Abzug **0 %**.

### Rest je Liga, Klasse `< 1,80`

Beobachtete minus vom Modell erwartete Treffer. Ein z über 2 oder unter −2 wäre auffällig.

| Liga | Fälle | beobachtet | erwartet | Differenz | z |
| --- | ---: | ---: | ---: | ---: | ---: |
| Süper Lig | 167 | 86 | 73,9 | 12,1 | 1,92 |
| Primeira Liga | 139 | 75 | 68,2 | 6,8 | 1,20 |
| Griechenland Super League | 109 | 53 | 50,7 | 2,3 | 0,45 |
| La Liga | 303 | 144 | 141,5 | 2,5 | 0,31 |
| Eredivisie | 312 | 153 | 153,2 | -0,2 | -0,03 |
| Serie A | 323 | 142 | 143,9 | -1,9 | -0,22 |
| Ligue 1 | 244 | 98 | 100,2 | -2,2 | -0,29 |
| Premier League | 313 | 145 | 147,6 | -2,6 | -0,30 |
| Belgien Pro League | 167 | 70 | 74,2 | -4,2 | -0,66 |
| Bundesliga | 268 | 120 | 125,2 | -5,2 | -0,66 |
| Scottish Premiership | 127 | 52 | 59,4 | -7,4 | -1,36 |

### Rest je Liga, Klasse `< 1,30`

Das ist die Zelle, in der die Spannweite von 44 bis 84 % aufgefallen ist.

| Liga | Fälle | beobachtet | erwartet | Differenz | z |
| --- | ---: | ---: | ---: | ---: | ---: |
| Eredivisie | 57 | 48 | 39,4 | 8,6 | 2,49 |
| Primeira Liga | 35 | 26 | 23,4 | 2,6 | 0,92 |
| Griechenland Super League | 19 | 14 | 12,2 | 1,8 | 0,87 |
| La Liga | 54 | 41 | 39,0 | 2,0 | 0,62 |
| Süper Lig | 11 | 8 | 7,0 | 1,0 | 0,60 |
| Scottish Premiership | 22 | 15 | 14,8 | 0,2 | 0,08 |
| Serie A | 38 | 25 | 25,4 | -0,4 | -0,13 |
| Premier League | 47 | 29 | 31,6 | -2,6 | -0,80 |
| Bundesliga | 36 | 22 | 25,4 | -3,4 | -1,24 |
| Belgien Pro League | 9 | 4 | 5,8 | -1,8 | -1,26 |
| Ligue 1 | 15 | 8 | 10,5 | -2,5 | -1,43 |

## 4. Was daraus folgt

**Das Torniveau erklärt nichts.** Der Koeffizient ist 0,1470 bei einem Standardfehler von 0,1660 (p = 0,3759). Über die Spannweite der elf Ligen — 2,33 bis 3,08 Tore pro Spiel — ändert das die geschätzte Trefferquote um weniger als einen Prozentpunkt. Die Vermutung, dass torreichere Ligen mehr Aufholjagden sehen, lässt sich an diesen Daten nicht belegen.

**Die Ligaunterschiede sind kleiner als das Rauschen.** Schon der rohe Test wird in keiner der drei Klassen signifikant. In der Klasse `< 1,30`, wo die Spannweite von 44 bis 84 % am stärksten ins Auge fällt, liegt p bei 0,1366. Mit elf Ligen und Fallzahlen zwischen 9 und 57 ist eine solche Spannweite genau das, was Zufall erzeugt.

**Zur Eredivisie:** dort liegt z bei 2,49, also über 2. Das ist der einzige Ausreißer unter 11 geprüften Ligen. Rein zufällig mindestens einen solchen Ausreißer zu sehen, hat eine Wahrscheinlichkeit von 40 % — es ist also kein Befund, sondern der erwartete Ausreißer.

**Damit fällt meine frühere Begründung weg.** Ich hatte geschrieben, die faire Quote sei liga-relativ und 1,25 bedeute in der Eredivisie etwas anderes als in der Premier League. Der Einwand dagegen ist richtig: die Vorquote ist der Preis des Buchmachers, und der ist nicht ligablind. Die Erklärung war aber nicht nur falsch, sie war überflüssig — es gibt keinen Ligaunterschied, der erklärt werden müsste. Die elf Ligen dürfen ein Topf sein.
