# Rote-Karten-Studie

Eine Statistik-Untersuchung: **Wie oft gewinnt eine Mannschaft ein Spiel
noch, nachdem sie eine Rote Karte bekommen hat?** — aufgeschlüsselt nach
Minute, Spielstand in dem Moment und Stärke der Mannschaft.

Ausgewertet wird ausschließlich das **Endergebnis (1X2)**. Keine
Quotenbewegung, keine Live-Wetten, kein Trading. Später soll daraus eine
Wette werden: *Sieg der Mannschaft mit zehn Mann* — und nichts anderes.

> Dieser Ordner ist komplett eigenständig. Er fasst den Portal-Code
> (`public/`, `src/`, `static-app/`, `.github/`) nicht an.

---

## Was du brauchst

| | |
|---|---|
| Python | 3.9 oder neuer (`python3 --version`) |
| Paket | nur `requests` — `pip install requests` |
| API-Key | **nur für Phase 2 Variante (b)**, siehe unten |

Bewusst **kein** pandas, numpy oder BeautifulSoup. Alles andere kommt aus
Pythons Standardbibliothek, damit nichts installiert werden muss.

### Was du selbst besorgen musst

**Nichts für Phase 1.** Die Spieldaten von football-data.co.uk sind frei
und brauchen keine Anmeldung.

**Für Phase 2, Variante (b) — API-Football:**

1. Auf <https://www.api-football.com/> kostenlos registrieren
   (Free-Plan: 100 Anfragen pro Tag).
2. Den Key kopieren.
3. In diesem Ordner eine Datei `.env` anlegen — Vorlage ist
   `.env.example`:

   ```
   API_FOOTBALL_KEY=hier_dein_key
   ```

`.env` steht in `.gitignore` und landet **nie** im Repository. Der Key
wird ausschließlich als HTTP-Header verschickt, nie in einer URL und
nie in einer Log-Ausgabe.

---

## Ausführungsreihenfolge

Alle Befehle in diesem Ordner ausführen:

```bash
cd research/rote-karten
```

### Vorher: Selbsttest (optional, dauert eine Sekunde)

```bash
python3 test_parser.py
```

Prüft ohne Internet und ohne API-Key, ob beide Auslese-Varianten und die
Auswertungslogik richtig arbeiten.

### Phase 1 — Spiele holen

```bash
python3 01_fetch_matches.py
```

Lädt die Saison-CSVs von football-data.co.uk, behält die gebrauchten
Spalten und schreibt:

- `data/matches_all.csv` — alle Spiele (Basis für die Vergleichsgruppe)
- `data/matches_with_reds.csv` — nur Spiele mit mindestens einer Roten Karte

Dauert wenige Sekunden.

### Phase 2 — Minute, Team und Spielstand der Roten Karte

```bash
# Variante (a), Standard: FBref-Spielberichte auslesen
python3 02_fetch_events.py

# Variante (b): API-Football (braucht .env, siehe oben)
python3 02_fetch_events.py --source api-football
```

Ergibt `data/red_card_events.csv`.

Danach noch die Vergleichsgruppe (Spiele **ohne** Rote Karte) — die
braucht Phase 4:

```bash
python3 02_fetch_events.py --set baseline
# oder
python3 02_fetch_events.py --set baseline --source api-football
```

Ergibt `data/baseline_events.csv`.

**Das dauert lange, und das ist Absicht.** FBref wird mit mindestens
3 Sekunden Abstand angefragt, API-Football mit 7 Sekunden. Der
Fortschritt wird laufend in `data/events_progress_*.json` gesichert:
Abbrechen ist jederzeit erlaubt, der nächste Start macht dort weiter.

Nützliche Schalter:

| Schalter | Bedeutung |
|---|---|
| `--source fbref \| api-football` | Datenquelle (Standard: `fbref`) |
| `--set reds \| baseline` | Spiele mit bzw. ohne Rote Karte |
| `--limit 20` | höchstens 20 Spiele in diesem Lauf |
| `--pause 5` | Sekunden zwischen zwei Anfragen |
| `--budget 95` | max. API-Anfragen pro Lauf (nur API-Football) |
| `--retry-errors` | früher gescheiterte Spiele noch einmal versuchen |

### Phase 3 — Basisraten

```bash
python3 03_analyse.py
```

Schreibt:

- `data/basisraten.csv` — Zahlen zum Weiterrechnen
- `data/faelle.csv` — jeder Einzelfall, zum Nachprüfen von Hand
- `results/basisraten.md` — **die lesbare Tabelle**

### Phase 4 — Vergleich mit Spielen ohne Rote Karte

```bash
python3 04_baseline.py
```

Schreibt:

- `data/vergleich.csv`
- `results/vergleich.md` — **beide Raten nebeneinander**

Braucht `data/baseline_events.csv` aus Phase 2. Fehlt die, sagt die
erzeugte Datei genau das und nennt den fehlenden Befehl.

---

## Mehr Daten: Ligen und Saisons freischalten

Ganz oben in `01_fetch_matches.py` stehen zwei Listen. Zeilen
einkommentieren reicht:

```python
LEAGUES = {
    "E0": "Premier League",
    # "D1":  "Bundesliga",
    # "SP1": "La Liga",
    # "I1":  "Serie A",
    # "F1":  "Ligue 1",
}

SEASONS = {
    "2324": "2023/24",
    # "2425": "2024/25",
    # "2223": "2022/23",
}
```

**Warum das nötig sein wird:** eine einzelne Premier-League-Saison hat
380 Spiele, davon nur **53 mit Roter Karte**. Aufgeteilt auf sechs
Minuten-Abschnitte bleiben pro Gruppe unter zehn Fälle — daraus lässt
sich nichts ableiten. Für Gruppen mit 30+ Fällen brauchst du grob
**fünf Ligen über fünf Saisons** (rund 1300 Rote Karten).

Nach dem Freischalten Phase 1 bis 4 erneut laufen lassen. Phase 2
fragt nur die neu dazugekommenen Spiele ab — die alten stehen im
Fortschritt.

---

## Bekannte Hürde: FBref blockt

FBref sitzt hinter Cloudflare. Aus manchen Netzen (Server, Cloud,
Rechenzentrum) kommt **HTTP 403** und eine „Just a moment…"-Seite
zurück — dann kommen keine Daten, egal wie lange man wartet.

Aus der Umgebung, in der dieses Repo gebaut wurde, ist FBref genau so
blockiert. Zwei Auswege:

1. `02_fetch_events.py` **vom eigenen Rechner aus** starten — von einem
   normalen Heimanschluss funktioniert FBref meist.
2. `--source api-football` benutzen. Kostet einen kostenlosen Key,
   dafür sind 100 Anfragen pro Tag drin. Der Spielplan einer Liga
   kostet dabei nur **eine** Anfrage (wird zwischengespeichert), jedes
   Spiel danach ebenfalls eine.

Das Skript merkt beides selbst und schreibt eine klare Meldung. Es
bricht nicht mittendrin ab: jeder Fehler landet im Log und im
Fortschritt, der Rest läuft weiter. Erst nach fünf Fehlern in Folge
hört es auf — dann ist offensichtlich die Quelle weg und nicht ein
einzelnes Spiel kaputt.

---

## Dateien

```
research/rote-karten/
├── README.md                 diese Datei
├── common.py                 gemeinsame Helfer (Teamnamen, Statistik, HTTP)
├── 01_fetch_matches.py       Phase 1
├── 02_fetch_events.py        Phase 2
├── 03_analyse.py             Phase 3
├── 04_baseline.py            Phase 4
├── test_parser.py            Selbsttest ohne Netz und ohne API-Key
├── .env.example              Vorlage für den API-Key
├── data/                     Zwischenstände und Rohdaten
└── results/                  die lesbaren Ergebnisse
```

---

## Wie die Zahlen zustande kommen

**Stärke der Mannschaft.** Aus den Bet365-Schlussquoten, aber erst
nachdem die **Buchmacher-Marge herausgerechnet** wurde: von jeder Quote
`1/Quote` bilden, die drei Werte addieren, dann jeden Wert durch diese
Summe teilen. Ohne diesen Schritt hätte man keine Wahrscheinlichkeit,
sondern nur die Preisliste des Buchmachers — die Summe liegt sonst bei
rund 105 %.

**Gruppen.**

| Merkmal | Einteilung |
|---|---|
| Minute | 0–15, 16–30, 31–45, 46–60, 61–75, 76+ |
| Spielstand (aus Sicht der bestraften Mannschaft) | führt, unentschieden, 1 zurück, 2+ zurück |
| Ort | heim, auswärts |
| Stärke (faire Siegquote vor Anpfiff) | <1,50, 1,50–2,50, >2,50 |

**Das 95-%-Intervall** (nach Wilson) sagt, wie sicher eine Quote ist.
`30 % (19 – 44 %)` heißt: der wahre Wert liegt sehr wahrscheinlich
irgendwo zwischen 19 und 44 %. Ein breites Intervall = zu wenig Fälle.
Gruppen unter **30 Fällen** sind ausdrücklich mit
**„zu wenig Daten"** markiert — die sind als Zahl nicht zu gebrauchen.

**Was rausfliegt.**

- Nur die **erste** Rote Karte eines Spiels. Bei der zweiten wäre es
  9 gegen 11 oder 10 gegen 10 — ein völlig anderer Zustand.
- Spiele, bei denen der aus den Ereignissen **nachgezählte Endstand
  nicht zum gemeldeten Endstand passt**. Lieber einen Fall verwerfen,
  als ihn falsch zu zählen.

**Der Vergleich in Phase 4.** Zu jedem echten Rote-Karte-Fall wird ein
Zwilling gesucht: dieselbe Minute, derselbe Spielstand, dieselbe
Stärke, dasselbe Heimrecht — nur eben elf gegen elf. Sind zu wenige
Zwillinge da, wird schrittweise gröber gesucht; welche Ebene benutzt
wurde, steht in der Tabelle. Der Abstand zwischen beiden Raten ist der
eigentliche Preis der Karte.

---

## Grenzen — bitte vor dem Wetten lesen

- **Basisraten sind keine Wettstrategie.** Sie sagen, wie oft etwas
  passiert — nicht, ob die angebotene Quote dafür ausreicht. Ob sich
  eine Wette lohnt, entscheidet sich erst am Vergleich mit der Quote,
  die im Moment der Karte tatsächlich angeboten wird.
- **Live-Quoten stecken hier nicht drin.** Der Buchmacher sieht die
  Rote Karte genauso wie du und rechnet sie sofort ein.
- **Die Referenzminute in Phase 4** ist die Mitte des Abschnitts, die
  Kartenminute dagegen exakt. Innerhalb eines Abschnitts ist das ein
  kleiner Zeitversatz.
- **Die Vergleichsspiele sind nicht unabhängig:** dasselbe Spiel taucht
  in mehreren Minuten-Abschnitten auf. Deshalb steht auf der
  Vergleichsseite bewusst kein Konfidenzintervall.
