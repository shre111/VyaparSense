"use client";

import * as React from "react";
import { Loader2, UploadCloud } from "lucide-react";
import { ApiError, uploadSalesCsv, type UploadSummary } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Status =
  | { kind: "idle" }
  | { kind: "uploading" }
  | { kind: "done"; summary: UploadSummary }
  | { kind: "error"; message: string };

export function UploadForm() {
  const [tenantId, setTenantId] = React.useState("demo");
  const [file, setFile] = React.useState<File | null>(null);
  const [status, setStatus] = React.useState<Status>({ kind: "idle" });

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file || !tenantId.trim()) return;
    setStatus({ kind: "uploading" });
    try {
      const summary = await uploadSalesCsv(tenantId.trim(), file);
      setStatus({ kind: "done", summary });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Could not reach the API. Is the backend running?";
      setStatus({ kind: "error", message });
    }
  }

  const uploading = status.kind === "uploading";

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Tenant
          <input
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            placeholder="tenant id"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm font-medium">
          Sales history CSV
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm file:mr-4 file:rounded-md file:border-0 file:bg-muted file:px-3 file:py-2 file:text-sm"
          />
        </label>

        <Button type="submit" disabled={!file || uploading} className="self-start">
          {uploading ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <UploadCloud className="h-4 w-4" aria-hidden />
          )}
          {uploading ? "Uploading…" : "Upload"}
        </Button>
      </form>

      {status.kind === "error" && (
        <p role="alert" className="text-sm text-red-600">
          {status.message}
        </p>
      )}

      {status.kind === "done" && <UploadResult summary={status.summary} />}
    </div>
  );
}

function UploadResult({ summary }: { summary: UploadSummary }) {
  const patterns = Object.entries(summary.patterns).sort((a, b) => b[1] - a[1]);
  return (
    <Card>
      <CardHeader>
        <CardTitle>{summary.filename}</CardTitle>
        <p className="text-sm text-muted-foreground">
          Upload #{summary.upload_id} · tenant {summary.tenant_id}
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex gap-8">
          <Stat label="Rows" value={summary.row_count.toLocaleString()} />
          <Stat label="Series" value={summary.series_count.toLocaleString()} />
        </div>
        {patterns.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium">Demand patterns</p>
            <ul className="flex flex-wrap gap-2">
              {patterns.map(([pattern, count]) => (
                <li
                  key={pattern}
                  className="rounded-full border px-3 py-1 text-xs text-muted-foreground"
                >
                  {pattern}: {count}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}
