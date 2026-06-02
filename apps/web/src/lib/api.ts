/**
 * Thin typed client for the VyaparSense FastAPI backend (`apps/api`).
 *
 * The browser talks only to the API over HTTPS (ADR-003) — never the DB. The
 * base URL comes from `NEXT_PUBLIC_API_BASE_URL` (see `.env.example`).
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** Shape of `UploadSummary` returned by `POST /tenants/{id}/uploads`. */
export interface UploadSummary {
  upload_id: number;
  tenant_id: string;
  filename: string;
  row_count: number;
  series_count: number;
  patterns: Record<string, number>;
}

/** Summary returned by `POST /tenants/{id}/forecasts`. */
export interface ForecastRunSummary {
  tenant_id: string;
  horizon: number;
  series_forecast: number;
  forecasts_created: number;
}

/** One forecast point from `GET /tenants/{id}/forecasts`. */
export interface ForecastItem {
  store_id: string;
  sku_id: string;
  model: string;
  horizon_date: string; // ISO date
  predicted_units: number;
}

/** One reorder recommendation from `GET /tenants/{id}/reorder-suggestions`. */
export interface ReorderItem {
  store_id: string;
  sku_id: string;
  service_level: number;
  lead_time_days: number;
  on_hand: number;
  reorder_point: number;
  safety_stock: number;
  should_reorder: boolean;
  order_quantity: number;
  days_of_cover: number;
}

/** One point on the accuracy-over-time curve from `GET /tenants/{id}/accuracy`. */
export interface AccuracyPoint {
  period: string; // ISO year-week, e.g. "2024-W05"
  n: number;
  wape: number | null; // null when undefined (zero actual demand that week)
}

/** Before/after policy KPIs from `GET /tenants/{id}/simulation-kpis`. */
export interface KpiComparison {
  series_simulated: number;
  naive_fill_rate: number;
  forecast_fill_rate: number;
  naive_units_lost: number;
  forecast_units_lost: number;
  lost_sales_reduction_pct: number;
  naive_avg_on_hand: number;
  forecast_avg_on_hand: number;
}

/** Raised for non-2xx API responses, carrying the server's detail message. */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function detail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // non-JSON error body; fall through to status text
  }
  return res.statusText || `request failed (${res.status})`;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, init);
  if (!res.ok) {
    throw new ApiError(res.status, await detail(res));
  }
  return (await res.json()) as T;
}

function tenantPath(tenantId: string, suffix: string): string {
  return `/tenants/${encodeURIComponent(tenantId)}${suffix}`;
}

/** Upload a sales-history CSV for a tenant; returns the parsed summary. */
export async function uploadSalesCsv(
  tenantId: string,
  file: File,
): Promise<UploadSummary> {
  const form = new FormData();
  form.append("file", file);
  return requestJson<UploadSummary>(tenantPath(tenantId, "/uploads"), {
    method: "POST",
    body: form,
  });
}

/** Generate and persist `horizon`-day forecasts for the tenant's series.
 *
 * With `asOf` (an ISO date), forecasts run forward from that past cutoff so
 * their horizon dates fall on days that already have realised actuals — used to
 * backfill the accuracy curve.
 */
export async function generateForecasts(
  tenantId: string,
  horizon = 7,
  asOf?: string,
): Promise<ForecastRunSummary> {
  const params = new URLSearchParams({ horizon: String(horizon) });
  if (asOf) params.set("as_of", asOf);
  return requestJson<ForecastRunSummary>(
    tenantPath(tenantId, `/forecasts?${params.toString()}`),
    { method: "POST" },
  );
}

/** Read the tenant's forecasts, optionally filtered to one `(store, sku)`. */
export async function getForecasts(
  tenantId: string,
  filter?: { storeId?: string; skuId?: string },
): Promise<ForecastItem[]> {
  const params = new URLSearchParams();
  if (filter?.storeId) params.set("store_id", filter.storeId);
  if (filter?.skuId) params.set("sku_id", filter.skuId);
  const qs = params.toString();
  return requestJson<ForecastItem[]>(
    tenantPath(tenantId, `/forecasts${qs ? `?${qs}` : ""}`),
  );
}

/** Reorder-policy inputs (API query params; not yet persisted server-side). */
export interface ReorderParams {
  leadTimeDays: number;
  serviceLevel: number;
  onHand: number;
}

/** Per-series reorder suggestions from `GET /tenants/{id}/reorder-suggestions`. */
export async function getReorderSuggestions(
  tenantId: string,
  params: ReorderParams,
): Promise<ReorderItem[]> {
  const qs = new URLSearchParams({
    lead_time_days: String(params.leadTimeDays),
    service_level: String(params.serviceLevel),
    on_hand: String(params.onHand),
  }).toString();
  return requestJson<ReorderItem[]>(
    tenantPath(tenantId, `/reorder-suggestions?${qs}`),
  );
}

/** Rolling-WAPE-by-week accuracy curve from `GET /tenants/{id}/accuracy`. */
export async function getAccuracy(tenantId: string): Promise<AccuracyPoint[]> {
  return requestJson<AccuracyPoint[]>(tenantPath(tenantId, "/accuracy"));
}

/** Before/after policy KPIs from `GET /tenants/{id}/simulation-kpis`. */
export async function getSimulationKpis(
  tenantId: string,
  params: ReorderParams,
): Promise<KpiComparison> {
  const qs = new URLSearchParams({
    lead_time_days: String(params.leadTimeDays),
    service_level: String(params.serviceLevel),
  }).toString();
  return requestJson<KpiComparison>(
    tenantPath(tenantId, `/simulation-kpis?${qs}`),
  );
}

/**
 * Backfill the accuracy history by generating forecasts at several past weekly
 * cutoffs, so horizon dates overlap realised actuals and the curve fills in.
 *
 * `lastSaleDate` is the most recent date with sales; we step back weekly from
 * `horizon` days before it (leaving room for the forecast to land on actuals)
 * for `weeks` cutoffs. Returns how many cutoffs were generated.
 */
export async function backfillAccuracy(
  tenantId: string,
  opts: { lastSaleDate: string; weeks?: number; horizon?: number },
): Promise<number> {
  const horizon = opts.horizon ?? 7;
  const weeks = opts.weeks ?? 8;
  const last = new Date(`${opts.lastSaleDate}T00:00:00Z`);
  let count = 0;
  for (let i = 1; i <= weeks; i++) {
    const cutoff = new Date(last);
    cutoff.setUTCDate(cutoff.getUTCDate() - horizon - i * 7);
    const asOf = cutoff.toISOString().slice(0, 10);
    await generateForecasts(tenantId, horizon, asOf);
    count += 1;
  }
  return count;
}
