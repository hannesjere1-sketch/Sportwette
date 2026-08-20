import Link from "next/link";
import { prisma } from "@/lib/prisma";
import type { BetStatus } from "@prisma/client";
import { betProfit } from "@/lib/betting";
import { formatCurrency, formatDateTime } from "@/lib/format";
import { PageHeader, StatusBadge, LinkButton, Card, EmptyState } from "@/components/ui";
import { SettleForm } from "@/components/settle-form";
import { DeleteBetButton } from "@/components/delete-bet-button";

export const dynamic = "force-dynamic";

const STATUS_FILTERS: { value: BetStatus | "ALL"; label: string }[] = [
  { value: "ALL", label: "Alle" },
  { value: "PENDING", label: "Offen" },
  { value: "WON", label: "Gewonnen" },
  { value: "LOST", label: "Verloren" },
  { value: "VOID", label: "Storniert" },
];

export default async function BetsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status } = await searchParams;
  const filter = (status ?? "ALL") as BetStatus | "ALL";

  const bets = await prisma.bet.findMany({
    where: filter === "ALL" ? {} : { status: filter },
    orderBy: { matchDate: "desc" },
  });

  return (
    <div>
      <PageHeader title="Wetten" description="Alle platzierten Wetten verwalten und abrechnen" action={<LinkButton href="/bets/new">+ Neue Wette</LinkButton>} />

      <div className="mb-4 flex flex-wrap gap-2">
        {STATUS_FILTERS.map((f) => (
          <Link
            key={f.value}
            href={f.value === "ALL" ? "/bets" : `/bets?status=${f.value}`}
            className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
              filter === f.value ? "bg-emerald-500/15 text-emerald-400" : "bg-slate-800/60 text-slate-400 hover:text-slate-200"
            }`}
          >
            {f.label}
          </Link>
        ))}
      </div>

      {bets.length === 0 ? (
        <EmptyState title="Keine Wetten gefunden" description="Für diesen Filter gibt es noch keine Einträge." action={<LinkButton href="/bets/new">Erste Wette anlegen</LinkButton>} />
      ) : (
        <div className="flex flex-col gap-3">
          {bets.map((bet) => {
            const profit = betProfit(bet);
            return (
              <Card key={bet.id} className="p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-slate-100">
                        {bet.homeTeam} – {bet.awayTeam}
                      </p>
                      <StatusBadge status={bet.status} />
                    </div>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {bet.league} · {formatDateTime(bet.matchDate)}
                    </p>
                    <p className="mt-1 text-sm text-slate-400">
                      {bet.market}: <span className="text-slate-200">{bet.selection}</span> @ {bet.odds.toFixed(2)} · Einsatz {formatCurrency(bet.stake)}
                    </p>
                    {bet.notes && <p className="mt-1 text-xs text-slate-500">{bet.notes}</p>}
                  </div>

                  <div className="flex shrink-0 flex-col items-end gap-2 text-right">
                    <span
                      className={`text-sm font-semibold ${
                        profit === null ? "text-slate-500" : profit > 0 ? "text-emerald-400" : profit < 0 ? "text-rose-400" : "text-slate-400"
                      }`}
                    >
                      {profit === null ? "—" : `${profit > 0 ? "+" : ""}${formatCurrency(profit)}`}
                    </span>
                    <div className="flex gap-2">
                      <Link href={`/bets/${bet.id}/edit`} className="text-xs font-medium text-slate-400 hover:text-slate-200">
                        Bearbeiten
                      </Link>
                      <DeleteBetButton id={bet.id} />
                    </div>
                  </div>
                </div>

                {bet.status === "PENDING" && <SettleForm betId={bet.id} defaultPayout={bet.stake * bet.odds} />}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
