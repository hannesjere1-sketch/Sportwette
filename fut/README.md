# Icons & Heroes flippen: wann kaufen, wann verkaufen?

Ziel: verstehen, an welchem **Wochentag** und zu welcher **Stunde** Icons (unter 500.000 Coins)
und Heroes (bis 500.000 Coins) am billigsten und am teuersten sind. Alle Zahlen sind **ohne
Steuer**. Die 5 % EA-Steuer rechnest du dir selbst ab.

Ergebnisse auf dem Handy: <https://hannesjere1-sketch.github.io/Sportwette/fut.html>

| Datei | Zweck |
| --- | --- |
| `players.json` | Die beobachteten Karten: 126 Base Icons und 145 Base Heroes, die beim Einrichten bis 600.000 Coins kosteten |
| `collect.py` | Holt den aktuellen Preis jeder Karte und hängt ihn an `icons-prices.csv` an |
| `run_collector.sh` + `.github/workflows/fut-prices.yml` | Läuft auf GitHub Actions: jede Stunde alle Karten, alle 10 Minuten die Schnäppchen-Kandidaten |
| `recheck.py` | Misst die Kandidaten nach (`icons-live.json`) und schickt Push-Nachrichten |
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

## Schnäppchen-Flips (10–15 % pro Flip)

Der Tagesrhythmus über alle Karten bringt nur 2–3 %. Einzelne Karten fallen aber immer wieder kurz
deutlich unter ihren fairen Preis und kommen danach zurück. Darauf zielt die Schnäppchen-Liste. Jede
Bewertung nutzt nur Daten, die zu diesem Zeitpunkt schon bekannt waren.

1. **Fairer Preis** = 40. Perzentil der letzten 72 Stunden (mindestens 24 Messungen). Stunden mehr als
   20 % über dem unteren Viertel der Woche gelten als **Preisspitze** und zählen nicht mit. Bewusst das
   untere Viertel und nicht der Median: Dauert eine Spitze die halbe Datenlage, wäre sonst der Median
   selbst schon nach oben verzogen. Ledley King (2) ging zum Beispiel von 395k auf 544k und zurück auf
   370k. Das ist kein −19-%-Schnäppchen, sondern Normalniveau.
2. **Nach einer Spitze:** Liegt die Karte wieder auf oder über dem Preis vor der Spitze, ist sie kein
   Schnäppchen.
3. **Abwärtstrend:** Ist die Karte in mindestens 5 der letzten 6 Stunden gefallen, heißt es
   „Abwärtstrend“ statt „kaufen“.
4. **Schwankung:** Standardabweichung der letzten 48 Stunden in %, ohne die jüngsten 3 Stunden, damit
   der Dip selbst nicht mitzählt. Sortiert wird nach Dip ÷ Schwankung: ruhige Karten mit plötzlichem
   Dip stehen oben, wilde unten.
5. **Marktbereinigt:** Zählt nur der eigene Dip, also der Abschlag der Karte minus der Abschlag aller
   Icons bzw. Heroes. Liegt der Markt mindestens 3 % unter fair, gibt es keine Kaufempfehlung
   („Markt fällt“).
6. **Netto:** Gelistet wird nur, was mindestens 10 % eigenen Dip **und** mindestens 3.000 Coins
   Gewinn nach Steuer bringt (fairer Preis × 0,95 − Kaufpreis).

Die **Bilanz** spielt die Regel für die letzten 21 Tage durch: kaufen, sobald eine Karte als „kaufen“
gelistet worden wäre; verkaufen, sobald sie den fairen Preis wieder erreicht, spätestens nach 12
Stunden. Ausgewiesen wird das brutto und netto, für 8, 10 und 15 % eigenen Dip.

Auf der Seite steht zu jeder Karte ein **48-Stunden-Verlauf** (gestrichelt: fairer Preis). Ein
**Trade-Tagebuch** rechnet deine echten Trades netto. Es speichert nur im eigenen Browser.

Vor dem Kauf immer den Preis im Spiel prüfen. Die Liste ist der Stand der letzten stündlichen
Messung, die Uhrzeit dazu steht groß oben auf der Seite.

## Schneller als die Stunde: Nachmessen, Push, Live-Preis

Dips sind oft nach weniger als einer Stunde wieder weg. Deshalb:

- **Nachmessen alle 10 Minuten:** Jede Karte mit mindestens 8 % eigenem Dip landet auf einer
  Beobachtungsliste und wird zwischen den stündlichen Messungen alle 10 Minuten neu abgefragt
  (`recheck.py`, Ergebnis in `icons-live.json`). Bewertet wird nach denselben Regeln wie die
  stündliche Liste. Die Seite zeigt pro Karte, wann sie zuletzt gemessen wurde und ob der Dip
  **noch besteht** oder **vorbei** ist. Karten, die erst beim Nachmessen zum Schnäppchen werden,
  erscheinen mit „neu seit der letzten vollen Stunde“. Die Seite lädt sich alle 2 Minuten selbst neu.
- **Max-Kaufpreis** = fairer Preis × 0,95 − 3.000, abgerundet auf eine gültige Gebotsstufe (bis 1.000:
  50er-Schritte, bis 10.000: 100, bis 50.000: 250, bis 100.000: 500, darüber 1.000). Bis dahin lohnt
  sich auch ein Auktionsgebot.
- **„Live-Preis prüfen“** fragt EasySBC direkt aus dem Browser ab. EasySBC erlaubt das
  (`Access-Control-Allow-Origin: *`), es gibt also kein CORS-Problem. Angezeigt werden der aktuelle
  Preis, der eigene Dip, der Netto-Gewinn und ob die Karte noch unter dem Max-Kaufpreis liegt.

### Push aufs Handy einrichten

Sobald eine Karte zum Kaufen wird, schickt `recheck.py` eine Nachricht mit Name, aktuellem Preis,
Max-Kaufpreis, Zielpreis und Netto-Gewinn. Dieselbe Karte meldet sie höchstens alle 6 Stunden. Die
Zugangsdaten gehören in **GitHub → Settings → Secrets and variables → Actions → New repository
secret**, nie in den Code, denn das Repository ist öffentlich.

**ntfy (einfachste Variante):**
1. App „ntfy“ installieren (iOS/Android) und ein Thema mit einem schwer zu erratenden Namen
   abonnieren, z. B. `fut-flips-` plus 12 zufällige Zeichen.
2. Secret `NTFY_TOPIC` mit genau diesem Namen anlegen.
3. Empfohlen: kostenloses Konto auf ntfy.sh, dort einen Access-Token erzeugen und als `NTFY_TOKEN`
   hinterlegen. Ohne Token begrenzt ntfy.sh die Nachrichten pro IP-Adresse, und GitHub-Runner teilen
   sich IP-Adressen. Beim Testen war das Tageskontingent einer geteilten Adresse schon aufgebraucht.

**Telegram (zusätzlich oder statt ntfy):**
1. In Telegram mit `@BotFather` einen Bot anlegen und den Token als `TELEGRAM_BOT_TOKEN` hinterlegen.
2. Dem Bot eine Nachricht schreiben, dann
   `https://api.telegram.org/bot<TOKEN>/getUpdates` öffnen und die `chat.id` als `TELEGRAM_CHAT_ID`
   hinterlegen.

Geschickt wird über alle eingerichteten Kanäle. Schlägt ein Push überall fehl, wird er beim nächsten
10-Minuten-Takt erneut versucht.

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
python3 -m unittest fut/test_analyze.py fut/test_recheck.py
```

## Grenzen

- Die Preise sind der günstigste Sofortkauf. Ob man genau dazu kauft oder verkauft, hängt vom
  Markt in dem Moment ab.
- Eine Messung pro Stunde verpasst kurze Ausreißer innerhalb der Stunde.
- Promos und neue Content-Wellen verschieben das Preisniveau stärker als die Uhrzeit. Die
  72-Stunden-Normierung fängt Trends ab, plötzliche Brüche aber nur teilweise.
