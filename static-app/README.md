# Wettportal — Webseiten-Fassung

Das komplette Portal in einer einzigen HTML-Datei: Übersicht mit Bankroll-Verlauf und
Rendite-Kennzahlen, Wettenverwaltung mit Abrechnung, Spielplan und Einsatzstrategie.

Kein Build-Schritt, kein Server, keine Abhängigkeiten — die Datei läuft auf jedem Webspace.
Für den Abgleich zwischen mehreren Geräten kann sie sich optional mit einem kostenlosen
Supabase-Projekt verbinden.

## Wo die Daten liegen

Die Seite wählt automatisch den besten verfügbaren Speicher:

| Zustand | Wo die Wetten liegen | Geräteabgleich |
|---|---|---|
| Ohne Anmeldung | im Browser (`localStorage`) | nein |
| Mit Supabase-Konto | in deinem Supabase-Projekt | **ja** |
| Als claude.ai-Artifact | in der Artifact-Seite selbst | ja, über denselben Link |

Der Stand im Browser wird immer zusätzlich geschrieben — die Seite funktioniert also auch
ohne Netz weiter und gleicht ab, sobald sie wieder verbunden ist.

## Geräteabgleich einrichten (einmalig, ca. 5 Minuten)

### 1. Supabase-Projekt anlegen

Auf [supabase.com](https://supabase.com) kostenlos registrieren und ein neues Projekt anlegen.
Die Region ruhig auf Frankfurt/EU stellen.

### 2. Tabelle anlegen

Im Projekt links auf **SQL Editor** → **New query**, das Folgende einfügen und ausführen:

```sql
create table public.portal_state (
  user_id    uuid primary key references auth.users(id) on delete cascade default auth.uid(),
  data       jsonb       not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.portal_state enable row level security;

create policy "own row read"   on public.portal_state
  for select using (auth.uid() = user_id);
create policy "own row insert" on public.portal_state
  for insert with check (auth.uid() = user_id);
create policy "own row update" on public.portal_state
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

Die drei Regeln sorgen dafür, dass jedes Konto ausschließlich die eigene Zeile sieht — auch
wenn der öffentliche Schlüssel aus Schritt 3 bekannt ist.

### 3. Zugangsdaten in die Seite eintragen

In Supabase unter **Project Settings → API** stehen zwei Werte:

- **Project URL** (`https://….supabase.co`)
- **anon public** — der öffentliche Schlüssel. Dieser darf in der Webseite stehen; er gewährt
  für sich genommen keinen Datenzugriff, das erledigen die Regeln aus Schritt 2.
  Der `service_role`-Schlüssel gehört **nie** in die Seite.

Beides im Portal unter **Einstellungen → Konto & Geräteabgleich** eintragen, auf *Verbinden*
klicken, danach **Konto anlegen** mit E-Mail und Passwort.

> Supabase verschickt standardmäßig eine Bestätigungsmail. Wer sich das sparen will,
> schaltet unter **Authentication → Sign In / Providers → Email** die Option
> *Confirm email* ab.

### 4. Zweites Gerät

Dieselbe Seite öffnen, dieselbe Projekt-URL und denselben Schlüssel eintragen und sich mit
den gleichen Zugangsdaten **anmelden**. Ab dann sehen beide Geräte denselben Stand.

## Veröffentlichen

### GitHub Pages (eingerichtet)

`.github/workflows/deploy-pages.yml` veröffentlicht diesen Ordner bei jedem Push automatisch.
Einmalig muss die Quelle aktiviert werden: im Repository **Settings → Pages → Build and
deployment → Source: GitHub Actions**. Danach läuft die Seite dauerhaft unter
<https://hannesjere1-sketch.github.io/Sportwette/>.

### Andere Hoster

Der Ordner `static-app/` ist ein fertiges Web-Verzeichnis:

- **Netlify / Cloudflare Pages / Vercel** — Repository verbinden, Publish-Verzeichnis
  `static-app`, kein Build-Befehl.
- **Klassischer Webspace** — `index.html` per FTP hochladen.

Eine eigene Domain wird bei allen genannten Anbietern in den Projekteinstellungen hinterlegt.

## Lokal ansehen

```bash
cd static-app && python3 -m http.server 4300
```

Dann <http://localhost:4300> öffnen.

## Die Strategie, die dieses Portal misst

Gewettet wird auf **Sieg (1X2)** eines Teams aus der eigenen Liste, das **vor Minute 35**
mit **genau einem Tor** zurückliegt.

Das Portal nimmt **ausschließlich** solche Wetten auf. Verstößt eine Eingabe gegen eine der
Regeln, bleibt der Dialog offen und nennt den Grund — gespeichert wird nichts. Schon beim
Tippen zeigt ein Hinweis unter dem Formular, ob die Wette zulässig ist. Dadurch enthält der
Datenbestand nur Wetten der Strategie, und jede Kennzahl bezieht sich auf genau diese Menge.

Konkret sind fest verdrahtet:

- **Wettmarkt** — „Sieg (1X2)“, nicht änderbar
- **Rückstand** — genau ein Tor, nicht änderbar
- **Minute** — Eingabefeld, aber auf 1–34 begrenzt
- **Team, Liga, Spielort** — Auswahllisten, kein Freitext

Ein Team, auf das bereits Wetten laufen, lässt sich nicht aus der Liste entfernen; sonst
verlören diese Wetten ihre Grundlage. Die Meldung nennt die Anzahl der betroffenen Wetten.

### Die Messlatte

| Kennzahl | Bedeutung |
|---|---|
| Trefferquote | gewonnen ÷ entschieden (annullierte Wetten zählen nicht als Versuch) |
| Ø-Quote | Durchschnitt aller gewerteten Quoten |
| Benötigte Quote | 1 ÷ Ø-Quote — ab hier ist die Strategie profitabel |
| Yield | Gewinn ÷ Summe der Einsätze |

Liegt die Trefferquote über der benötigten, erscheint dort ein grünes ▲, sonst ein rotes ▼.

### Teamliste

Die 13 Teams sind vorbelegt und werden unter **Einstellungen → Meine Teams** gepflegt.
Männer- und Frauenmannschaften desselben Vereins sind **getrennte Einträge**
(`FC Bayern München` und `FC Bayern München (F)`) — sie spielen in verschiedenen Ligen und
dürfen in der Team-Auswertung nie zusammenfallen.

### Spielplan-Import

Ein zweiter Workflow (`.github/workflows/update-fixtures.yml`) holt täglich um 04:00 UTC die
Partien der kommenden 14 Tage und schreibt sie nach `public/fixtures.json`. Er lässt sich unter
**Actions → Spielplan aktualisieren → Run workflow** auch von Hand starten.

Einmalig einzurichten: unter **Settings → Secrets and variables → Actions → New repository
secret** ein Secret namens `FOOTBALL_DATA_TOKEN` mit dem Token von
[football-data.org](https://www.football-data.org/client/register) anlegen.

Zur Sicherheit:

- Der Token wird dem Skript nur als Umgebungsvariable übergeben und als Header `X-Auth-Token`
  gesendet — er steht in keiner URL, keinem Kommandoaufruf und keinem Log.
- Er landet **nie** in `fixtures.json` und **nie** im Frontend.
- Die veröffentlichte Seite ruft selbst keinen externen Dienst auf. Ihr einziger Netzzugriff ist
  die lokale `fixtures.json` (plus Google Fonts und, falls eingerichtet, das eigene
  Supabase-Projekt).

Abgefragt werden die fünf Wettbewerbe des kostenlosen Tarifs: BL1, PL, PD, SA, FL1. Das Skript
kommt mit **einer** Anfrage aus; scheitert die kombinierte Abfrage, verteilt es fünf Einzelabfragen
mit sieben Sekunden Abstand — beides bleibt klar unter dem Limit von zehn Anfragen pro Minute.

Die API-Schreibweisen werden auf die Namen der Teamliste zurückgeführt (`Arsenal FC` → `Arsenal`,
`FC Internazionale Milano` → `Inter`). Die Reihenfolge der Regeln ist dabei wesentlich: `Inter`
wird vor `AC Milan` geprüft, sonst landete Inter wegen „Milano“ beim Stadtrivalen.

**Frauen-Bundesliga:** Im kostenlosen Tarif nicht enthalten. Partien von `FC Bayern München (F)`
trägst du weiterhin von Hand ein.

### Manuelle Partien

Importierte und selbst eingetragene Partien werden getrennt gehalten: Der Import liegt nur im
Arbeitsspeicher, gespeichert werden ausschließlich deine eigenen Einträge. Ein Lauf des Workflows
kann sie deshalb nicht überschreiben. In der Liste tragen sie die Markierung **manuell** und sind
die einzigen, die sich entfernen lassen. Deckt sich ein Import mit einem eigenen Eintrag
(gleiche Paarung, gleicher Tag), hat der eigene Vorrang.

### Nächste Spiele je Team

Der Spielplan zeigt oben für jedes der 13 Teams die **nächsten drei Partien**, mit Wochentag,
Anstoßzeit und Gegner; „bei“ steht für ein Auswärtsspiel, „gegen“ für ein Heimspiel. Die
nächste Partie ist farblich hervorgehoben. Ein Spiel zwischen zwei eigenen Teams erscheint bei
beiden.

Gespeist wird das aus den von Hand eingetragenen Partien. Beim Eintragen schlägt ein
Auswahlfeld die eigenen Teams vor, und abweichende Groß-/Kleinschreibung wird automatisch auf
die Schreibweise der Liste zurückgeführt — sonst würde die Partie dem Team nicht zugeordnet.

## Analyse-Tab

Getrennt vom Wett-Journal — keine Einsätze, keine Quoten, kein Geld. Er beantwortet eine
einzige Frage: **Wie oft gewinnt eines der Teams noch, nachdem es früh das erste Gegentor
kassiert hat?**

Der Trigger, genau:

- eines der Teams kassiert das **erste Tor der Partie**
- dieses Tor fällt **vor Minute 35**
- der Einstiegszeitpunkt ist die Minute dieses Tores, nicht Minute 35
- **Treffer** ist nur ein Sieg; Unentschieden und Niederlage zählen beide als Fehlschlag
- fällt das Team danach weiter zurück und gewinnt trotzdem, bleibt es ein Treffer
- höchstens ein Trigger je Spiel — durch die Regel „erstes Tor" ohnehin eindeutig
- Eigentore zählen als reguläre Tore, gutgeschrieben der Seite, der sie nützen

Weil nur das *erste* Tor zählt, kann ein Spielstand wie 1:1 oder 2:1 nie als Trigger
durchgehen: dort hat das eigene Team vorher getroffen. Ein Halbzeitstand allein könnte das
nicht unterscheiden — 1:1 zur Pause entsteht aus 0:1 ebenso wie aus 1:0. Deshalb wertet der
Aufbau die Torreihenfolge aus, nicht den Zwischenstand.

### Datenquelle

Alles kommt von [API-Football](https://www.api-football.com) über das Secret
`API_FOOTBALL_KEY`. Deren Spielliste enthält bereits den Halbzeitstand, deshalb genügt eine
Quelle. Zwei Quellen zu mischen wäre eine Fehlerquelle: Die Dienste schreiben Vereine
unterschiedlich („Bayern Munich" gegen „FC Bayern München"), und jede übersehene Schreibweise
ließe Fälle still verschwinden.

Der Spielplan-Tab bleibt davon unberührt und wird weiter von football-data.org gespeist.

### Wie der Aufbau das Tageslimit einhält

Der kostenlose Zugang erlaubt 100 Anfragen pro Tag. Der Lauf verbraucht höchstens 95 und
schreibt seinen Stand nach `data/analysis-state.json`; am nächsten Tag macht er dort weiter.

Entscheidend ist der Vorfilter: Torereignisse werden **nur** für Spiele abgefragt, in denen der
Gegner zur Halbzeit mindestens ein Tor erzielt hatte. Bei 0:0 oder eigener Führung zur Pause ist
ein Trigger vor Minute 35 ausgeschlossen — diese Spiele kosten keine Anfrage. Gemessen an den
verfügbaren Saisons: 1.396 Spiele der Teams, davon brauchen 515 eine Abfrage. Der Filter spart
63 % und der Aufbau ist in gut einer Woche durch.

Ein Spiel zwischen zwei verfolgten Teams wird mit **einer** Abfrage für beide Seiten ausgewertet.

### Eingebaute Gegenprobe

Aus den Torereignissen wird der Spielstand nachgebaut und mit dem gemeldeten Endstand
verglichen. Stimmen sie nicht überein — etwa weil ein Eigentor falsch zugeordnet wurde oder
Ereignisse fehlen —, wird der Fall **verworfen statt falsch gewertet** und in der
Fortschrittsanzeige als übersprungen ausgewiesen.

### Saisons

Erfasst wird, was der Tarif hergibt; das Skript stellt selbst fest, welche Saisons zugänglich
sind, und vermerkt den Rest als nicht abgedeckt. Bei football-data.org sind 2021/22 und 2022/23
gesperrt, bei API-Football prüft der erste Lauf es nach.

## Was diese Fassung nicht kann

- **Keine Frauen-Bundesliga im Import.** Der kostenlose Tarif von football-data.org deckt sie
  nicht ab; diese Partien werden von Hand eingetragen.
- **Kein Tipico-Import.** Die Browser-Erweiterung in `extension/` spricht mit der
  Next.js-Fassung im Projektstammverzeichnis, nicht mit dieser Seite.
