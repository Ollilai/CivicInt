// TypeScript types matching the backend Pydantic schemas

export interface CaseListItem {
  id: number;
  slug: string;
  primary_category: string;
  headline: string;
  status: string; // "valitusaika" | "nahtavilla" | "vireilla" | "lainvoimainen"
  municipalities: string[] | null;
  meeting_date: string | null;
  action_deadline: string | null;
  first_seen_at: string;
  updated_at: string;
}

export interface EvidenceItem {
  id: number;
  page: number | null;
  snippet: string;
  source_url: string;
  created_at: string;
}

export interface CaseEventItem {
  id: number;
  event_type: string;
  event_time: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export interface CaseDetail extends CaseListItem {
  summary_md: string;
  evidence: EvidenceItem[];
  events: CaseEventItem[];
  entities: Record<string, unknown> | null;
  locations: Record<string, unknown> | null;
  permit_number: string | null;
}

export interface MunicipalityItem {
  name: string;
  case_count: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface PipelineStats {
  total_sources: number;
  enabled_sources: number;
  total_documents: number;
  documents_by_status: Record<string, number>;
  total_cases: number;
  total_files: number;
}

export interface LLMSpend {
  month: string;
  total_cost_eur: number;
  budget_eur: number;
  triage_cost: number;
  case_builder_cost: number;
  documents_triaged: number;
  cases_built: number;
}

export interface Source {
  id: number;
  name: string;
  platform: string;
  municipality: string;
  base_url: string;
  enabled: boolean;
  last_discovered_at: string | null;
  last_error: string | null;
}

export interface CaseFilters {
  page?: number;
  per_page?: number;
  municipality?: string;
  category?: string;
  status?: string;
  search?: string;
}
