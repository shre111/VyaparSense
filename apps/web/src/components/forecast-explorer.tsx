"use client";

import * as React from "react";
import { Loader2, LineChart as LineChartIcon } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ApiError,
  type ForecastItem,
  generateForecasts,
  getForecasts,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Status =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; items: ForecastItem[] }
  | { kind: "error"; message: string };

function seriesKey(item: ForecastItem): string {
  return `${item.store_id} · ${item.sku_id}`;
}

export function ForecastExplorer() {
  const [tenantId, setTenantId] = React.useState("demo");
  const [status, setStatus] = React.useState<Status>({ kind: "idle" });
  const [selected, setSelected] = React.useState<string | null>(null);

  async function handleRun(event: React.FormEvent) {
    event.preventDefault();
    if (!tenantId.trim()) return;
    setStatus({ kind: "loading" });
    setSelected(null);
    try {
      const tenant = tenantId.trim();
      await generateForecasts(tenant, 7);
      const items = await getForecasts(tenant);
      setStatus({ kind: "ready", items });
      if (items.length > 0) setSelected(seriesKey(items[0]));
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Could not reach the API. Is the backend running?";
      setStatus({ kind: "error", message });
    }
  }

  const seriesKeys =
    status.kind === "ready"
      ? Array.from(new Set(status.items.map(seriesKey))).sort()
      : [];

  const chartData =
    status.kind === "ready" && selected
      ? status.items
          .filter((it) => seriesKey(it) === selected)
          .sort((a, b) => a.horizon_date.localeCompare(b.horizon_date))
          .map((it) => ({ date: it.horizon_date, units: it.predicted_units }))
      : [];

  const model =
    status.kind === "ready" && selected
      ? status.items.find((it) => seriesKey(it) === selected)?.model
      : undefined;

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={handleRun} className="flex items-end gap-3">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Tenant
          <input
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            placeholder="tenant id"
          />
        </label>
        <Button type="submit" disabled={status.kind === "loading"}>
          {status.kind === "loading" ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <LineChartIcon className="h-4 w-4" aria-hidden />
          )}
          {status.kind === "loading" ? "Forecasting…" : "Run forecast"}
        </Button>
      </form>

      {status.kind === "error" && (
        <p role="alert" className="text-sm text-red-600">
          {status.message}
        </p>
      )}

      {status.kind === "ready" && status.items.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No forecasts yet — upload at least ~5 weeks of sales history for this
          tenant, then run again.
        </p>
      )}

      {status.kind === "ready" && seriesKeys.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>7-day forecast</CardTitle>
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-sm text-muted-foreground">
                Series
                <select
                  value={selected ?? ""}
                  onChange={(e) => setSelected(e.target.value)}
                  className="ml-2 h-9 rounded-md border border-input bg-background px-2 text-sm text-foreground"
                >
                  {seriesKeys.map((key) => (
                    <option key={key} value={key}>
                      {key}
                    </option>
                  ))}
                </select>
              </label>
              {model && (
                <span className="rounded-full border px-3 py-1 text-xs text-muted-foreground">
                  model: {model}
                </span>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="date" fontSize={12} tickMargin={8} />
                  <YAxis fontSize={12} width={40} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="units"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={false}
                    name="predicted units"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
