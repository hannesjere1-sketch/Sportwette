"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { deleteBet } from "@/app/actions/bets";

export function DeleteBetButton({ id }: { id: string }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  return (
    <button
      className="text-xs font-medium text-rose-400/80 hover:text-rose-400 disabled:opacity-50"
      disabled={isPending}
      onClick={() => {
        if (!confirm("Diese Wette wirklich löschen?")) return;
        startTransition(async () => {
          await deleteBet(id);
          router.refresh();
        });
      }}
    >
      Löschen
    </button>
  );
}
