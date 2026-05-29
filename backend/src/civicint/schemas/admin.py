from pydantic import BaseModel


class PipelineStats(BaseModel):
    total_sources: int
    enabled_sources: int
    total_documents: int
    documents_by_status: dict[str, int]
    total_cases: int
    total_files: int


class LLMSpend(BaseModel):
    month: str
    total_cost_eur: float
    budget_eur: float
    triage_cost: float
    case_builder_cost: float
    documents_triaged: int
    cases_built: int
