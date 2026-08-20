"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/bets", label: "Wetten", icon: "🎟️" },
  { href: "/fixtures", label: "Spielplan", icon: "📅" },
  { href: "/settings", label: "Einstellungen", icon: "⚙️" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden sm:flex w-56 shrink-0 flex-col border-r border-slate-800 bg-slate-900/60 px-4 py-6">
      <div className="mb-8 px-2">
        <span className="text-lg font-semibold tracking-tight text-white">Wettportal</span>
        <p className="mt-0.5 text-xs text-slate-500">Strategie &amp; Bankroll</p>
      </div>
      <nav className="flex flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-emerald-500/10 text-emerald-400"
                  : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-100"
              }`}
            >
              <span aria-hidden>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
