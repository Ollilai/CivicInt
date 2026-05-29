from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from civicint.api.deps import get_db
from civicint.schemas.sources import MunicipalityItem
from civicint.services.source_service import get_municipalities

router = APIRouter(prefix="/municipalities", tags=["municipalities"])


@router.get("", response_model=list[MunicipalityItem])
def list_municipalities(db: Session = Depends(get_db)):
    return get_municipalities(db)
