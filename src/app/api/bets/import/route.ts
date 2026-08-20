import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getSettings } from "@/lib/settings";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

function json(body: unknown, init?: ResponseInit) {
  return NextResponse.json(body, { ...init, headers: { ...CORS_HEADERS, ...init?.headers } });
}

async function authorize(req: NextRequest): Promise<boolean> {
  const header = req.headers.get("authorization") ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : null;
  if (!token) return false;
  const settings = await getSettings();
  return Boolean(settings.apiKey) && token === settings.apiKey;
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: CORS_HEADERS });
}

/** Used by the browser extension's "Verbindung testen" check. */
export async function GET(req: NextRequest) {
  if (!(await authorize(req))) {
    return json({ ok: false, error: "Ungültiger oder fehlender API-Key." }, { status: 401 });
  }
  return json({ ok: true, service: "wettportal" });
}

const importSchema = z.object({
  league: z.string().min(1),
  homeTeam: z.string().min(1),
  awayTeam: z.string().min(1),
  matchDate: z.string().min(1),
  market: z.string().min(1),
  selection: z.string().min(1),
  odds: z.coerce.number().gt(1),
  stake: z.coerce.number().gt(0),
  notes: z.string().optional(),
});

export async function POST(req: NextRequest) {
  if (!(await authorize(req))) {
    return json({ ok: false, error: "Ungültiger oder fehlender API-Key." }, { status: 401 });
  }

  let payload: unknown;
  try {
    payload = await req.json();
  } catch {
    return json({ ok: false, error: "Ungültiges JSON." }, { status: 400 });
  }

  const parsed = importSchema.safeParse(payload);
  if (!parsed.success) {
    return json({ ok: false, error: parsed.error.issues[0]?.message ?? "Ungültige Eingabe." }, { status: 400 });
  }

  const data = parsed.data;
  const matchDate = new Date(data.matchDate);
  if (Number.isNaN(matchDate.getTime())) {
    return json({ ok: false, error: "Ungültiges Datum für matchDate." }, { status: 400 });
  }

  const bet = await prisma.bet.create({
    data: {
      league: data.league,
      homeTeam: data.homeTeam,
      awayTeam: data.awayTeam,
      matchDate,
      market: data.market,
      selection: data.selection,
      odds: data.odds,
      stake: data.stake,
      notes: data.notes || null,
      source: "TIPICO_EXTENSION",
    },
  });

  return json({ ok: true, betId: bet.id });
}
