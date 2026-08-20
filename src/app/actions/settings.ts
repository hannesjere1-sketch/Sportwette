"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import type { ActionResult } from "./bets";
import type { StakingMethod } from "@prisma/client";

const settingsSchema = z.object({
  startingBankroll: z.coerce.number().gt(0, "Startkapital muss größer als 0 sein"),
  stakingMethod: z.enum(["FLAT", "PERCENTAGE", "KELLY"]),
  flatStakeAmount: z.coerce.number().gt(0),
  percentageStake: z.coerce.number().gt(0),
  kellyFraction: z.coerce.number().gt(0).max(1),
  footballDataApiToken: z.string().optional(),
});

export async function updateSettings(_prevState: ActionResult | null, formData: FormData): Promise<ActionResult> {
  const parsed = settingsSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0]?.message ?? "Ungültige Eingabe" };
  }

  const data = parsed.data;
  await prisma.settings.upsert({
    where: { id: 1 },
    create: {
      id: 1,
      startingBankroll: data.startingBankroll,
      stakingMethod: data.stakingMethod as StakingMethod,
      flatStakeAmount: data.flatStakeAmount,
      percentageStake: data.percentageStake,
      kellyFraction: data.kellyFraction,
      footballDataApiToken: data.footballDataApiToken || null,
    },
    update: {
      startingBankroll: data.startingBankroll,
      stakingMethod: data.stakingMethod as StakingMethod,
      flatStakeAmount: data.flatStakeAmount,
      percentageStake: data.percentageStake,
      kellyFraction: data.kellyFraction,
      footballDataApiToken: data.footballDataApiToken || null,
    },
  });

  revalidatePath("/settings");
  revalidatePath("/dashboard");
  revalidatePath("/bets/new");
  return { ok: true };
}
