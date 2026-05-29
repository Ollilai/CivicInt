from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from civicint.api.deps import get_db
from civicint.schemas.admin import LLMSpend, PipelineStats
from civicint.schemas.sources import SourceCreate, SourceHealth
from civicint.services.pipeline_service import get_llm_spend, get_pipeline_stats
from civicint.services.source_service import create_source, list_sources

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/sources", response_model=list[SourceHealth])
def get_sources(db: Session = Depends(get_db)):
    return list_sources(db)


@router.post("/sources", response_model=SourceHealth, status_code=201)
def add_source(body: SourceCreate, db: Session = Depends(get_db)):
    source = create_source(
        db,
        municipality=body.municipality,
        region=body.region,
        platform=body.platform,
        base_url=body.base_url,
        scrape_interval_minutes=body.scrape_interval_minutes,
        extra_config=body.extra_config,
    )
    return source


@router.get("/pipeline/stats", response_model=PipelineStats)
def pipeline_stats(db: Session = Depends(get_db)):
    return get_pipeline_stats(db)


@router.get("/pipeline/spend", response_model=LLMSpend)
def llm_spend(db: Session = Depends(get_db)):
    return get_llm_spend(db)
