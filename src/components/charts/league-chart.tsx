"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from "recharts";
import type { LeagueBreakdown } from "@/lib/betting";
import { formatCurrency } from "@/lib/format";

export function LeagueChart({ data }: { data: LeagueBreakdown[] }) {
  if (data.length === 0) {
    return <p className="py-10 text-center text-sm text-slate-500">Noch keine Daten für diese Ansicht.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
        <XAxis dataKey="league" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} interval={0} angle={-15} textAnchor="end" height={50} />
        <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} width={64} tickFormatter={(v: number) => formatCurrency(v)} />
        <Tooltip
          contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "#94a3b8" }}
          formatter={(value) => [formatCurrency(Number(value)), "Profit"]}
        />
        <Bar dataKey="profit" radius={[4, 4, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.profit >= 0 ? "#34d399" : "#fb7185"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
