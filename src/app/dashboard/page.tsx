import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { getSettings } from "@/lib/settings";
import { bankrollTimeline, breakdownByLeague, computeStats } from "@/lib/betting";
import { formatCurrency, formatDateTime } from "@/lib/format";
import { Card, PageHeader, StatCard, StatusBadge, EmptyState, LinkButton } from "@/components/ui";
import { BankrollChart } from "@/components/charts/bankroll-chart";
import { LeagueChart } from "@/components/charts/league-chart";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const [bets, settings, upcomingFixtures] = await Promise.all([
    prisma.bet.findMany({ orderBy: { matchDate: "desc" } }),
    getSettings(),
    prisma.fixture.findMany({ where: { kickoff: { gte: new Date() } }, orderBy: { kickoff: "asc" }, take: 5 }),
  ]);

  const stats = computeStats(bets, settings.startingBankroll);
  const timeline = bankrollTimeline(bets, settings.startingBankroll);
  const leagueBreakdown = breakdownByLeague(bets);
  const recentBets = bets.slice(0, 6);

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Überblick über Bankroll, Performance und offene Wetten"
        action={<LinkButton href="/bets/new">+ Neue Wette</LinkButton>}
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Bankroll" value={formatCurrency(stats.currentBankroll)} hint={`Start: ${formatCurrency(settings.startingBankroll)}`} />
        <StatCard
          label="Gesamt-Profit"
          value={formatCurrency(stats.totalProfit)}
          tone={stats.totalProfit > 0 ? "positive" : stats.totalProfit < 0 ? "negative" : "neutral"}
        />
        <StatCard label="ROI" value={`${stats.roi.toFixed(1)}%`} tone={stats.roi > 0 ? "positive" : stats.roi < 0 ? "negative" : "neutral"} hint={`${stats.settledBets} abgerechnete Wetten`} />
        <StatCard label="Trefferquote" value={`${stats.winRate.toFixed(1)}%`} hint={`${stats.wins}S / ${stats.losses}N`} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <h2 className="mb-1 text-sm font-semibold text-slate-200">Bankroll-Verlauf</h2>
          <p className="mb-2 text-xs text-slate-500">Kumulierter Kontostand nach jeder abgerechneten Wette</p>
          <BankrollChart data={timeline} startingBankroll={settings.startingBankroll} />
        </Card>

        <Card>
          <h2 className="mb-1 text-sm font-semibold text-slate-200">Nächste Spiele</h2>
          <p className="mb-3 text-xs text-slate-500">Aus deinem Spielplan</p>
          {upcomingFixtures.length === 0 ? (
            <EmptyState
              title="Keine anstehenden Spiele"
              description="Synchronisiere den Spielplan oder trage ein Spiel manuell ein."
              action={<LinkButton href="/fixtures" variant="secondary">Zum Spielplan</LinkButton>}
            />
          ) : (
            <ul className="flex flex-col gap-3">
              {upcomingFixtures.map((f) => (
                <li key={f.id} className="flex items-center justify-between gap-2 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-200">
                      {f.homeTeam} – {f.awayTeam}
                    </p>
                    <p className="text-xs text-slate-500">{f.league}</p>
                  </div>
                  <span className="shrink-0 text-xs text-slate-400">{formatDateTime(f.kickoff)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <h2 className="mb-1 text-sm font-semibold text-slate-200">Profit nach Liga</h2>
          <p className="mb-2 text-xs text-slate-500">Welche Ligen sich bisher am meisten lohnen</p>
          <LeagueChart data={leagueBreakdown} />
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-slate-200">Letzte Wetten</h2>
          {recentBets.length === 0 ? (
            <EmptyState title="Noch keine Wetten" description="Lege deine erste Wette an, um hier Daten zu sehen." />
          ) : (
            <ul className="flex flex-col gap-3">
              {recentBets.map((bet) => (
                <li key={bet.id} className="flex items-center justify-between gap-2 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-200">
                      {bet.homeTeam} – {bet.awayTeam}
                    </p>
                    <p className="truncate text-xs text-slate-500">
                      {bet.market}: {bet.selection} @ {bet.odds.toFixed(2)}
                    </p>
                  </div>
                  <StatusBadge status={bet.status} />
                </li>
              ))}
            </ul>
          )}
          <div className="mt-4">
            <Link href="/bets" className="text-xs font-medium text-emerald-400 hover:text-emerald-300">
              Alle Wetten ansehen →
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}
