import { randomBytes } from "crypto";
import { prisma } from "@/lib/prisma";

function generateApiKey(): string {
  return randomBytes(24).toString("hex");
}

/** Settings is a singleton row (id=1); this creates it with defaults (incl. a fresh API key) on first access. */
export async function getSettings() {
  const existing = await prisma.settings.findUnique({ where: { id: 1 } });
  if (existing) {
    if (existing.apiKey) return existing;
    return prisma.settings.update({ where: { id: 1 }, data: { apiKey: generateApiKey() } });
  }
  return prisma.settings.create({ data: { id: 1, apiKey: generateApiKey() } });
}

export { generateApiKey };
