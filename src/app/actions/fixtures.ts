"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { fetchUpcomingFixtures, FootballDataError } from "@/lib/football-data";
import { getSettings } from "@/lib/settings";
import type { ActionResult } from "./bets";

export async function syncFixtures(): Promise<ActionResult & { synced?: number }> {
  const settings = await getSettings();
  if (!settings.footballDataApiToken) {
    return {
      ok: false,
      error: "Kein API-Token hinterlegt. Trage einen football-data.org Token unter Einstellungen ein.",
    };
  }

  try {
    const fixtures = await fetchUpcomingFixtures(settings.footballDataApiToken);
    for (const fixture of fixtures) {
      await prisma.fixture.upsert({
        where: { externalId: fixture.externalId },
        create: {
          externalId: fixture.externalId,
          league: fixture.league,
          homeTeam: fixture.homeTeam,
          awayTeam: fixture.awayTeam,
          kickoff: fixture.kickoff,
          status: fixture.status,
          source: "API",
        },
        update: {
          league: fixture.league,
          homeTeam: fixture.homeTeam,
          awayTeam: fixture.awayTeam,
          kickoff: fixture.kickoff,
          status: fixture.status,
        },
      });
    }
    revalidatePath("/fixtures");
    return { ok: true, synced: fixtures.length };
  } catch (err) {
    if (err instanceof FootballDataError) {
      return { ok: false, error: err.message };
    }
    return { ok: false, error: "Synchronisation fehlgeschlagen." };
  }
}

const fixtureInputSchema = z.object({
  league: z.string().min(1, "Liga ist erforderlich"),
  homeTeam: z.string().min(1, "Heimteam ist erforderlich"),
  awayTeam: z.string().min(1, "Auswärtsteam ist erforderlich"),
  kickoff: z.string().min(1, "Anstoßzeit ist erforderlich"),
});

export async function addFixture(_prevState: ActionResult | null, formData: FormData): Promise<ActionResult> {
  const parsed = fixtureInputSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0]?.message ?? "Ungültige Eingabe" };
  }

  const data = parsed.data;
  await prisma.fixture.create({
    data: {
      league: data.league,
      homeTeam: data.homeTeam,
      awayTeam: data.awayTeam,
      kickoff: new Date(data.kickoff),
      source: "MANUAL",
    },
  });

  revalidatePath("/fixtures");
  return { ok: true };
}

export async function deleteFixture(id: string): Promise<ActionResult> {
  await prisma.fixture.delete({ where: { id } });
  revalidatePath("/fixtures");
  return { ok: true };
}
