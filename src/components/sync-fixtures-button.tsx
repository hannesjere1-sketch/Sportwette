"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { syncFixtures } from "@/app/actions/fixtures";
import { Button } from "@/components/ui";

export function SyncFixturesButton() {
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState<{ type: "ok" | "error"; text: string } | null>(null);
  const router = useRouter();

  return (
    <div className="flex flex-col items-end gap-1.5">
      <Button
        variant="secondary"
        disabled={isPending}
        onClick={() => {
          setMessage(null);
          startTransition(async () => {
            const result = await syncFixtures();
            if (result.ok) {
              setMessage({ type: "ok", text: `${result.synced ?? 0} Spiele synchronisiert.` });
              router.refresh();
            } else {
              setMessage({ type: "error", text: result.error ?? "Fehler bei der Synchronisation." });
            }
          });
        }}
      >
        {isPending ? "Synchronisiere…" : "🔄 Spielplan synchronisieren"}
      </Button>
      {message && <p className={`text-xs ${message.type === "ok" ? "text-emerald-400" : "text-rose-400"}`}>{message.text}</p>}
    </div>
  );
}
