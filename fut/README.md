# Icons & Heroes flippen: wann kaufen, wann verkaufen?

Ziel: verstehen, an welchem **Wochentag** und zu welcher **Stunde** Icons (unter 500.000 Coins)
und Heroes (bis 500.000 Coins) am billigsten und am teuersten sind. Alle Zahlen sind **ohne
Steuer**. Die 5 % EA-Steuer rechnest du dir selbst ab.

Ergebnisse auf dem Handy: <https://hannesjere1-sketch.github.io/Sportwette/fut.html>

| Datei | Zweck |
| --- | --- |
| `players.json` | Die beobachteten Karten: 126 Base Icons und 145 Base Heroes, die beim Einrichten bis 600.000 Coins kosteten |
| `collect.py` | Holt den aktuellen Preis jeder Karte und hängt ihn an `icons-prices.csv` an |
| `run_collector.sh` + `.github/workflows/fut-prices.yml` | Läuft auf GitHub Actions und macht jede Stunde um :05 eine Messung |
| `analyze.py` | Wochen-Heatmap, Tagesverlauf, beste Flips, ehrlicher Test, Werte pro Karte |
| `test_analyze.py` | Tests mit künstlichen Preisen, deren Muster bekannt ist |
| `../static-app/fut.html` | Die Handy-Seite |

## Woher die Preise kommen

Die Preise stammen aus der öffentlichen API von EasySBC (`api-fc27.easysbc.io`). Sie liefert den
günstigsten Sofortkauf-Preis und blockt, anders als FUT.GG, FUTBIN und FUTWIZ, keine Server. Einen
Verlauf kennt sie nicht. Deshalb wird jede Stunde gemessen und der Verlauf hier aufgebaut.

GitHub überspringt viele Läufe häufiger Zeitpläne. Deshalb bleibt jeder Lauf knapp 6 Stunden aktiv
und misst selbst zu jeder vollen Stunde. Die Zeitpläne um :13 und :43 dienen nur als Neustart. Die
Daten liegen auf dem Branch **`fut-data`** (`icons-prices.csv`, `icons-analysis.json`,
`bericht.txt`).

Icons und Heroes sind bei EasySBC an der `versionId` zu erkennen: 12 steht für „Base Icon“, 72 für
„Base Hero“. Viele Icons gibt es unter zwei IDs mit eigenem Preis. Beide werden beobachtet, die
zweite heißt dann z. B. „Xabi Alonso (2)“. Die 500.000-Grenze gilt für den **mittleren** Preis einer
Karte, damit eine kurze Preisspitze sie nicht rauswirft.

## Was die Auswertung macht

1. **Pro Karte eine Stunde, ein Preis.** Gibt es mehrere Messungen in einer Stunde, zählt der Median.
2. **Vergleich mit dem eigenen Niveau.** Jeder Stundenpreis wird durch den Median derselben Karte
   über die umliegenden 72 Stunden geteilt. Dadurch sieht eine Karte, die die ganze Woche steigt,
   am Sonntag nicht künstlich teuer aus. Übrig bleibt nur: Wie viel billiger oder teurer als üblich
   ist diese Stunde? Dafür braucht jede Karte mindestens 24 Stunden Daten.
3. **Wochen-Heatmap.** Für jedes Feld aus Wochentag × Stunde wird der Median über alle Karten
   gebildet. Blau heißt billiger als üblich, rot teurer. Belohnungstage, TOTW am Mittwochabend
   oder die Weekend League zeigen sich hier automatisch.
4. **Beste Flips.** Aus der Heatmap: in welchem Feld kaufen, in welchem bis zu 72 Stunden später
   verkaufen, sortiert nach dem Unterschied.
5. **Ehrlicher Test.** Für jeden Tag werden die billigste und die teuerste Stunde jeder Karte nur
   aus den Vortagen gelernt und dann an diesem Tag geflippt. Was nur im Rückblick funktioniert,
   fällt hier durch. Die Unsicherheit wird über Kalendertage gerechnet, weil alle Karten am selben
   Markt hängen.
6. **Pro Karte:** aktueller Preis, Tief und Hoch der letzten 7 Tage, typisch billigste und teuerste
   Stunde und die Spanne dazwischen.

Alles lässt sich getrennt für Icons, Heroes und beide zusammen ansehen.

## Wie lange es dauert

- **Tagesverlauf:** nach etwa 2 Tagen.
- **Ehrlicher Test:** nach 3 vollen Tagen.
- **Wochen-Heatmap und beste Flips:** Jeder Wochentag erscheint, sobald er einmal gemessen ist.
  Belastbar werden sie erst nach 2–3 Wochen, weil jeder Wochentag dann mehrmals vorkommt.

## Lokal ausführen

```bash
git fetch origin fut-data
git show origin/fut-data:icons-prices.csv > icons-prices.csv
python3 fut/analyze.py icons-prices.csv
python3 -m unittest fut/test_analyze.py
```

## Grenzen

- Die Preise sind der günstigste Sofortkauf. Ob man genau dazu kauft oder verkauft, hängt vom
  Markt in dem Moment ab.
- Eine Messung pro Stunde verpasst kurze Ausreißer innerhalb der Stunde.
- Promos und neue Content-Wellen verschieben das Preisniveau stärker als die Uhrzeit. Die
  72-Stunden-Normierung fängt Trends ab, plötzliche Brüche aber nur teilweise.
