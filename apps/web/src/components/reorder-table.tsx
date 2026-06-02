"use client";

import * as React from "react";
import { Loader2, PackageCheck } from "lucide-react";
import {
  ApiError,
  getReorderSuggestions,
  type ReorderItem,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type Status =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; rows: ReorderItem[] }
  | { kind: "error"; message: string };

function NumberField({
  label,
  value,
  onChange,
  step = "1",
  min,
  max,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: string;
  min?: number;
  max?: number;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm font-medium">
      {label}
      <input
        type="number"
        value={value}
        step={step}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-10 w-32 rounded-md border border-input bg-background px-3 text-sm"
      />
    </label>
  );
}

export function ReorderTable() {
  const [tenantId, setTenantId] = React.useState("demo");
  const [leadTimeDays, setLeadTimeDays] = React.useState(7);
  const [serviceLevel, setServiceLevel] = React.useState(0.95);
  const [onHand, setOnHand] = React.useState(0);
  const [status, setStatus] = React.useState<Status>({ kind: "idle" });

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!tenantId.trim()) return;
    setStatus({ kind: "loading" });
    try {
      const rows = await getReorderSuggestions(tenantId.trim(), {
        leadTimeDays,
        serviceLevel,
        onHand,
      });
      setStatus({ kind: "ready", rows });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Could not reach the API. Is the backend running?";
      setStatus({ kind: "error", message });
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Tenant
          <input
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            className="h-10 w-40 rounded-md border border-input bg-background px-3 text-sm"
            placeholder="tenant id"
          />
        </label>
        <NumberField
          label="Lead time (days)"
          value={leadTimeDays}
          onChange={setLeadTimeDays}
          min={1}
          max={90}
        />
        <NumberField
          label="Service level"
          value={serviceLevel}
          onChange={setServiceLevel}
          step="0.01"
          min={0.5}
          max={0.999}
        />
        <NumberField label="On hand" value={onHand} onChange={setOnHand} min={0} />
        <Button type="submit" disabled={status.kind === "loading"}>
          {status.kind === "loading" ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <PackageCheck className="h-4 w-4" aria-hidden />
          )}
          {status.kind === "loading" ? "Computing…" : "Get suggestions"}
        </Button>
      </form>

      {status.kind === "error" && (
        <p role="alert" className="text-sm text-red-600">
          {status.message}
        </p>
      )}

      {status.kind === "ready" && status.rows.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No suggestions — upload at least ~2 weeks of sales history for this
          tenant first.
        </p>
      )}

      {status.kind === "ready" && status.rows.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Store</TableHead>
              <TableHead>SKU</TableHead>
              <TableHead className="text-right">Reorder point</TableHead>
              <TableHead className="text-right">Safety stock</TableHead>
              <TableHead className="text-right">Order qty</TableHead>
              <TableHead className="text-right">Days cover</TableHead>
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {status.rows.map((r) => (
              <TableRow key={`${r.store_id}/${r.sku_id}`}>
                <TableCell>{r.store_id}</TableCell>
                <TableCell>{r.sku_id}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {r.reorder_point.toFixed(1)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {r.safety_stock.toFixed(1)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {r.order_quantity.toFixed(1)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {Number.isFinite(r.days_of_cover)
                    ? r.days_of_cover.toFixed(1)
                    : "∞"}
                </TableCell>
                <TableCell>
                  {r.should_reorder ? (
                    <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                      reorder
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">ok</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
