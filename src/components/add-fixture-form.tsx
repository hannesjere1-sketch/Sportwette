"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { addFixture } from "@/app/actions/fixtures";
import { Button } from "@/components/ui";

const COMMON_LEAGUES = ["Premier League", "Bundesliga", "La Liga", "Serie A", "Ligue 1"];

const inputClass =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500";

export function AddFixtureForm() {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="text-xs font-medium text-emerald-400 hover:text-emerald-300">
        + Spiel manuell hinzufügen
      </button>
    );
  }

  return (
    <form
      action={(formData) => {
        setError(null);
        startTransition(async () => {
          const result = await addFixture(null, formData);
          if (!result.ok) {
            setError(result.error ?? "Fehler beim Speichern");
            return;
          }
          setOpen(false);
          router.refresh();
        });
      }}
      className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4"
    >
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-400">Liga</span>
          <input list="fixture-leagues" name="league" required className={inputClass} />
          <datalist id="fixture-leagues">
            {COMMON_LEAGUES.map((l) => (
              <option key={l} value={l} />
            ))}
          </datalist>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-400">Anstoßzeit</span>
          <input type="datetime-local" name="kickoff" required className={inputClass} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-400">Heimteam</span>
          <input name="homeTeam" required className={inputClass} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-400">Auswärtsteam</span>
          <input name="awayTeam" required className={inputClass} />
        </label>
      </div>
      {error && <p className="text-xs text-rose-400">{error}</p>}
      <div className="flex gap-2">
        <Button type="submit" disabled={isPending}>
          {isPending ? "Speichere…" : "Spiel speichern"}
        </Button>
        <button type="button" onClick={() => setOpen(false)} className="text-xs text-slate-500 hover:text-slate-300">
          Abbrechen
        </button>
      </div>
    </form>
  );
}
