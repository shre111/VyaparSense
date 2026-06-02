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

/** Upload a sales-history CSV for a tenant; returns the parsed summary. */
export async function uploadSalesCsv(
  tenantId: string,
  file: File,
): Promise<UploadSummary> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(
    `${API_BASE_URL}/tenants/${encodeURIComponent(tenantId)}/uploads`,
    { method: "POST", body: form },
  );
  if (!res.ok) {
    throw new ApiError(res.status, await detail(res));
  }
  return (await res.json()) as UploadSummary;
}
