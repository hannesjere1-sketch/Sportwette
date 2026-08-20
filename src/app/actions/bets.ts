"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import type { BetStatus } from "@prisma/client";

const betInputSchema = z.object({
  league: z.string().min(1, "Liga ist erforderlich"),
  homeTeam: z.string().min(1, "Heimteam ist erforderlich"),
  awayTeam: z.string().min(1, "Auswärtsteam ist erforderlich"),
  matchDate: z.string().min(1, "Anstoßzeit ist erforderlich"),
  market: z.string().min(1, "Markt ist erforderlich"),
  selection: z.string().min(1, "Tipp ist erforderlich"),
  odds: z.coerce.number().gt(1, "Quote muss größer als 1 sein"),
  stake: z.coerce.number().gt(0, "Einsatz muss größer als 0 sein"),
  notes: z.string().optional(),
  fixtureId: z.string().optional(),
});

export interface ActionResult {
  ok: boolean;
  error?: string;
}

export async function createBet(_prevState: ActionResult | null, formData: FormData): Promise<ActionResult> {
  const parsed = betInputSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0]?.message ?? "Ungültige Eingabe" };
  }

  const data = parsed.data;
  await prisma.bet.create({
    data: {
      league: data.league,
      homeTeam: data.homeTeam,
      awayTeam: data.awayTeam,
      matchDate: new Date(data.matchDate),
      market: data.market,
      selection: data.selection,
      odds: data.odds,
      stake: data.stake,
      notes: data.notes || null,
      fixtureId: data.fixtureId || null,
    },
  });

  revalidatePath("/bets");
  revalidatePath("/dashboard");
  revalidatePath("/fixtures");
  return { ok: true };
}

export async function updateBet(id: string, _prevState: ActionResult | null, formData: FormData): Promise<ActionResult> {
  const parsed = betInputSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0]?.message ?? "Ungültige Eingabe" };
  }

  const data = parsed.data;
  await prisma.bet.update({
    where: { id },
    data: {
      league: data.league,
      homeTeam: data.homeTeam,
      awayTeam: data.awayTeam,
      matchDate: new Date(data.matchDate),
      market: data.market,
      selection: data.selection,
      odds: data.odds,
      stake: data.stake,
      notes: data.notes || null,
    },
  });

  revalidatePath("/bets");
  revalidatePath("/dashboard");
  return { ok: true };
}

const settleSchema = z.object({
  status: z.enum(["PENDING", "WON", "LOST", "VOID", "PUSH"]),
  payout: z.coerce.number().optional(),
});

export async function settleBet(id: string, formData: FormData): Promise<ActionResult> {
  const parsed = settleSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0]?.message ?? "Ungültige Eingabe" };
  }

  const status = parsed.data.status as BetStatus;
  await prisma.bet.update({
    where: { id },
    data: {
      status,
      payout: status === "WON" ? parsed.data.payout ?? null : null,
    },
  });

  revalidatePath("/bets");
  revalidatePath("/dashboard");
  return { ok: true };
}

export async function deleteBet(id: string): Promise<ActionResult> {
  await prisma.bet.delete({ where: { id } });
  revalidatePath("/bets");
  revalidatePath("/dashboard");
  return { ok: true };
}
