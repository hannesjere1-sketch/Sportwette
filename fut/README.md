# FUT-Tagesrhythmus-Strategie (Gold-Spieler)

Idee: Auf dem Transfermarkt von EA FC schwanken die Preise über den Tag. Morgens sind wenige
Spieler online und viele Auktionen der Nacht laufen aus, abends wollen viele kaufen. Wenn eine
Gold-Karte regelmäßig z. B. um 7 Uhr am billigsten und um 20 Uhr am teuersten ist, kann man
morgens kaufen und abends verkaufen — **aber nur, wenn die Spanne die 5 % EA-Steuer schlägt.**

Dieses Verzeichnis enthält:

| Datei | Zweck |
| --- | --- |
| `collect.py`, `run_collector.sh` + `.github/workflows/fut-prices.yml` | **Automatisch:** sammelt alle 15 Minuten die Preise (GitHub Actions, kostenlos) |
| `players.json` | 80 beobachtete Gold-Karten (EA-IDs, 2.000–400.000 Coins), geprüft: Gold, Basisversion, Transfermarkt-Preis |
| `../static-app/fut.html` | Handy-Seite mit Tagesprofil, Backtest und Preisen |
| `collector/` | Alternative: Chrome-Erweiterung, die Preise im eigenen Browser sammelt |
| `analyze.py` | Stundenprofil pro Spieler + Walk-Forward-Backtest nach Steuer, Belohnungseffekte |
| `events.json` | Belohnungstermine (Squad Battles, Champions, Division Rivals), anpassbar |
| `test_analyze.py` | Tests mit künstlichen Preisen, deren Wahrheit bekannt ist |

## Automatisch sammeln (empfohlen, auch fürs Handy)

Kostenlose, aktuelle Preise liefert die öffentliche API von EasySBC (`api-fc27.easysbc.io`). Anders als
FUT.GG, FUTBIN und FUTWIZ blockt sie Server nicht per Cloudflare. Sie kennt aber nur den aktuellen
Preis, keinen Verlauf. Deshalb fragt ein GitHub-Actions-Job alle 15 Minuten ab und baut den Verlauf
selbst auf.

GitHub überspringt die meisten Läufe eines häufigen Zeitplans: Am ersten Tag kamen bei „alle 20 Minuten“
nur 2 von 24 an. Deshalb bleibt jeder Lauf knapp 6 Stunden aktiv und sammelt selbst im 15-Minuten-Takt
(`run_collector.sh`). Die Zeitpläne um :13 und :43 dienen nur als Neustart. Kommt ein Anstoß, während
noch ein Lauf aktiv ist, wartet er und übernimmt nahtlos. Für öffentliche Repos kosten die
Actions-Minuten nichts.

Bei jeder Runde passiert Folgendes:

1. `fut/collect.py` hängt die Preise der 80 Gold-Karten aus `players.json` an `fut-prices.csv` an.
2. `fut/analyze.py` wertet sofort aus und schreibt `fut-analysis.json` und `bericht.txt`.
3. Alle drei Dateien werden auf den eigenen Branch **`fut-data`** committet, damit die Code-Historie
   sauber bleibt.
4. Die Seite `fut.html` (GitHub Pages) liest `fut-analysis.json` und zeigt alles handytauglich an:
   `https://hannesjere1-sketch.github.io/Sportwette/fut.html`

Zeitgesteuerte Workflows startet GitHub nur vom Standard-Branch aus. Der Workflow muss dort also
liegen, damit er läuft. Einmal manuell starten geht unter Actions → „FUT-Preise sammeln“ → Run workflow.

## Warum zusätzlich eine Browser-Erweiterung?

FUT.GG hat genauere Preise, blockt aber Server und Cloud-Rechner (geprüft: HTTP 403 „Just a moment…“).
Ein normaler Chrome kommt durch. Die Erweiterung ist die Alternative, falls EasySBC einmal ausfällt.
Die Erweiterung nutzt einen inoffiziellen FUT.GG-Endpunkt, der sich ändern kann. Sie loggt sich
**nicht** in die EA-Web-App ein und handelt nicht automatisch. Automatisiertes Handeln verstößt
gegen die EA-Nutzungsbedingungen und kann zum Bann führen, deshalb kaufst und verkaufst du selbst.

## Ablauf mit der Browser-Erweiterung

1. **Erweiterung laden**: `chrome://extensions` → Entwicklermodus → „Entpackte Erweiterung laden“
   → Ordner `fut/collector` wählen.
2. Einmal <https://www.fut.gg> normal öffnen (Cloudflare-Check), dann im Popup „Jetzt abrufen“.
   Kommen Preise an, läuft ab jetzt alles automatisch, solange Chrome offen ist.
3. Liste anpassen: eine Karte pro Zeile, `EA-ID Name`. Die ID steht in der FUT.GG-URL
   (`fut.gg/players/231747-kylian-mbappe/` → `231747`). Voreingestellt sind 14 beliebte Rare-Golds.
   Für mehr Umsatz eignen sich auch günstigere Meta-Golds (5.000–50.000 Coins).
4. **Mindestens 6 volle Tage sammeln.** Das Zuverlässigkeits-Urteil (siehe unten) sagt, wann es reicht.
5. „CSV exportieren“, dann:

   ```bash
   python3 fut/analyze.py ~/Downloads/fut-preise-2026-10-09.csv --json fut-ergebnis.json
   ```

Chrome muss dafür nicht rund um die Uhr laufen. Fehlende Stunden werden einfach ausgelassen. Ein
Tag zählt aber erst, wenn für ihn mindestens 12 Stunden Preise vorliegen (`--min-hours`).

## Wie schnell gibt es eine Aussage?

Statt fester zwei Wochen zeigt die Auswertung ein **Zuverlässigkeits-Urteil**. Es wird nur aus Tagen
berechnet, die das Modell vorher nicht kannte:

- **Trefferquote:** An wie vielen Spieler-Tagen lag die gelernte teure Stunde wirklich über der
  gelernten billigen? Dazu kommt die untere Grenze des 95-%-Bereichs.
- **Ø nach Steuer:** Die Rendite pro Trade nach 5 % Steuer und 1 % Unterbieten. Die Unsicherheit wird
  aus einem Mittelwert **pro Kalendertag** berechnet, weil alle Karten am selben Markt hängen und an
  einem Tag gemeinsam schwanken. 80 Karten sind also nicht 80 unabhängige Beweise.
- Urteile: ⏳ weiter sammeln · 🟡 Muster echt, schlägt die Steuer aber nicht sicher ·
  🟢 stabil und nach Steuer sicher im Plus · 🔴 nach einer Woche kein Muster.

Das Modell lernt 3 Tage und prüft dann an mindestens 3 weiteren Tagen. Das früheste Urteil kommt
deshalb nach etwa **6 vollen Tagen**, ein Tag zählt ab 12 Stunden mit Preisen. Mit künstlichen Daten
und ±4–5 % Tagesspanne kommt 🟢 genau dann. Ob das Muster Promo-Tage übersteht, zeigt sich erst nach
einer vollen Woche.

## Belohnungen: Squad Battles, Champions, Division Rivals

Werden Belohnungen ausgeschüttet, öffnen viele Spieler Packs, und plötzlich kommen deutlich mehr Karten
auf den Markt. Das verzerrt das normale Tagesmuster. Die Auswertung berücksichtigt das auf drei Arten:

1. **An Belohnungstagen handelt die Tagesstrategie nicht.** Das Stundenprofil nimmt außerdem den
   Median über die Tage statt des Durchschnitts, damit die zwei bis drei Belohnungstage pro Woche es
   nicht verbiegen.
2. **Der Effekt wird gemessen:** Für jede Ausschüttung wird der Preisverlauf der nächsten 48 Stunden
   mit normalen Tagen ab derselben Uhrzeit verglichen. Heraus kommen Tiefpunkt (wie viel tiefer,
   nach wie vielen Stunden) und der Stand nach 24 Stunden.
3. **Eigener Backtest „nach der Belohnung kaufen“:** Kauft zum gelernten Tiefpunkt und verkauft beim
   Höchststand danach. Die Stunden kommen nur aus früheren Ausschüttungen derselben Art.

Die Termine stehen in `events.json` in deutscher Zeit, Wochentag 0 = Montag:

| Belohnung | Annahme |
| --- | --- |
| Squad Battles | Sonntag 09:00 |
| Champions | Montag 09:00 |
| Division Rivals | Donnerstag 09:00 |

Diese Zeiten stammen aus den Vorjahren (8 Uhr britischer Zeit) und sind für FC 27 nicht bestätigt.
Liegt der gemessene Tiefpunkt deutlich später als erwartet, stimmt vermutlich die Uhrzeit nicht und
sollte in `events.json` korrigiert werden.

## Was die Auswertung macht

1. Alle Preise werden pro Spieler auf eine Stunde verdichtet (Median, Zeitzone Europe/Berlin).
2. Jede Stunde wird durch den Tagesmedian des Spielers geteilt. Dadurch sieht ein Spieler, der die
   ganze Woche steigt, abends nicht künstlich teuer aus. Übrig bleibt nur das Muster innerhalb des Tages.
3. **Walk-Forward-Backtest:** Für jeden Tag D lernt das Modell die billigste und die teuerste Stunde
   **nur aus den Tagen vor D** (Standard: 14 Tage). Gekauft wird zur billigsten Stunde, verkauft zur
   teuersten (am selben Tag, sonst am nächsten). Gehandelt wird nur, wenn die gelernte Spanne nach
   5 % Steuer und 1 % Unterbieten noch mindestens 1 % bringt.
4. Ausgabe: Stundenprofil über alle Spieler, pro Spieler die billigste und teuerste Stunde, Trades,
   Trefferquote, Ø Rendite und Gewinn in Coins, dazu das Ergebnis pro Woche.

„Nachhaltig“ ist die Strategie erst, wenn **mehrere Spieler** und **mehrere Wochen** hintereinander
im Plus sind, nicht nur ein Spieler in einer guten Woche.

Parameter: `--window`, `--min-days`, `--min-hours`, `--min-edge`, `--slippage` (siehe `--help`).

## Ehrliche Einordnung

- Ob sich das lohnt, entscheiden die echten Daten, nicht der Code. Eine Spanne unter ca. 6,5 %
  (Steuer plus Unterbieten) bringt nichts, und der Backtest handelt dann einfach nicht.
- Die Preisseiten zeigen den günstigsten Sofortkauf-Preis (Lowest BIN). Zu genau diesem Preis
  bekommt man die Karte nicht immer, und beim Verkauf wird nicht jede Karte zur teuersten Stunde
  verkauft. Die Rendite im Backtest ist deshalb eher eine Obergrenze.
- Promo-Starts (TOTW am Mittwoch 19 Uhr, neue SBCs, Weekend League) verschieben Preise stärker als
  die Tageszeit. Das Wochen-Ergebnis zeigt, ob das Muster solche Wochen übersteht.
- Die Tests (`python3 -m unittest fut/test_analyze.py`) prüfen mit künstlichen Daten, dass ein
  echtes Muster erkannt wird, dass Rauschen **keinen** Scheingewinn erzeugt und dass der Backtest
  nicht in die Zukunft schaut. Die künstlichen Daten sagen nichts über den echten Markt aus.
