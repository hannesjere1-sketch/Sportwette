/** Client for the free football-data.org API (v4), used to sync the fixture timetable. */

export const TOP_5_LEAGUES = [
  { code: "PL", name: "Premier League" },
  { code: "BL1", name: "Bundesliga" },
  { code: "SA", name: "Serie A" },
  { code: "PD", name: "La Liga" },
  { code: "FL1", name: "Ligue 1" },
] as const;

interface FootballDataMatch {
  id: number;
  utcDate: string;
  status: string;
  competition: { code: string; name: string };
  homeTeam: { name: string };
  awayTeam: { name: string };
}

interface FootballDataResponse {
  matches: FootballDataMatch[];
}

export interface FetchedFixture {
  externalId: string;
  league: string;
  homeTeam: string;
  awayTeam: string;
  kickoff: Date;
  status: string;
}

export class FootballDataError extends Error {}

/** Fetches upcoming matches for the top 5 leagues over the next `days` days. */
export async function fetchUpcomingFixtures(token: string, days = 14): Promise<FetchedFixture[]> {
  if (!token) {
    throw new FootballDataError("Kein FOOTBALL_DATA_API_TOKEN konfiguriert.");
  }

  const dateFrom = new Date().toISOString().slice(0, 10);
  const dateTo = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const competitions = TOP_5_LEAGUES.map((l) => l.code).join(",");

  const url = `https://api.football-data.org/v4/matches?competitions=${competitions}&dateFrom=${dateFrom}&dateTo=${dateTo}`;

  const res = await fetch(url, {
    headers: { "X-Auth-Token": token },
    cache: "no-store",
  });

  if (!res.ok) {
    if (res.status === 429) {
      throw new FootballDataError("API-Rate-Limit erreicht. Bitte später erneut versuchen.");
    }
    throw new FootballDataError(`football-data.org antwortete mit Status ${res.status}.`);
  }

  const data = (await res.json()) as FootballDataResponse;

  return data.matches.map((m) => ({
    externalId: String(m.id),
    league: m.competition.name,
    homeTeam: m.homeTeam.name,
    awayTeam: m.awayTeam.name,
    kickoff: new Date(m.utcDate),
    status: m.status,
  }));
}
