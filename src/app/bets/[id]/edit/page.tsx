import { notFound } from "next/navigation";
import { prisma } from "@/lib/prisma";
import { updateBet } from "@/app/actions/bets";
import { PageHeader, Card } from "@/components/ui";
import { BetForm } from "@/components/bet-form";

export const dynamic = "force-dynamic";

function toDatetimeLocal(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export default async function EditBetPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const bet = await prisma.bet.findUnique({ where: { id } });
  if (!bet) notFound();

  const boundUpdateBet = updateBet.bind(null, id);

  return (
    <div className="max-w-2xl">
      <PageHeader title="Wette bearbeiten" description={`${bet.homeTeam} – ${bet.awayTeam}`} />
      <Card>
        <BetForm
          action={boundUpdateBet}
          submitLabel="Änderungen speichern"
          defaults={{
            league: bet.league,
            homeTeam: bet.homeTeam,
            awayTeam: bet.awayTeam,
            matchDate: toDatetimeLocal(bet.matchDate),
            market: bet.market,
            selection: bet.selection,
            odds: bet.odds,
            stake: bet.stake,
            notes: bet.notes ?? undefined,
          }}
        />
      </Card>
    </div>
  );
}
