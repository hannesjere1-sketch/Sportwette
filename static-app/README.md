# Wettportal — statische Fassung

Das komplette Portal in einer einzigen HTML-Datei: Übersicht mit Bankroll-Verlauf und
Rendite-Kennzahlen, Wettenverwaltung mit Abrechnung, Spielplan und Einsatzstrategie.

Es braucht **keinen Server und keine Datenbank** — die Datei läuft in jedem Browser und
speichert die Daten lokal im Browser (`localStorage`). Damit lässt sie sich auf jeden
beliebigen Webspace legen, auch mit eigener Domain.

## Lokal ansehen

```bash
cd static-app
python3 -m http.server 4300
```

Dann <http://localhost:4300> öffnen. (Direktes Öffnen der Datei per Doppelklick geht auch,
nur die Schriften werden dann je nach Browser nicht geladen.)

## Veröffentlichen

Der Ordner `static-app/` ist bereits ein fertiges Web-Verzeichnis. Alles, was ein Hoster
braucht, ist dieser Ordner:

- **Netlify / Vercel / Cloudflare Pages** — Repository verbinden, als Publish-Verzeichnis
  `static-app` angeben, fertig. Eigene Domain wird in den Projekteinstellungen hinterlegt.
- **Klassischer Webspace** — `index.html` per FTP ins Web-Verzeichnis kopieren.

## Grenzen dieser Fassung

- **Die Daten liegen im Browser.** PC und Handy führen damit getrennte Bestände. Über
  *Einstellungen → Datensicherung* lässt sich der Stand als Datei sichern und auf einem
  anderen Gerät einspielen.
- **Kein automatischer Spielplan-Import.** Partien werden von Hand eingetragen.

Die Fassung im Projektstammverzeichnis (Next.js + PostgreSQL) hebt beide Grenzen auf:
Daten liegen dort in einer Datenbank und werden zwischen allen Geräten geteilt, und der
Spielplan lässt sich über football-data.org automatisch befüllen.
