"use client";

import { useActionState } from "react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import type { ActionResult } from "@/app/actions/bets";
import { Button } from "@/components/ui";

export interface BetFormDefaults {
  league?: string;
  homeTeam?: string;
  awayTeam?: string;
  matchDate?: string; // datetime-local value
  market?: string;
  selection?: string;
  odds?: number;
  stake?: number;
  notes?: string;
  fixtureId?: string;
}

const COMMON_LEAGUES = ["Premier League", "Bundesliga", "La Liga", "Serie A", "Ligue 1"];
const COMMON_MARKETS = ["Match Result (1X2)", "Über/Unter 2.5 Tore", "Beide Teams treffen", "Doppelte Chance", "Handicap"];

export function BetForm({
  action,
  defaults,
  submitLabel,
  suggestedStake,
}: {
  action: (prevState: ActionResult | null, formData: FormData) => Promise<ActionResult>;
  defaults?: BetFormDefaults;
  submitLabel: string;
  suggestedStake?: number;
}) {
  const router = useRouter();
  const [state, formAction, isPending] = useActionState(action, null);

  useEffect(() => {
    if (state?.ok) {
      router.push("/bets");
      router.refresh();
    }
  }, [state, router]);

  return (
    <form action={formAction} className="flex flex-col gap-5">
      {defaults?.fixtureId && <input type="hidden" name="fixtureId" value={defaults.fixtureId} />}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Liga">
          <input list="leagues" name="league" defaultValue={defaults?.league} required className={inputClass} placeholder="z. B. Bundesliga" />
          <datalist id="leagues">
            {COMMON_LEAGUES.map((l) => (
              <option key={l} value={l} />
            ))}
          </datalist>
        </Field>
        <Field label="Anstoßzeit">
          <input type="datetime-local" name="matchDate" defaultValue={defaults?.matchDate} required className={inputClass} />
        </Field>
        <Field label="Heimteam">
          <input name="homeTeam" defaultValue={defaults?.homeTeam} required className={inputClass} placeholder="z. B. FC Bayern" />
        </Field>
        <Field label="Auswärtsteam">
          <input name="awayTeam" defaultValue={defaults?.awayTeam} required className={inputClass} placeholder="z. B. Borussia Dortmund" />
        </Field>
        <Field label="Markt">
          <input list="markets" name="market" defaultValue={defaults?.market} required className={inputClass} placeholder="z. B. Match Result" />
          <datalist id="markets">
            {COMMON_MARKETS.map((m) => (
              <option key={m} value={m} />
            ))}
          </datalist>
        </Field>
        <Field label="Tipp">
          <input name="selection" defaultValue={defaults?.selection} required className={inputClass} placeholder="z. B. Heimsieg" />
        </Field>
        <Field label="Quote">
          <input type="number" step="0.01" min="1.01" name="odds" defaultValue={defaults?.odds} required className={inputClass} placeholder="1.85" />
        </Field>
        <Field label="Einsatz (€)" hint={suggestedStake ? `Vorschlag aus Strategie: ${suggestedStake.toFixed(2)} €` : undefined}>
          <input type="number" step="0.01" min="0.01" name="stake" defaultValue={defaults?.stake ?? suggestedStake} required className={inputClass} />
        </Field>
      </div>

      <Field label="Notizen (optional)">
        <textarea name="notes" defaultValue={defaults?.notes} rows={3} className={inputClass} placeholder="Begründung, Value-Einschätzung, etc." />
      </Field>

      {state?.error && <p className="text-sm text-rose-400">{state.error}</p>}

      <div className="flex gap-3">
        <Button type="submit" disabled={isPending}>
          {isPending ? "Speichere…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}

const inputClass =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500";

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-slate-400">{label}</span>
      {children}
      {hint && <span className="text-xs text-slate-500">{hint}</span>}
    </label>
  );
}
