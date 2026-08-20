import { prisma } from "@/lib/prisma";

/** Settings is a singleton row (id=1); this creates it with defaults on first access. */
export async function getSettings() {
  const existing = await prisma.settings.findUnique({ where: { id: 1 } });
  if (existing) return existing;
  return prisma.settings.create({ data: { id: 1 } });
}
