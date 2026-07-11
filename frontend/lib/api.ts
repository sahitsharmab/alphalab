/** Typed client for the AlphaLab backend API. */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface Observation {
  series_id: string;
  observation_date: string; // ISO date
  as_of: string; // ISO datetime
  value: string; // exact decimal as string
}

export interface SeriesInfo {
  series_id: string;
  provider: string;
  name: string;
  unit: string;
  description: string;
}

export interface IngestionReport {
  provider: string;
  dataset: string;
  raw_payload_id: number;
  raw_payload_reused: boolean;
  observations_parsed: number;
  observations_inserted: number;
  retrieved_at: string;
}

export const SERIES = {
  yoy: "nowflation.headline.yoy",
  index: "nowflation.headline.index",
  coverage: "nowflation.headline.coverage",
} as const;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${await response.text()}`);
  }
  return (await response.json()) as T;
}

export function getObservations(
  seriesId: string,
  start?: string,
): Promise<Observation[]> {
  const query = start ? `?start=${start}` : "";
  return request<Observation[]>(
    `/api/v1/macro/series/${seriesId}/observations${query}`,
  );
}

export function ingestNowflation(): Promise<IngestionReport> {
  return request<IngestionReport>("/api/v1/macro/ingest/nowflation", {
    method: "POST",
  });
}

export interface Health {
  status: "ok" | "degraded";
  environment: string;
  version: string;
  database: { status: string; latency_ms: number | null; error: string | null };
}

export function getHealth(): Promise<Health> {
  return request<Health>("/api/v1/health");
}
