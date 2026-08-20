"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { deleteFixture } from "@/app/actions/fixtures";

export function DeleteFixtureButton({ id }: { id: string }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  return (
    <button
      className="text-xs font-medium text-slate-500 hover:text-rose-400 disabled:opacity-50"
      disabled={isPending}
      onClick={() => {
        startTransition(async () => {
          await deleteFixture(id);
          router.refresh();
        });
      }}
    >
      Entfernen
    </button>
  );
}
