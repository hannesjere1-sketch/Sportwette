import type { ReactNode } from "react";
import type { BetStatus } from "@prisma/client";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-800 bg-slate-900/60 p-5 ${className}`}>
      {children}
    </div>
  );
}

export function PageHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-400">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function StatCard({ label, value, hint, tone = "neutral" }: { label: string; value: string; hint?: string; tone?: "neutral" | "positive" | "negative" }) {
  const toneClass = tone === "positive" ? "text-emerald-400" : tone === "negative" ? "text-rose-400" : "text-white";
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${toneClass}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </Card>
  );
}

const STATUS_STYLES: Record<BetStatus, string> = {
  PENDING: "bg-amber-500/10 text-amber-400",
  WON: "bg-emerald-500/10 text-emerald-400",
  LOST: "bg-rose-500/10 text-rose-400",
  VOID: "bg-slate-500/10 text-slate-400",
  PUSH: "bg-slate-500/10 text-slate-400",
};

const STATUS_LABELS: Record<BetStatus, string> = {
  PENDING: "Offen",
  WON: "Gewonnen",
  LOST: "Verloren",
  VOID: "Annulliert",
  PUSH: "Rückerstattet",
};

export function StatusBadge({ status }: { status: BetStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  );
}

export function Button({
  children,
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" }) {
  const variants: Record<string, string> = {
    primary: "bg-emerald-500 text-slate-950 hover:bg-emerald-400",
    secondary: "bg-slate-800 text-slate-100 hover:bg-slate-700",
    danger: "bg-rose-500/10 text-rose-400 hover:bg-rose-500/20",
  };
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors disabled:opacity-50 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function LinkButton({ children, href, variant = "primary", className = "" }: { children: ReactNode; href: string; variant?: "primary" | "secondary"; className?: string }) {
  const variants: Record<string, string> = {
    primary: "bg-emerald-500 text-slate-950 hover:bg-emerald-400",
    secondary: "bg-slate-800 text-slate-100 hover:bg-slate-700",
  };
  return (
    <a
      href={href}
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${variants[variant]} ${className}`}
    >
      {children}
    </a>
  );
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-800 px-6 py-16 text-center">
      <p className="text-sm font-medium text-slate-300">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
