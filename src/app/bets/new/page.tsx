import { prisma } from "@/lib/prisma";
import { getSettings } from "@/lib/settings";
import { computeStats, suggestStake } from "@/lib/betting";
import { createBet } from "@/app/actions/bets";
import { PageHeader, Card } from "@/components/ui";
import { BetForm } from "@/components/bet-form";

export const dynamic = "force-dynamic";

export default async function NewBetPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const params = await searchParams;
  const [bets, settings] = await Promise.all([prisma.bet.findMany(), getSettings()]);
  const { currentBankroll } = computeStats(bets, settings.startingBankroll);
  const suggested = suggestStake(settings, currentBankroll);

  return (
    <div className="max-w-2xl">
      <PageHeader title="Neue Wette" description="Trage eine platzierte Wette ein" />
      <Card>
        <BetForm
          action={createBet}
          submitLabel="Wette speichern"
          suggestedStake={suggested}
          defaults={{
            league: params.league,
            homeTeam: params.homeTeam,
            awayTeam: params.awayTeam,
            matchDate: params.matchDate,
            fixtureId: params.fixtureId,
          }}
        />
      </Card>
    </div>
  );
}
