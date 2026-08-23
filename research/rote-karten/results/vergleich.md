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
| alle Fälle | 53 | 28,3 % | 18,0 – 41,6 % | 36,5 % | -8,2 PP | Minute+Stand+Stärke+Ort | — |

## Nach Minute der Roten Karte

| Gruppe | Fälle mit Rot | Sieg mit Rot | 95 %-Intervall | erwartet ohne Rot | Differenz | Vergleichsebene | Hinweis |
| --- | ---: | ---: | :---: | ---: | ---: | --- | --- |
| 0-15 | 2 | 0,0 % | 0,0 – 65,8 % | 41,6 % | -41,6 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 2) |
| 16-30 | 5 | 20,0 % | 3,6 – 62,4 % | 25,4 % | -5,4 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 5) |
| 31-45 | 8 | 25,0 % | 7,1 – 59,1 % | 35,5 % | -10,5 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 8) |
| 46-60 | 5 | 40,0 % | 11,8 – 76,9 % | 51,7 % | -11,7 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 5) |
| 61-75 | 13 | 30,8 % | 12,7 – 57,6 % | 45,0 % | -14,2 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 13) |
| 76+ | 20 | 30,0 % | 14,5 – 51,9 % | 29,9 % | +0,1 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 20) |

## Nach Spielstand in dem Moment

| Gruppe | Fälle mit Rot | Sieg mit Rot | 95 %-Intervall | erwartet ohne Rot | Differenz | Vergleichsebene | Hinweis |
| --- | ---: | ---: | :---: | ---: | ---: | --- | --- |
| fuehrt | 17 | 76,5 % | 52,7 – 90,4 % | 83,4 % | -6,9 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 17) |
| unentschieden | 18 | 5,6 % | 1,0 – 25,8 % | 26,7 % | -21,1 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 18) |
| 1 zurueck | 10 | 10,0 % | 1,8 – 40,4 % | 3,8 % | +6,2 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 10) |
| 2+ zurueck | 8 | 0,0 % | 0,0 – 32,4 % | 0,0 % | 0,0 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 8) |

## Nach Stärke vor dem Anpfiff

| Gruppe | Fälle mit Rot | Sieg mit Rot | 95 %-Intervall | erwartet ohne Rot | Differenz | Vergleichsebene | Hinweis |
| --- | ---: | ---: | :---: | ---: | ---: | --- | --- |
| <1.50 | 5 | 80,0 % | 37,6 – 96,4 % | 93,8 % | -13,8 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 5) |
| 1.50-2.50 | 14 | 50,0 % | 26,8 – 73,2 % | 58,2 % | -8,2 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 14) |
| >2.50 | 34 | 11,8 % | 4,7 – 26,6 % | 19,2 % | -7,4 PP | Minute+Stand+Stärke+Ort | — |

## Nach Heim oder Auswärts

| Gruppe | Fälle mit Rot | Sieg mit Rot | 95 %-Intervall | erwartet ohne Rot | Differenz | Vergleichsebene | Hinweis |
| --- | ---: | ---: | :---: | ---: | ---: | --- | --- |
| heim | 25 | 28,0 % | 14,3 – 47,6 % | 44,5 % | -16,5 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 25) |
| auswaerts | 28 | 28,6 % | 15,3 – 47,1 % | 29,4 % | -0,8 PP | Minute+Stand+Stärke+Ort | zu wenig Daten (rot: 28) |

---

## Lesehilfe

- **Differenz −18 PP** heißt: von 100 vergleichbaren Situationen
  gewinnt die Mannschaft mit Roter Karte 18-mal seltener.
- Eine Differenz nahe 0 heißt: in dieser Lage hätte es auch mit elf
  Mann kaum anders ausgesehen — die Karte war nicht das Entscheidende.
- Gruppen mit dem Hinweis „zu wenig Daten" bitte nicht interpretieren.
- Für belastbare Zahlen in `01_fetch_matches.py` mehr Saisons und
  Ligen freischalten und Phase 2 bis 4 erneut laufen lassen.
