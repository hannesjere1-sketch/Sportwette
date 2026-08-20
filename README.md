# Wettportal

Persönliches Portal zum Verwalten einer Sportwetten-Strategie: alle Wetten an einem Ort,
Bankroll- und Performance-Charts, sowie ein Spielplan der kommenden Spiele der Top-5-Fußballligen.

## Features

- **Dashboard**: Bankroll, Gesamt-Profit, ROI und Trefferquote auf einen Blick, plus
  Bankroll-Verlauf und Profit-nach-Liga als Charts.
- **Wetten**: Alle Wetten erfassen, bearbeiten, abrechnen (gewonnen/verloren/storniert/rückerstattet)
  und filtern.
- **Spielplan**: Kommende Spiele der Premier League, Bundesliga, La Liga, Serie A und Ligue 1 —
  entweder automatisch über [football-data.org](https://www.football-data.org/client/register)
  synchronisiert oder manuell gepflegt. Direkt aus dem Spielplan heraus lässt sich eine Wette
  vorausgefüllt anlegen.
- **Einstellungen**: Startkapital und Staking-Strategie (fester Einsatz, Prozent der Bankroll oder
  Kelly-Kriterium) konfigurieren — der vorgeschlagene Einsatz beim Anlegen einer neuen Wette
  richtet sich danach.
- **Tipico-Import per Browser-Erweiterung**: Wette bei Tipico platzieren, Erweiterungs-Icon
  klicken, erkannte Felder prüfen und mit einem Klick ins Portal übernehmen — siehe
  [`extension/README.md`](./extension/README.md).

## Tech-Stack

- [Next.js](https://nextjs.org) (App Router) + TypeScript
- [Prisma](https://www.prisma.io) + PostgreSQL
- Tailwind CSS für das Styling
- [Recharts](https://recharts.org) für die Charts

## Setup (lokal)

Braucht eine erreichbare PostgreSQL-Datenbank — lokal per Docker oder eine kostenlose Cloud-DB
(z. B. [Neon](https://neon.tech)) funktioniert gleichermaßen.

```bash
npm install
cp .env.example .env
# DATABASE_URL in .env auf die eigene Postgres-Instanz anpassen
npm run dev
```

`npm run dev` bzw. `npm run build` wenden beim Start automatisch ausstehende Migrationen an
(`prisma migrate deploy`). Danach [http://localhost:3000](http://localhost:3000) öffnen.

## Deployment auf Vercel

1. Projekt auf [vercel.com](https://vercel.com) importieren (GitHub-Repo, gewünschten Branch wählen).
2. Im Vercel-Projekt unter **Storage** eine Postgres-Datenbank verbinden (z. B. die Neon-Integration —
   kostenloser Tier reicht). Das setzt automatisch eine `DATABASE_URL`-Umgebungsvariable.
   Falls die Integration die Variable anders benennt (z. B. `POSTGRES_PRISMA_URL`), unter
   **Settings → Environment Variables** zusätzlich eine `DATABASE_URL` mit demselben Wert anlegen.
3. Deploy anstoßen (bzw. erneut deployen, falls die DB erst nach dem ersten Deploy verbunden wurde) —
   der Build-Schritt führt `prisma migrate deploy` automatisch aus, bevor die App gebaut wird.

Wichtig: SQLite funktioniert auf Vercel **nicht**, da Serverless-Functions kein persistentes
Dateisystem haben — daher die PostgreSQL-Anbindung oben.

### Spielplan-Synchronisation (optional)

Um den Spielplan automatisch zu befüllen, kostenlosen Token unter
[football-data.org](https://www.football-data.org/client/register) holen und entweder in `.env`
als `FOOTBALL_DATA_API_TOKEN` oder direkt in den App-Einstellungen unter **Einstellungen** eintragen.
Ohne Token lassen sich Spiele weiterhin manuell im Spielplan anlegen.

## Datenmodell

- `Bet`: eine platzierte Wette (Liga, Teams, Markt, Tipp, Quote, Einsatz, Status, Auszahlung).
- `Fixture`: ein Spiel im Spielplan (aus der API synchronisiert oder manuell angelegt).
- `Settings`: Singleton-Datensatz mit Startkapital, Staking-Strategie, API-Token und dem
  API-Key für den `/api/bets/import`-Endpunkt (Browser-Erweiterung).

## Weiterentwicklung

Bewusst nicht enthalten (siehe Projekt-Scope): automatischer Wettabschluss bei einem Buchmacher.
Das Portal unterstützt aktuell die manuelle Erfassung von Wetten plus automatisierten Spielplan-Import;
eine echte Strategie-Engine (z. B. Value-Bet-Erkennung anhand von Live-Quoten) lässt sich auf Basis
von `src/lib/betting.ts` und `src/lib/football-data.ts` ergänzen.
