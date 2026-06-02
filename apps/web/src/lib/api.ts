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

/** Generate and persist `horizon`-day forecasts for the tenant's series. */
export async function generateForecasts(
  tenantId: string,
  horizon = 7,
): Promise<ForecastRunSummary> {
  return requestJson<ForecastRunSummary>(
    tenantPath(tenantId, `/forecasts?horizon=${horizon}`),
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
