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
  createForecastJob,
  type ForecastItem,
  type ForecastJobState,
  getForecasts,
  pollForecastJob,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fieldClass } from "@/components/ui/input";

type Status =
  | { kind: "idle" }
  | { kind: "running"; state: ForecastJobState }
  | { kind: "ready"; items: ForecastItem[] }
  | { kind: "error"; message: string };

function seriesKey(item: ForecastItem): string {
  return `${item.store_id} · ${item.sku_id}`;
}

const _RUN_LABEL: Record<ForecastJobState, string> = {
  queued: "Queued…",
  running: "Forecasting…",
  completed: "Loading results…",
  failed: "Failed",
};

export function ForecastExplorer() {
  const [status, setStatus] = React.useState<Status>({ kind: "idle" });
  const [selected, setSelected] = React.useState<string | null>(null);

  // Show any forecasts already computed by a previous job so a completed run is
  // visible without re-running the (slow) ladder — and so a client-side poll
  // timeout doesn't hide results the backend has already stored.
  React.useEffect(() => {
    let active = true;
    getForecasts()
      .then((items) => {
        if (!active || items.length === 0) return;
        setStatus({ kind: "ready", items });
        setSelected(seriesKey(items[0]));
      })
      .catch(() => {
        /* no existing forecasts / not signed in yet — stay idle */
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleRun(event: React.FormEvent) {
    event.preventDefault();
    setStatus({ kind: "running", state: "queued" });
    setSelected(null);
    try {
      // Forecasts run as an async job (ADR-007): enqueue, poll, then read.
      const job = await createForecastJob(7);
      const done = await pollForecastJob(job.job_id, {
        // The inline ladder (statsforecast + global LightGBM over full history)
        // can run well past 10 min on a dev box; give it room to finish.
        timeoutMs: 1_800_000,
        onUpdate: (s) => setStatus({ kind: "running", state: s.status }),
      });
      if (done.status === "failed") {
        setStatus({ kind: "error", message: done.error ?? "The forecast job failed." });
        return;
      }
      const items = await getForecasts();
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

  const running = status.kind === "running";
  const runLabel = status.kind === "running" ? _RUN_LABEL[status.state] : "Run forecast";

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
      <Card>
        <CardContent className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-6">
          <form onSubmit={handleRun}>
            <Button type="submit" disabled={running}>
              {running ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <LineChartIcon className="h-4 w-4" aria-hidden />
              )}
              {runLabel}
            </Button>
          </form>
          <p className="text-xs text-muted-foreground">
            Runs the full model ladder as a background job.
          </p>
        </CardContent>
      </Card>

      {status.kind === "error" && (
        <p role="alert" className="text-sm text-destructive">
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
                  className={`${fieldClass} ml-2 h-9`}
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
