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

## Tech-Stack

- [Next.js](https://nextjs.org) (App Router) + TypeScript
- [Prisma](https://www.prisma.io) + SQLite als lokale Datenbank
- Tailwind CSS für das Styling
- [Recharts](https://recharts.org) für die Charts

## Setup

```bash
npm install
cp .env.example .env
npx prisma migrate deploy
npm run dev
```

Danach [http://localhost:3000](http://localhost:3000) öffnen.

### Spielplan-Synchronisation (optional)

Um den Spielplan automatisch zu befüllen, kostenlosen Token unter
[football-data.org](https://www.football-data.org/client/register) holen und entweder in `.env`
als `FOOTBALL_DATA_API_TOKEN` oder direkt in den App-Einstellungen unter **Einstellungen** eintragen.
Ohne Token lassen sich Spiele weiterhin manuell im Spielplan anlegen.

## Datenmodell

- `Bet`: eine platzierte Wette (Liga, Teams, Markt, Tipp, Quote, Einsatz, Status, Auszahlung).
- `Fixture`: ein Spiel im Spielplan (aus der API synchronisiert oder manuell angelegt).
- `Settings`: Singleton-Datensatz mit Startkapital, Staking-Strategie und API-Token.

## Weiterentwicklung

Bewusst nicht enthalten (siehe Projekt-Scope): automatischer Wettabschluss bei einem Buchmacher.
Das Portal unterstützt aktuell die manuelle Erfassung von Wetten plus automatisierten Spielplan-Import;
eine echte Strategie-Engine (z. B. Value-Bet-Erkennung anhand von Live-Quoten) lässt sich auf Basis
von `src/lib/betting.ts` und `src/lib/football-data.ts` ergänzen.
