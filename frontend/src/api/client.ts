import type {
  AuditTrail,
  ChatReply,
  ColumnProfile,
  ColumnSuggestion,
  DatasetSummary,
  PipelineConfigIn,
  PreviewResult,
  RecommendationResult,
  RunPipelineResult,
} from "../types";

export const API_BASE = "http://127.0.0.1:8000";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadDatasets(files: File[]): Promise<DatasetSummary[]> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  const res = await fetch(`${API_BASE}/api/datasets/upload`, { method: "POST", body: form });
  return handle(res);
}

export async function listDatasets(): Promise<DatasetSummary[]> {
  const res = await fetch(`${API_BASE}/api/datasets`);
  return handle(res);
}

export async function getProfile(datasetId: string): Promise<ColumnProfile[]> {
  const res = await fetch(`${API_BASE}/api/datasets/${datasetId}/profile`);
  return handle(res);
}

export async function getPreview(datasetId: string, limit = 25): Promise<PreviewResult> {
  const res = await fetch(`${API_BASE}/api/datasets/${datasetId}/preview?limit=${limit}`);
  return handle(res);
}

export async function runPipeline(datasetId: string, config: PipelineConfigIn): Promise<RunPipelineResult> {
  const res = await fetch(`${API_BASE}/api/pipeline/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_id: datasetId, config }),
  });
  return handle(res);
}

export async function combineDatasets(
  datasetIds: string[],
  mode: "concat" | "merge",
  on: string[] | null,
  how: "outer" | "left" | "right" | "inner"
): Promise<{ dataset_id: string; name: string; rows: number; columns: number; report: unknown }> {
  const res = await fetch(`${API_BASE}/api/pipeline/combine`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_ids: datasetIds, mode, on, how }),
  });
  return handle(res);
}

export async function generateSynthetic(
  datasetId: string,
  nRows: number,
  seed: number | null,
  augment: boolean
): Promise<{ dataset_id: string; name: string; rows: number; columns: number; report: unknown }> {
  const res = await fetch(`${API_BASE}/api/pipeline/synthetic`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_id: datasetId, n_rows: nRows, seed, augment }),
  });
  return handle(res);
}

export async function getAuditTrail(datasetId: string): Promise<AuditTrail> {
  const res = await fetch(`${API_BASE}/api/datasets/${datasetId}/audit`);
  return handle(res);
}

export async function getSuggestions(datasetId: string): Promise<ColumnSuggestion[]> {
  const res = await fetch(`${API_BASE}/api/pipeline/${datasetId}/suggestions`);
  return handle(res);
}

export function downloadUrl(datasetId: string, format: "csv" | "json" | "xlsx"): string {
  return `${API_BASE}/api/datasets/${datasetId}/download?format=${format}`;
}

export async function getRecommendations(datasetId: string, targetColumn?: string | null): Promise<RecommendationResult> {
  const res = await fetch(`${API_BASE}/api/assistant/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_id: datasetId, target_column: targetColumn ?? null }),
  });
  return handle(res);
}

export async function sendChatMessage(datasetId: string, message: string): Promise<ChatReply> {
  const res = await fetch(`${API_BASE}/api/assistant/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_id: datasetId, message }),
  });
  return handle(res);
}
