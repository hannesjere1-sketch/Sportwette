"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { BankrollPoint } from "@/lib/betting";
import { formatCurrency } from "@/lib/format";

export function BankrollChart({ data, startingBankroll }: { data: BankrollPoint[]; startingBankroll: number }) {
  const points = data.length > 0 ? data : [{ date: "Start", bankroll: startingBankroll, profit: 0 }];

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={points} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="bankrollFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#34d399" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
        <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
        <YAxis
          stroke="#64748b"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          width={64}
          tickFormatter={(v: number) => formatCurrency(v)}
        />
        <Tooltip
          contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "#94a3b8" }}
          formatter={(value) => [formatCurrency(Number(value)), "Bankroll"]}
        />
        <Area type="monotone" dataKey="bankroll" stroke="#34d399" strokeWidth={2} fill="url(#bankrollFill)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
