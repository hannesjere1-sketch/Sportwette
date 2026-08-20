"use client";

import { useState, useTransition } from "react";
import { regenerateApiKey } from "@/app/actions/settings";
import { Button } from "@/components/ui";

export function ApiKeyPanel({ initialApiKey, origin }: { initialApiKey: string; origin: string }) {
  const [apiKey, setApiKey] = useState(initialApiKey);
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState<"key" | "url" | null>(null);
  const [isPending, startTransition] = useTransition();

  const importUrl = `${origin}/api/bets/import`;
  const masked = `${apiKey.slice(0, 4)}${"•".repeat(Math.max(apiKey.length - 8, 8))}${apiKey.slice(-4)}`;

  function copy(value: string, which: "key" | "url") {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(which);
      setTimeout(() => setCopied(null), 1500);
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <span className="text-xs font-medium text-slate-400">Portal-URL (in der Extension eintragen)</span>
        <div className="mt-1.5 flex items-center gap-2">
          <code className="flex-1 truncate rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300">{origin || "…"}</code>
          <button
            type="button"
            onClick={() => copy(origin, "url")}
            className="shrink-0 text-xs font-medium text-emerald-400 hover:text-emerald-300"
          >
            {copied === "url" ? "Kopiert!" : "Kopieren"}
          </button>
        </div>
        <p className="mt-1 text-xs text-slate-500">Import-Endpunkt: {importUrl}</p>
      </div>

      <div>
        <span className="text-xs font-medium text-slate-400">API-Key (in der Extension eintragen)</span>
        <div className="mt-1.5 flex items-center gap-2">
          <code className="flex-1 truncate rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300">
            {revealed ? apiKey : masked}
          </code>
          <button type="button" onClick={() => setRevealed((v) => !v)} className="shrink-0 text-xs font-medium text-slate-400 hover:text-slate-200">
            {revealed ? "Verbergen" : "Anzeigen"}
          </button>
          <button type="button" onClick={() => copy(apiKey, "key")} className="shrink-0 text-xs font-medium text-emerald-400 hover:text-emerald-300">
            {copied === "key" ? "Kopiert!" : "Kopieren"}
          </button>
        </div>
      </div>

      <div>
        <Button
          type="button"
          variant="secondary"
          disabled={isPending}
          onClick={() => {
            if (!confirm("Neuen API-Key erzeugen? Der alte Key funktioniert danach nicht mehr — die Browser-Erweiterung muss neu konfiguriert werden.")) return;
            startTransition(async () => {
              const result = await regenerateApiKey();
              if (result.apiKey) {
                setApiKey(result.apiKey);
                setRevealed(true);
              }
            });
          }}
        >
          {isPending ? "Erzeuge…" : "API-Key neu erzeugen"}
        </Button>
      </div>
    </div>
  );
}
