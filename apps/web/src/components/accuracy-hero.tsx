"use client";

import * as React from "react";
import { Loader2, Sparkles, TrendingDown } from "lucide-react";
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
  type AccuracyPoint,
  ApiError,
  backfillAccuracy,
  getAccuracy,
  getSimulationKpis,
  type KpiComparison,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fieldClass } from "@/components/ui/input";

type Status =
  | { kind: "idle" }
  | { kind: "working"; label: string }
  | { kind: "ready"; points: AccuracyPoint[]; kpis: KpiComparison }
  | { kind: "error"; message: string };

const PARAMS = { leadTimeDays: 7, serviceLevel: 0.95, onHand: 0 };

export function AccuracyHero() {
  const [historyEnd, setHistoryEnd] = React.useState("2025-12-30");
  const [status, setStatus] = React.useState<Status>({ kind: "idle" });

  const errorMessage = (err: unknown) =>
    err instanceof ApiError
      ? err.message
      : "Could not reach the API. Is the backend running?";

  async function load() {
    const [points, kpis] = await Promise.all([getAccuracy(), getSimulationKpis(PARAMS)]);
    setStatus({ kind: "ready", points, kpis });
  }

  async function handleLoad(event: React.FormEvent) {
    event.preventDefault();
    setStatus({ kind: "working", label: "Loading…" });
    try {
      await load();
    } catch (err) {
      setStatus({ kind: "error", message: errorMessage(err) });
    }
  }

  async function handleBackfill() {
    setStatus({ kind: "working", label: "Building accuracy history…" });
    try {
      await backfillAccuracy({ lastSaleDate: historyEnd });
      await load();
    } catch (err) {
      setStatus({ kind: "error", message: errorMessage(err) });
    }
  }

  const working = status.kind === "working";
  const chartData =
    status.kind === "ready"
      ? status.points
          .filter((p) => p.wape !== null)
          .map((p) => ({ period: p.period, wape: Number((p.wape! * 100).toFixed(2)) }))
      : [];

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleLoad} className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1.5 text-sm font-medium">
              History ends
              <input
                type="date"
                value={historyEnd}
                onChange={(e) => setHistoryEnd(e.target.value)}
                className={fieldClass}
              />
            </label>
            <Button type="submit" variant="outline" disabled={working}>
              {working && status.label === "Loading…" ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : null}
              Load
            </Button>
            <Button type="button" onClick={handleBackfill} disabled={working}>
              {working && status.label.startsWith("Building") ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Sparkles className="h-4 w-4" aria-hidden />
              )}
              Build accuracy history
            </Button>
          </form>
        </CardContent>
      </Card>

      {status.kind === "error" && (
        <p role="alert" className="text-sm text-destructive">
          {status.message}
        </p>
      )}

      {status.kind === "ready" && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Forecast accuracy over time</CardTitle>
              <p className="text-sm text-muted-foreground">
                Weekly WAPE (lower is better). Lower over time = the model
                getting smarter.
              </p>
            </CardHeader>
            <CardContent>
              {chartData.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No accuracy data yet — click “Build accuracy history” to
                  generate forecasts against past weeks for this tenant.
                </p>
              ) : (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={chartData}
                      margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="period" fontSize={12} tickMargin={8} />
                      <YAxis fontSize={12} width={44} unit="%" />
                      <Tooltip formatter={(v: number) => [`${v}%`, "WAPE"]} />
                      <Line
                        type="monotone"
                        dataKey="wape"
                        stroke="hsl(var(--primary))"
                        strokeWidth={2}
                        dot={{ r: 2 }}
                        name="WAPE"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          <KpiCards kpis={status.kpis} />
        </>
      )}
    </div>
  );
}

function KpiCards({ kpis }: { kpis: KpiComparison }) {
  if (kpis.series_simulated === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No KPI comparison yet — upload sales history for this tenant first.
      </p>
    );
  }
  const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Lost-sales reduction
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="flex items-center gap-2 text-2xl font-bold text-accent">
            <TrendingDown className="h-5 w-5" aria-hidden />
            {pct(kpis.lost_sales_reduction_pct)}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            forecast-driven vs naive policy
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Fill rate
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{pct(kpis.forecast_fill_rate)}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            naive {pct(kpis.naive_fill_rate)}
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Units lost
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">
            {Math.round(kpis.forecast_units_lost).toLocaleString()}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            naive {Math.round(kpis.naive_units_lost).toLocaleString()}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
