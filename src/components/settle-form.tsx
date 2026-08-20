"use client";

import { useState, useTransition } from "react";
import { settleBet } from "@/app/actions/bets";
import { Button } from "@/components/ui";

export function SettleForm({ betId, defaultPayout }: { betId: string; defaultPayout: number }) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState("WON");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="mt-3 text-xs font-medium text-emerald-400 hover:text-emerald-300">
        Wette abrechnen
      </button>
    );
  }

  return (
    <form
      action={(formData) => {
        setError(null);
        startTransition(async () => {
          const result = await settleBet(betId, formData);
          if (!result.ok) setError(result.error ?? "Fehler beim Speichern");
          else setOpen(false);
        });
      }}
      className="mt-3 flex flex-wrap items-end gap-3 border-t border-slate-800 pt-3"
    >
      <label className="flex flex-col gap-1">
        <span className="text-xs text-slate-500">Ergebnis</span>
        <select
          name="status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-sm text-slate-100"
        >
          <option value="WON">Gewonnen</option>
          <option value="LOST">Verloren</option>
          <option value="VOID">Storniert</option>
          <option value="PUSH">Rückerstattet</option>
        </select>
      </label>
      {status === "WON" && (
        <label className="flex flex-col gap-1">
          <span className="text-xs text-slate-500">Auszahlung (€)</span>
          <input
            type="number"
            step="0.01"
            name="payout"
            defaultValue={defaultPayout.toFixed(2)}
            className="w-28 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-sm text-slate-100"
          />
        </label>
      )}
      <Button type="submit" disabled={isPending}>
        {isPending ? "Speichere…" : "Bestätigen"}
      </Button>
      <button type="button" onClick={() => setOpen(false)} className="text-xs text-slate-500 hover:text-slate-300">
        Abbrechen
      </button>
      {error && <p className="w-full text-xs text-rose-400">{error}</p>}
    </form>
  );
}
