"use client";

import { useActionState, useState } from "react";
import { updateSettings } from "@/app/actions/settings";
import { Button } from "@/components/ui";
import type { Settings } from "@prisma/client";

const inputClass =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500";

export function SettingsForm({ settings }: { settings: Settings }) {
  const [state, formAction, isPending] = useActionState(updateSettings, null);
  const [method, setMethod] = useState(settings.stakingMethod);

  return (
    <form action={formAction} className="flex flex-col gap-6">
      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-slate-200">Bankroll</h2>
        <label className="flex max-w-xs flex-col gap-1.5">
          <span className="text-xs font-medium text-slate-400">Startkapital (€)</span>
          <input type="number" step="0.01" min="0.01" name="startingBankroll" defaultValue={settings.startingBankroll} required className={inputClass} />
        </label>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-slate-200">Staking-Strategie</h2>
        <p className="text-xs text-slate-500">Bestimmt den vorgeschlagenen Einsatz beim Anlegen einer neuen Wette.</p>

        <div className="flex flex-col gap-2">
          {(
            [
              { value: "FLAT", label: "Fester Einsatz", hint: "Immer der gleiche Betrag pro Wette." },
              { value: "PERCENTAGE", label: "Prozent der Bankroll", hint: "Einsatz skaliert mit dem aktuellen Kontostand." },
              { value: "KELLY", label: "Kelly-Kriterium", hint: "Braucht eine geschätzte Gewinnwahrscheinlichkeit pro Wette." },
            ] as const
          ).map((opt) => (
            <label
              key={opt.value}
              className={`flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2.5 ${
                method === opt.value ? "border-emerald-500 bg-emerald-500/5" : "border-slate-800"
              }`}
            >
              <input
                type="radio"
                name="stakingMethod"
                value={opt.value}
                checked={method === opt.value}
                onChange={() => setMethod(opt.value)}
                className="mt-0.5"
              />
              <span>
                <span className="block text-sm font-medium text-slate-200">{opt.label}</span>
                <span className="block text-xs text-slate-500">{opt.hint}</span>
              </span>
            </label>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-slate-400">Fester Einsatz (€)</span>
            <input type="number" step="0.01" min="0.01" name="flatStakeAmount" defaultValue={settings.flatStakeAmount} required className={inputClass} />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-slate-400">Einsatz in % der Bankroll</span>
            <input type="number" step="0.1" min="0.1" name="percentageStake" defaultValue={settings.percentageStake} required className={inputClass} />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-slate-400">Kelly-Fraktion (0–1)</span>
            <input type="number" step="0.05" min="0.05" max="1" name="kellyFraction" defaultValue={settings.kellyFraction} required className={inputClass} />
          </label>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-slate-200">Spielplan-Synchronisation</h2>
        <p className="text-xs text-slate-500">
          Kostenloser Token von{" "}
          <a href="https://www.football-data.org/client/register" target="_blank" rel="noreferrer" className="text-emerald-400 hover:text-emerald-300">
            football-data.org
          </a>{" "}
          für automatischen Import der Top-5-Ligen. Ohne Token können Spiele weiterhin manuell gepflegt werden.
        </p>
        <label className="flex max-w-md flex-col gap-1.5">
          <span className="text-xs font-medium text-slate-400">API-Token</span>
          <input name="footballDataApiToken" defaultValue={settings.footballDataApiToken ?? ""} className={inputClass} placeholder="optional" />
        </label>
      </section>

      {state?.error && <p className="text-sm text-rose-400">{state.error}</p>}
      {state?.ok && <p className="text-sm text-emerald-400">Einstellungen gespeichert.</p>}

      <div>
        <Button type="submit" disabled={isPending}>
          {isPending ? "Speichere…" : "Einstellungen speichern"}
        </Button>
      </div>
    </form>
  );
}
