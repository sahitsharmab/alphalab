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

// --- Investment Workspace (ADR-010) ---

export interface EvidenceItem {
  id: string;
  label: string;
  value: number | null;
  display: string;
  as_of: string;
  source: string;
  trust_level?: number | null;
  url?: string | null;
}

/** Editorial playbook context for a scheduled event — judgment, not evidence. */
export interface CatalystAssessment {
  playbook_version: string;
  kind: string;
  importance: string;
  typical_time_et: string;
  why_it_matters: string;
  transmission: string[];
  watch: string[];
  supportive_scenario: string;
  adverse_scenario: string;
  horizon: string;
}

export interface WorkspaceStatement {
  text: string;
  evidence_ids: string[];
  assessment?: CatalystAssessment | null;
}

export interface WorkspaceSection {
  id: string;
  title: string;
  statements: WorkspaceStatement[];
  evidence: EvidenceItem[];
}

export interface WorkspaceView {
  symbol: string;
  name: string;
  currency: string;
  exchange: string;
  generated_at: string;
  quote: { price: number; price_date: string; change_1d: number | null };
  price_history: { date: string; close: number }[];
  sections: WorkspaceSection[];
}

export function getWorkspace(
  symbol: string,
  refresh = false,
): Promise<WorkspaceView> {
  const query = refresh ? "?refresh=true" : "";
  return request<WorkspaceView>(
    `/api/v1/workspace/${encodeURIComponent(symbol)}${query}`,
  );
}

export interface ManualAnalysisPacket {
  prompt_version: string;
  content: string;
}

export function getManualAnalysisPacket(
  symbol: string,
): Promise<ManualAnalysisPacket> {
  return request<ManualAnalysisPacket>(
    `/api/v1/workspace/${encodeURIComponent(symbol)}/manual-analysis`,
  );
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
