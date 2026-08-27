# Was kostet die Rote Karte wirklich?

Links die Mannschaft **mit** Roter Karte. Daneben, was Mannschaften
**ohne** Rote Karte in genau derselben Lage erreicht haben. Die
Spalte *Differenz* ist der Abstand in Prozentpunkten (PP) — das ist
der eigentliche Preis der Karte.

## Wie der Vergleich gebaut ist

Zu jedem echten Rote-Karte-Fall wird ein Zwilling gesucht: dieselbe
Minute, derselbe Spielstand, dieselbe Stärke, dasselbe Heimrecht —
nur eben elf gegen elf. Der Zwilling kommt aus allen Spielen ohne
Rote Karte, bei denen der Spielstand an einer festen Referenzminute
je Abschnitt abgelesen wird (0-15 → Min. 8, 16-30 → Min. 23, 31-45 → Min. 38, 46-60 → Min. 53, 61-75 → Min. 68, 76+ → Min. 83).

Gibt es zu einem Zustand weniger als 20 Vergleichsspiele, wird eine
Stufe gröber gesucht — erst ohne Heimrecht, dann ohne Stärke, dann
ohne Minute. Die Spalte *Vergleichsebene* sagt, wie fein es am Ende
wirklich war. Steht dort „gesamt", ist der Vergleich praktisch
wertlos.

**Eine ehrliche Einschränkung:** jedes Vergleichsspiel taucht in
mehreren Minuten-Abschnitten auf. Die Beobachtungen sind also nicht
unabhängig voneinander. Deshalb steht auf der Vergleichsseite
bewusst kein Konfidenzintervall — nur links, wo jeder Fall genau
einmal zählt.

---

## Gesamt

| Gruppe | Fälle mit Rot | Sieg mit Rot | 95 %-Intervall | erwartet ohne Rot | Differenz | Vergleichsebene | Hinweis |
| --- | ---: | ---: | :---: | ---: | ---: | --- | --- |
| alle Fälle | 2796 | 19,3 % | 17,9 – 20,8 % | 30,3 % | -11,0 PP | Minute+Stand+Stärke+Ort | — |

## Nach Minute der Roten Karte

| Gruppe | Fälle mit Rot | Sieg mit Rot | 95 %-Intervall | erwartet ohne Rot | Differenz | Vergleichsebene | Hinweis |
| --- | ---: | ---: | :---: | ---: | ---: | --- | --- |
| 0-15 | 121 | 9,1 % | 5,2 – 15,5 % | 34,9 % | -25,9 PP | Minute+Stand+Stärke+Ort | — |
| 16-30 | 206 | 15,0 % | 10,8 – 20,6 % | 32,1 % | -17,0 PP | Minute+Stand+Stärke+Ort | — |
| 31-45 | 384 | 13,5 % | 10,5 – 17,3 % | 33,0 % | -19,5 PP | Minute+Stand+Stärke+Ort | — |
| 46-60 | 381 | 19,7 % | 16,0 – 24,0 % | 32,5 % | -12,8 PP | Minute+Stand+Stärke+Ort | — |
| 61-75 | 549 | 25,3 % | 21,9 – 29,1 % | 34,8 % | -9,4 PP | Minute+Stand+Stärke+Ort | — |
| 76+ | 1155 | 20,1 % | 17,9 – 22,5 % | 25,7 % | -5,6 PP | Minute+Stand+Stärke+Ort | — |

## Nach Spielstand in dem Moment

| Gruppe | Fälle mit Rot | Sieg mit Rot | 95 %-Intervall | erwartet ohne Rot | Differenz | Vergleichsebene | Hinweis |
| --- | ---: | ---: | :---: | ---: | ---: | --- | --- |
| fuehrt | 677 | 65,9 % | 62,2 – 69,4 % | 81,7 % | -15,8 PP | Minute+Stand+Stärke+Ort | — |
| unentschieden | 1032 | 7,8 % | 6,4 – 9,7 % | 24,3 % | -16,5 PP | Minute+Stand+Stärke+Ort | — |
| 1 zurueck | 727 | 1,8 % | 1,0 – 3,0 % | 5,6 % | -3,9 PP | Minute+Stand+Stärke+Ort | — |
| 2+ zurueck | 360 | 0,0 % | 0,0 – 1,1 % | 0,6 % | -0,6 PP | Minute+Stand+Stärke+Ort | — |

## Nach Stärke vor dem Anpfiff

| Gruppe | Fälle mit Rot | Sieg mit Rot | 95 %-Intervall | erwartet ohne Rot | Differenz | Vergleichsebene | Hinweis |
| --- | ---: | ---: | :---: | ---: | ---: | --- | --- |
| <1.50 | 138 | 50,0 % | 41,8 – 58,2 % | 69,3 % | -19,3 PP | Minute+Stand+Stärke+Ort | — |
| 1.50-2.50 | 851 | 29,4 % | 26,4 – 32,5 % | 45,2 % | -15,8 PP | Minute+Stand+Stärke+Ort | — |
| >2.50 | 1807 | 12,2 % | 10,8 – 13,8 % | 20,3 % | -8,1 PP | Minute+Stand+Stärke+Ort | — |

## Nach Heim oder Auswärts

| Gruppe | Fälle mit Rot | Sieg mit Rot | 95 %-Intervall | erwartet ohne Rot | Differenz | Vergleichsebene | Hinweis |
| --- | ---: | ---: | :---: | ---: | ---: | --- | --- |
| heim | 1259 | 22,4 % | 20,2 – 24,8 % | 36,0 % | -13,6 PP | Minute+Stand+Stärke+Ort | — |
| auswaerts | 1537 | 16,8 % | 15,0 – 18,7 % | 25,6 % | -8,8 PP | Minute+Stand+Stärke+Ort | — |

---

## Lesehilfe

- **Differenz −18 PP** heißt: von 100 vergleichbaren Situationen
  gewinnt die Mannschaft mit Roter Karte 18-mal seltener.
- Eine Differenz nahe 0 heißt: in dieser Lage hätte es auch mit elf
  Mann kaum anders ausgesehen — die Karte war nicht das Entscheidende.
- Gruppen mit dem Hinweis „zu wenig Daten" bitte nicht interpretieren.
- Für belastbare Zahlen in `01_fetch_matches.py` mehr Saisons und
  Ligen freischalten und Phase 2 bis 4 erneut laufen lassen.
