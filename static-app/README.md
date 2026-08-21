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

### Nächste Spiele je Team

Der Spielplan zeigt oben für jedes der 13 Teams die **nächsten drei Partien**, mit Wochentag,
Anstoßzeit und Gegner; „bei“ steht für ein Auswärtsspiel, „gegen“ für ein Heimspiel. Die
nächste Partie ist farblich hervorgehoben. Ein Spiel zwischen zwei eigenen Teams erscheint bei
beiden.

Gespeist wird das aus den von Hand eingetragenen Partien. Beim Eintragen schlägt ein
Auswahlfeld die eigenen Teams vor, und abweichende Groß-/Kleinschreibung wird automatisch auf
die Schreibweise der Liste zurückgeführt — sonst würde die Partie dem Team nicht zugeordnet.

## Was diese Fassung nicht kann

- **Kein automatischer Spielplan-Import.** Partien werden von Hand eingetragen; ein
  eingetragenes Spiel lässt sich mit einem Klick in eine Wette überführen.
- **Kein Tipico-Import.** Die Browser-Erweiterung in `extension/` spricht mit der
  Next.js-Fassung im Projektstammverzeichnis, nicht mit dieser Seite.
