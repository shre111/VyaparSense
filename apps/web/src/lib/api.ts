/**
 * Thin typed client for the VyaparSense FastAPI backend (`apps/api`).
 *
 * The browser talks only to the API over HTTPS (ADR-003) — never the DB. The
 * base URL comes from `NEXT_PUBLIC_API_BASE_URL` (see `.env.example`).
 *
 * Auth (ADR-006): `/auth/login` and `/auth/signup` return a short-lived access
 * token (held in memory here) and set an httpOnly refresh cookie. Business calls
 * go through `authedFetch`, which attaches the bearer token and, on a 401,
 * transparently tries `/auth/refresh` once (rotating the cookie) before failing.
 * The tenant is derived server-side from the token, so no tenant id is sent.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// --- types ------------------------------------------------------------------

export interface AuthResult {
  access_token: string;
  token_type: string;
  user_id: number;
  tenant_id: string;
  email: string;
}

export interface CurrentUser {
  user_id: number;
  tenant_id: string;
  email: string;
}

export interface UploadSummary {
  upload_id: number;
  tenant_id: string;
  filename: string;
  row_count: number;
  series_count: number;
  patterns: Record<string, number>;
}

export interface ForecastRunSummary {
  tenant_id: string;
  horizon: number;
  series_forecast: number;
  forecasts_created: number;
}

export interface ForecastItem {
  store_id: string;
  sku_id: string;
  model: string;
  horizon_date: string; // ISO date
  predicted_units: number;
}

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

export interface AccuracyPoint {
  period: string; // ISO year-week, e.g. "2024-W05"
  n: number;
  wape: number | null; // null when undefined (zero actual demand that week)
}

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

// --- access-token store (in memory; refresh lives in the httpOnly cookie) ----

let _accessToken: string | null = null;

/** Set/clear the in-memory access token (called by the auth context). */
export function setAccessToken(token: string | null): void {
  _accessToken = token;
}

export function getAccessToken(): string | null {
  return _accessToken;
}

// --- low-level helpers ------------------------------------------------------

async function detail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // non-JSON error body; fall through to status text
  }
  return res.statusText || `request failed (${res.status})`;
}

function authHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  if (_accessToken) headers.set("Authorization", `Bearer ${_accessToken}`);
  return headers;
}

/** Try to refresh the access token using the httpOnly refresh cookie. */
async function tryRefresh(): Promise<boolean> {
  const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) return false;
  const body = (await res.json()) as AuthResult;
  _accessToken = body.access_token;
  return true;
}

/**
 * Fetch with the bearer token attached. On a 401 (expired access token), tries
 * a single refresh and replays the request once. Sends cookies so the refresh
 * flow works.
 */
async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const opts: RequestInit = { ...init, credentials: "include", headers: authHeaders(init.headers) };
  let res = await fetch(`${API_BASE_URL}${path}`, opts);
  if (res.status === 401 && (await tryRefresh())) {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: authHeaders(init.headers),
    });
  }
  return res;
}

async function authedJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await authedFetch(path, init);
  if (!res.ok) throw new ApiError(res.status, await detail(res));
  return (await res.json()) as T;
}

// --- auth -------------------------------------------------------------------

export async function login(email: string, password: string): Promise<AuthResult> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new ApiError(res.status, await detail(res));
  const body = (await res.json()) as AuthResult;
  _accessToken = body.access_token;
  return body;
}

export async function signup(
  tenantId: string,
  email: string,
  password: string,
): Promise<AuthResult> {
  const res = await fetch(`${API_BASE_URL}/auth/signup`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tenant_id: tenantId, email, password }),
  });
  if (!res.ok) throw new ApiError(res.status, await detail(res));
  const body = (await res.json()) as AuthResult;
  _accessToken = body.access_token;
  return body;
}

/** Resolve the current user from a refresh cookie (used to restore a session). */
export async function fetchCurrentUser(): Promise<CurrentUser> {
  return authedJson<CurrentUser>("/auth/me");
}

export function logout(): void {
  _accessToken = null;
}

// --- business endpoints (tenant derived from the token, server-side) --------

export async function uploadSalesCsv(file: File): Promise<UploadSummary> {
  const form = new FormData();
  form.append("file", file);
  return authedJson<UploadSummary>("/uploads", { method: "POST", body: form });
}

export async function generateForecasts(horizon = 7, asOf?: string): Promise<ForecastRunSummary> {
  const params = new URLSearchParams({ horizon: String(horizon) });
  if (asOf) params.set("as_of", asOf);
  return authedJson<ForecastRunSummary>(`/forecasts?${params.toString()}`, { method: "POST" });
}

export async function getForecasts(filter?: {
  storeId?: string;
  skuId?: string;
}): Promise<ForecastItem[]> {
  const params = new URLSearchParams();
  if (filter?.storeId) params.set("store_id", filter.storeId);
  if (filter?.skuId) params.set("sku_id", filter.skuId);
  const qs = params.toString();
  return authedJson<ForecastItem[]>(`/forecasts${qs ? `?${qs}` : ""}`);
}

export interface ReorderParams {
  leadTimeDays: number;
  serviceLevel: number;
  onHand: number;
}

export async function getReorderSuggestions(params: ReorderParams): Promise<ReorderItem[]> {
  const qs = new URLSearchParams({
    lead_time_days: String(params.leadTimeDays),
    service_level: String(params.serviceLevel),
    on_hand: String(params.onHand),
  }).toString();
  return authedJson<ReorderItem[]>(`/reorder-suggestions?${qs}`);
}

export async function getAccuracy(): Promise<AccuracyPoint[]> {
  return authedJson<AccuracyPoint[]>("/accuracy");
}

export async function getSimulationKpis(params: ReorderParams): Promise<KpiComparison> {
  const qs = new URLSearchParams({
    lead_time_days: String(params.leadTimeDays),
    service_level: String(params.serviceLevel),
  }).toString();
  return authedJson<KpiComparison>(`/simulation-kpis?${qs}`);
}

/**
 * Backfill the accuracy history by generating forecasts at several past weekly
 * cutoffs, so horizon dates overlap realised actuals and the curve fills in.
 */
export async function backfillAccuracy(opts: {
  lastSaleDate: string;
  weeks?: number;
  horizon?: number;
}): Promise<number> {
  const horizon = opts.horizon ?? 7;
  const weeks = opts.weeks ?? 8;
  const last = new Date(`${opts.lastSaleDate}T00:00:00Z`);
  let count = 0;
  for (let i = 1; i <= weeks; i++) {
    const cutoff = new Date(last);
    cutoff.setUTCDate(cutoff.getUTCDate() - horizon - i * 7);
    const asOf = cutoff.toISOString().slice(0, 10);
    await generateForecasts(horizon, asOf);
    count += 1;
  }
  return count;
}
