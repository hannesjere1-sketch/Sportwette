import type { Bet, Settings, StakingMethod } from "@prisma/client";

/** Profit/loss of a single bet. Returns null while the bet is still pending. */
export function betProfit(bet: Pick<Bet, "status" | "stake" | "odds" | "payout">): number | null {
  switch (bet.status) {
    case "PENDING":
      return null;
    case "VOID":
    case "PUSH":
      return 0;
    case "LOST":
      return -bet.stake;
    case "WON":
      return (bet.payout ?? bet.stake * bet.odds) - bet.stake;
    default:
      return null;
  }
}

export interface BetStats {
  totalBets: number;
  settledBets: number;
  pendingBets: number;
  wins: number;
  losses: number;
  voids: number;
  totalStaked: number;
  totalProfit: number;
  roi: number; // percent, over settled+staked bets only
  winRate: number; // percent, over settled bets excluding void/push
  currentBankroll: number;
}

export function computeStats(bets: Bet[], startingBankroll: number): BetStats {
  let settledBets = 0;
  let pendingBets = 0;
  let wins = 0;
  let losses = 0;
  let voids = 0;
  let totalStaked = 0;
  let totalProfit = 0;
  let settledStake = 0;

  for (const bet of bets) {
    const profit = betProfit(bet);
    if (bet.status === "PENDING") {
      pendingBets++;
      continue;
    }
    settledBets++;
    totalStaked += bet.stake;
    totalProfit += profit ?? 0;
    if (bet.status === "WON") wins++;
    else if (bet.status === "LOST") losses++;
    else voids++;
    if (bet.status === "WON" || bet.status === "LOST") settledStake += bet.stake;
  }

  const decidedBets = wins + losses;

  return {
    totalBets: bets.length,
    settledBets,
    pendingBets,
    wins,
    losses,
    voids,
    totalStaked,
    totalProfit,
    roi: settledStake > 0 ? (totalProfit / settledStake) * 100 : 0,
    winRate: decidedBets > 0 ? (wins / decidedBets) * 100 : 0,
    currentBankroll: startingBankroll + totalProfit,
  };
}

export interface BankrollPoint {
  date: string;
  bankroll: number;
  profit: number;
}

/** Cumulative bankroll over time, ordered by match date, for the bankroll chart. */
export function bankrollTimeline(bets: Bet[], startingBankroll: number): BankrollPoint[] {
  const settled = bets
    .filter((b) => b.status !== "PENDING")
    .slice()
    .sort((a, b) => a.matchDate.getTime() - b.matchDate.getTime());

  let running = startingBankroll;
  return settled.map((bet) => {
    const profit = betProfit(bet) ?? 0;
    running += profit;
    return {
      date: bet.matchDate.toISOString().slice(0, 10),
      bankroll: Math.round(running * 100) / 100,
      profit,
    };
  });
}

export interface LeagueBreakdown {
  league: string;
  bets: number;
  profit: number;
  roi: number;
  winRate: number;
}

export function breakdownByLeague(bets: Bet[]): LeagueBreakdown[] {
  const groups = new Map<string, Bet[]>();
  for (const bet of bets) {
    const list = groups.get(bet.league) ?? [];
    list.push(bet);
    groups.set(bet.league, list);
  }

  return Array.from(groups.entries())
    .map(([league, leagueBets]) => {
      const stats = computeStats(leagueBets, 0);
      return {
        league,
        bets: leagueBets.length,
        profit: stats.totalProfit,
        roi: stats.roi,
        winRate: stats.winRate,
      };
    })
    .sort((a, b) => b.bets - a.bets);
}

/** Suggests a stake for a new bet based on the configured staking method. */
export function suggestStake(
  settings: Pick<Settings, "stakingMethod" | "flatStakeAmount" | "percentageStake" | "kellyFraction">,
  currentBankroll: number,
  odds?: number,
  estimatedWinProbability?: number,
): number {
  const method: StakingMethod = settings.stakingMethod;

  if (method === "FLAT") {
    return round2(settings.flatStakeAmount);
  }

  if (method === "PERCENTAGE") {
    return round2((settings.percentageStake / 100) * currentBankroll);
  }

  // KELLY: requires odds and an estimated win probability; falls back to flat stake.
  if (method === "KELLY" && odds && odds > 1 && estimatedWinProbability) {
    const b = odds - 1;
    const p = estimatedWinProbability;
    const q = 1 - p;
    const kelly = (b * p - q) / b;
    const fraction = Math.max(0, kelly) * settings.kellyFraction;
    return round2(fraction * currentBankroll);
  }

  return round2(settings.flatStakeAmount);
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}
