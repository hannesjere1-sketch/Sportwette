"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/bets", label: "Wetten", icon: "🎟️" },
  { href: "/fixtures", label: "Spielplan", icon: "📅" },
  { href: "/settings", label: "Settings", icon: "⚙️" },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="sm:hidden sticky top-0 z-10 flex items-center justify-between gap-1 border-b border-slate-800 bg-slate-900/90 px-2 py-2 backdrop-blur">
      {NAV_ITEMS.map((item) => {
        const active = pathname === item.href || pathname.startsWith(item.href + "/");
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex flex-1 flex-col items-center gap-0.5 rounded-md py-1.5 text-[11px] font-medium ${
              active ? "text-emerald-400" : "text-slate-400"
            }`}
          >
            <span aria-hidden className="text-base">
              {item.icon}
            </span>
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
