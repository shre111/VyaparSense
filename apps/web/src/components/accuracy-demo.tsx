"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// Illustrative only — the real, per-tenant curve lives on the Accuracy page and
// is reconstructed from stored forecast-vs-actual history (the flywheel metric).
const DEMO = [
  { week: "W1", wape: 42 },
  { week: "W2", wape: 39 },
  { week: "W3", wape: 37 },
  { week: "W4", wape: 34 },
  { week: "W5", wape: 33 },
  { week: "W6", wape: 31 },
  { week: "W7", wape: 30 },
  { week: "W8", wape: 29 },
];

export function AccuracyDemo() {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={DEMO} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="week" fontSize={12} tickMargin={8} />
          <YAxis fontSize={12} width={40} unit="%" domain={[0, 50]} />
          <Tooltip formatter={(v) => [`${v}%`, "WAPE"]} />
          <Line
            type="monotone"
            dataKey="wape"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={{ r: 3 }}
            name="WAPE"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
