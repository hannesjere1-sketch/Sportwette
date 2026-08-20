import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { formatDateTime, formatDate } from "@/lib/format";
import { PageHeader, Card, EmptyState } from "@/components/ui";
import { SyncFixturesButton } from "@/components/sync-fixtures-button";
import { AddFixtureForm } from "@/components/add-fixture-form";
import { DeleteFixtureButton } from "@/components/delete-fixture-button";

export const dynamic = "force-dynamic";

export default async function FixturesPage() {
  const fixtures = await prisma.fixture.findMany({
    where: { kickoff: { gte: recentCutoff() } },
    orderBy: { kickoff: "asc" },
  });

  const groups = new Map<string, typeof fixtures>();
  for (const fixture of fixtures) {
    const key = formatDate(fixture.kickoff);
    const list = groups.get(key) ?? [];
    list.push(fixture);
    groups.set(key, list);
  }

  return (
    <div>
      <PageHeader
        title="Spielplan"
        description="Anstehende Spiele der Top-5-Ligen — synchronisiert oder manuell gepflegt"
        action={<SyncFixturesButton />}
      />

      <div className="mb-4">
        <AddFixtureForm />
      </div>

      {fixtures.length === 0 ? (
        <EmptyState
          title="Keine anstehenden Spiele"
          description="Synchronisiere den Spielplan über football-data.org (Token in den Einstellungen) oder füge Spiele manuell hinzu."
        />
      ) : (
        <div className="flex flex-col gap-6">
          {Array.from(groups.entries()).map(([date, dayFixtures]) => (
            <div key={date}>
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{date}</h2>
              <div className="flex flex-col gap-2">
                {dayFixtures.map((f) => (
                  <Card key={f.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                    <div className="min-w-0">
                      <p className="font-medium text-slate-100">
                        {f.homeTeam} – {f.awayTeam}
                      </p>
                      <p className="text-xs text-slate-500">
                        {f.league} · {formatDateTime(f.kickoff)} {f.source === "MANUAL" && "· manuell"}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-4">
                      <Link
                        href={{
                          pathname: "/bets/new",
                          query: {
                            league: f.league,
                            homeTeam: f.homeTeam,
                            awayTeam: f.awayTeam,
                            matchDate: toDatetimeLocal(f.kickoff),
                            fixtureId: f.id,
                          },
                        }}
                        className="text-xs font-medium text-emerald-400 hover:text-emerald-300"
                      >
                        Wette platzieren
                      </Link>
                      <DeleteFixtureButton id={f.id} />
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function recentCutoff(): Date {
  return new Date(Date.now() - 24 * 60 * 60 * 1000);
}

function toDatetimeLocal(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
