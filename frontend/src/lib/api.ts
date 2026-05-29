import type {
  CaseListItem,
  CaseDetail,
  MunicipalityItem,
  PaginatedResponse,
  PipelineStats,
  LLMSpend,
  Source,
  CaseFilters,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// --- Cases ---

export async function getCases(
  filters: CaseFilters = {}
): Promise<PaginatedResponse<CaseListItem>> {
  const params = new URLSearchParams();
  if (filters.page) params.set("page", String(filters.page));
  if (filters.per_page) params.set("per_page", String(filters.per_page));
  if (filters.municipality) params.set("municipality", filters.municipality);
  if (filters.category) params.set("category", filters.category);
  if (filters.status) params.set("status", filters.status);
  if (filters.confidence) params.set("confidence", filters.confidence);
  if (filters.search) params.set("search", filters.search);

  const query = params.toString();
  return fetchAPI<PaginatedResponse<CaseListItem>>(
    `/cases${query ? `?${query}` : ""}`
  );
}

export async function getCaseBySlug(slug: string): Promise<CaseDetail> {
  return fetchAPI<CaseDetail>(`/cases/${slug}`);
}

// --- Municipalities ---

export async function getMunicipalities(): Promise<MunicipalityItem[]> {
  return fetchAPI<MunicipalityItem[]>("/municipalities");
}

// --- Admin ---

export async function getSources(): Promise<Source[]> {
  return fetchAPI<Source[]>("/admin/sources");
}

export async function getPipelineStats(): Promise<PipelineStats> {
  return fetchAPI<PipelineStats>("/admin/pipeline/stats");
}

export async function getLLMSpend(): Promise<LLMSpend> {
  return fetchAPI<LLMSpend>("/admin/pipeline/spend");
}

// --- Health ---

export async function ping(): Promise<{ status: string }> {
  return fetchAPI<{ status: string }>("/ping");
}
