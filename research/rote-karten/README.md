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
| Pakete | `requests`, dazu optional `brotli` — `pip install -r requirements.txt` |
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

---

## Lokal ausführen (Windows, Schritt für Schritt)

Geschrieben für jemanden, der so etwas zum ersten Mal macht. Jeder Block
ist ein Befehl zum Kopieren. Nach jedem Befehl **Enter** drücken und
warten, bis wieder eine neue Zeile erscheint.

### Schritt 1 — Python installieren

Auf <https://www.python.org/downloads/> die Schaltfläche
*Download Python* anklicken und die Datei starten.

> **Wichtig:** Im Installationsfenster ganz unten das Häkchen bei
> **„Add python.exe to PATH"** setzen, *bevor* du auf *Install Now*
> klickst. Ohne dieses Häkchen findet Windows den Befehl `python`
> später nicht.

### Schritt 2 — Git installieren

Auf <https://git-scm.com/download/win> herunterladen und installieren.
Alle Vorgaben können so bleiben, wie sie sind — einfach durchklicken.

### Schritt 3 — PowerShell öffnen

Windows-Taste drücken, `powershell` tippen, Enter.

Es öffnet sich ein blaues oder schwarzes Fenster. Da kommen alle
folgenden Befehle hinein.

### Schritt 4 — Prüfen, ob beides da ist

```powershell
python --version
```

```powershell
git --version
```

Beide Befehle müssen eine Versionsnummer ausgeben, zum Beispiel
`Python 3.12.4`. Kommt stattdessen eine Fehlermeldung, ist bei Schritt 1
oder 2 etwas schiefgegangen — am häufigsten fehlt das PATH-Häkchen.
Dann Python noch einmal installieren und das Häkchen setzen.

### Schritt 5 — Repo herunterladen

Erst in den eigenen Dokumente-Ordner wechseln:

```powershell
cd $HOME\Documents
```

Dann das Repo holen:

```powershell
git clone https://github.com/hannesjere1-sketch/Sportwette.git
```

In den heruntergeladenen Ordner wechseln:

```powershell
cd Sportwette
```

### Schritt 6 — Auf den richtigen Branch wechseln

Die Studie liegt nicht im Haupt-Branch, sondern in einem eigenen:

```powershell
git checkout research/rote-karten
```

Danach in den Ordner der Studie:

```powershell
cd research\rote-karten
```

### Schritt 7 — Eigene Python-Umgebung anlegen

Damit die Installation nichts an deinem restlichen System verändert:

```powershell
python -m venv .venv
```

Und die Umgebung einschalten:

```powershell
.\.venv\Scripts\Activate.ps1
```

Danach steht am Zeilenanfang `(.venv)`. **Das muss bei jedem weiteren
Befehl dort stehen.**

> **Wenn eine rote Fehlermeldung mit „Die Ausführung von Skripten ist
> auf diesem System deaktiviert" kommt:** einmal diesen Befehl ausführen
> und dann den Aktivierungsbefehl oben wiederholen.
>
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```
>
> Das gilt nur für dieses eine Fenster und ändert nichts dauerhaft.

### Schritt 8 — Das benötigte Paket installieren

```powershell
pip install -r requirements.txt
```

Es wird genau ein Paket installiert: `requests`.

### Schritt 9 — Selbsttest

```powershell
python test_parser.py
```

Am Ende muss **„Alle Tests bestanden."** stehen. Das läuft ohne
Internet und ohne API-Key und dauert eine Sekunde.

### Schritt 10 — Phase 1: Spiele holen

```powershell
python 01_fetch_matches.py
```

Dauert wenige Sekunden. Danach liegen `data/matches_all.csv` und
`data/matches_with_reds.csv` im Ordner.

### Schritt 11 — Phase 2: Rote Karten holen

```powershell
python 02_fetch_events.py
```

**Das dauert rund 6 Minuten** und sieht die meiste Zeit so aus, als
würde nichts passieren — das ist richtig so, das Skript wartet zwischen
den Anfragen. Alle fünf Spiele kommt eine Fortschrittsmeldung.

Danach die Vergleichsgruppe:

```powershell
python 02_fetch_events.py --set baseline
```

**Das dauert rund 33 Minuten.** Du kannst das Fenster jederzeit mit
`Strg + C` abbrechen oder einfach schließen — beim nächsten Start macht
das Skript genau dort weiter. Es geht höchstens das eine Spiel verloren,
das gerade lief.

### Schritt 12 — Auswerten

```powershell
python 03_analyse.py
```

```powershell
python 04_baseline.py
```

Die Ergebnisse liegen dann in `results\basisraten.md` und
`results\vergleich.md`. Beide Dateien lassen sich mit jedem Texteditor
öffnen — oder mit einem Doppelklick, wenn du VS Code installiert hast.

### Schritt 13 — Ergebnisse zurück ins Repo (optional)

Damit die Ergebnisse auch auf GitHub landen und nicht nur auf deinem PC:

```powershell
git add data results
```

```powershell
git commit -m "Ergebnisse vom lokalen Lauf"
```

```powershell
git push origin research/rote-karten
```

Beim ersten `git push` fragt Windows nach deinem GitHub-Login. Das
Fenster, das aufgeht, einmal durchklicken — danach merkt Windows sich
das.

### Beim nächsten Mal

Wenn du später weiterarbeiten willst, brauchst du nur noch:

```powershell
cd $HOME\Documents\Sportwette\research\rote-karten
```

```powershell
.\.venv\Scripts\Activate.ps1
```

Schritt 1 bis 8 sind einmalig.

### Wenn etwas nicht klappt

| Fehlermeldung | Was zu tun ist |
|---|---|
| `python : Die Benennung "python" wurde nicht erkannt` | Python neu installieren, Häkchen bei „Add python.exe to PATH" setzen |
| `Die Ausführung von Skripten ist auf diesem System deaktiviert` | siehe Kasten in Schritt 7 |
| `FBref HTTP 403 … Cloudflare` | FBref blockt deinen Anschluss. Entweder `--source api-football` oder Seiten von Hand speichern und `--from-cache` benutzen (siehe unten) |
| `Kein FBref-Spielbericht gefunden` | einzelne Spiele fehlen bei FBref. Der Lauf geht weiter, das ist kein Abbruch |
| `Abbruch: 5 Fehler in Folge` | die Quelle ist gerade nicht erreichbar. Später mit `--retry-errors` erneut starten |
| `data\matches_with_reds.csv fehlt` | Schritt 10 wurde übersprungen |

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
Auswertungslogik richtig arbeiten — unter anderem an einem echten,
von Hand gespeicherten FBref-Spielbericht unter
`data/sample/sample.html` (Burnley – Manchester City, 11.08.2023) und an
einer echten Spielplanseite unter `data/sample/sample_schedule.html`
(Premier League 2023/24, 380 Spiele).

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

**Das dauert lange, und das ist Absicht.** FBref wird mit 6 Sekunden
Abstand angefragt, API-Football mit 7 Sekunden — gemessen ab dem *Ende*
der vorigen Anfrage, damit eine langsame Antwort die Pause nicht
auffrisst. Bei einer Premier-League-Saison heißt das rund **6 Minuten**
für die Rote-Karten-Spiele und rund **33 Minuten** für die
Vergleichsgruppe.

Der Fortschritt wird **nach jedem einzelnen Spiel** in
`data/events_progress_*.json` gesichert. Abbrechen ist jederzeit
erlaubt — mit `Strg + C` oder indem du das Fenster zumachst. Der
nächste Start überspringt alles, was schon geholt wurde; verloren geht
höchstens das eine Spiel, das gerade lief.

Nützliche Schalter:

| Schalter | Bedeutung |
|---|---|
| `--source fbref \| api-football` | Datenquelle (Standard: `fbref`) |
| `--set reds \| baseline` | Spiele mit bzw. ohne Rote Karte |
| `--limit 20` | höchstens 20 Spiele in diesem Lauf |
| `--pause 8` | Sekunden zwischen zwei Anfragen (Standard: 6 bei FBref, 7 bei API-Football; nie schneller als 3) |
| `--budget 95` | max. API-Anfragen pro Lauf (nur API-Football) |
| `--retry-errors` | früher gescheiterte Spiele noch einmal versuchen |
| `--from-cache` | **nur** gespeicherte HTML-Dateien aus `data/cache/` benutzen, gar keine Netzabrufe |
| `--list-missing` | auflisten, welche Dateien in `data/cache/` noch fehlen — mit Adresse und genauem Dateinamen |

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

FBref sitzt hinter Cloudflare. Kommt **HTTP 403** und eine
„Just a moment…"-Seite zurück, wurde der Abruf für einen Bot gehalten.

Dagegen ist Folgendes eingebaut:

- **Vollständige Browser-Kopfzeilen.** Nicht nur ein User-Agent, sondern
  auch `Accept`, `Accept-Language`, `Accept-Encoding` und die
  `Sec-Fetch-*`-Zeilen, die jeder Chrome mitschickt. Ein nackter
  User-Agent fällt sofort auf, weil der Rest fehlt.
- **Eine gemeinsame Verbindung (Session).** Damit bleiben die Cookies
  erhalten, die Cloudflare beim ersten Aufruf setzt. Einzelne,
  voneinander unabhängige Anfragen wirken dagegen wie ein Bot.
- **Zwei Wiederholversuche** nach einer Abweisung, mit wachsender
  Wartezeit (20 s, dann 60 s). Erst danach gilt das Spiel als
  gescheitert.
- **Ein Zwischenspeicher.** Jede geholte Seite landet als HTML-Datei
  unter `data/cache/` und wird nie zweimal geholt. Der Spielplan einer
  Liga kostet also genau **eine** Anfrage im Leben, nicht eine pro Spiel.

Hilft das alles nicht, gibt es zwei Auswege — der zweite funktioniert
immer:

1. `--source api-football` benutzen (kostenloser Key, siehe oben).
2. Die Seiten von Hand im Browser speichern und mit `--from-cache`
   einlesen. Der Browser kommt ja durch.

---

## Seiten von Hand speichern (`--from-cache`)

`--from-cache` macht **keinen einzigen Netzabruf**. Es liest
ausschließlich HTML-Dateien aus `data/cache/`. Damit das Skript sie
findet, müssen die Dateinamen exakt stimmen.

### So heißen die Dateien

| Was | Dateiname | Beispiel |
|---|---|---|
| Spielplan einer Liga/Saison | `schedule_<LIGA>_<SAISON>.html` | `schedule_E0_2324.html` |
| Ein Spielbericht | `match_<match_id>.html` | `match_E0-2324-2023-08-11-burnley-man-city.html` |

`<LIGA>` und `<SAISON>` sind dieselben Kürzel wie in
`01_fetch_matches.py` (`E0`, `2324`). Die `match_id` steht in der ersten
Spalte von `data/matches_with_reds.csv` — du musst sie dir aber nicht
selbst zusammenbauen, siehe nächster Abschnitt.

### Der Ablauf

**Schritt 1 — fragen, was fehlt:**

```powershell
python 02_fetch_events.py --from-cache --list-missing
```

Das gibt für jede fehlende Seite den **genauen Dateinamen** und die
**Adresse zum Öffnen** aus. Zuerst kommen die Spielpläne — ohne die
kennt das Skript die Adressen der einzelnen Spielberichte gar nicht.

**Schritt 2 — Seite im Browser speichern:**

Adresse öffnen, warten bis die Seite ganz geladen ist, dann `Strg + S`.
Im Speichern-Fenster bei *Dateityp* **„Webseite, nur HTML"** wählen —
nicht „Webseite, vollständig", das legt zusätzlich einen Ordner mit
Bildern an, den wir nicht brauchen.

Als Speicherort `data\cache` wählen und den Dateinamen aus Schritt 1
eintragen. Windows hängt gern ein `.htm` an — die Datei muss am Ende
wirklich auf `.html` enden.

**Schritt 3 — Schritt 1 wiederholen.** Sobald der Spielplan da ist,
listet `--list-missing` auch alle Spielberichte mit Adresse auf.

**Schritt 4 — auswerten, ohne Netz:**

```powershell
python 02_fetch_events.py --from-cache
```

### Lohnt sich das?

Für die 53 Spiele mit Roter Karte: 1 Spielplan + 53 Berichte = 54 Seiten
von Hand. Das ist eine knappe Stunde stumpfe Arbeit, aber es
funktioniert garantiert.

Für die Vergleichsgruppe mit 327 Spielen wäre das unzumutbar — falls
FBref dauerhaft blockt, ist dafür `--source api-football` der richtige
Weg.

> Der Ordner `data/cache/` steht in `.gitignore`. Die Seiten bleiben auf
> deinem Rechner und landen nicht im Repository — eine einzelne Seite
> ist rund 200 KB groß.

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
├── requirements.txt          das eine benötigte Paket
├── .env.example              Vorlage für den API-Key
├── data/                     Zwischenstände und Rohdaten
│   └── cache/                 gespeicherte HTML-Seiten (nicht im Repo)
│   └── sample/                echte FBref-Seiten für den Selbsttest
│       ├── sample.html            ein Spielbericht
│       └── sample_schedule.html   eine Spielplanseite
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
