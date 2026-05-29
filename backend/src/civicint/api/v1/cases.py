
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from civicint.api.deps import get_current_user, get_db
from civicint.models.enums import CaseStatus, Confidence
from civicint.schemas.cases import CaseDetail, CaseEventItem, CaseListItem, EvidenceItem
from civicint.schemas.common import PaginatedResponse
from civicint.services.case_service import get_case_by_slug, list_cases

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=PaginatedResponse[CaseListItem])
def get_cases(
    municipality: str | None = None,
    category: str | None = None,
    status: CaseStatus | None = None,
    confidence: Confidence | None = None,
    search: str | None = None,
    bookmarked: bool = False,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = getattr(user, "id", None)
    cases, total = list_cases(
        db,
        municipality=municipality,
        category=category,
        status=status,
        confidence=confidence,
        search=search,
        user_id=user_id,
        bookmarked=bookmarked,
        page=page,
        per_page=per_page,
    )
    pages = (total + per_page - 1) // per_page

    items = []
    for case in cases:
        municipalities = case.municipalities_json or []
        items.append(
            CaseListItem(
                id=case.id,
                slug=case.slug,
                headline=case.headline,
                primary_category=case.primary_category,
                status=case.status,
                confidence=case.confidence,
                municipalities=municipalities,
                first_seen_at=case.first_seen_at,
                updated_at=case.updated_at,
                is_bookmarked=False,
            )
        )

    return PaginatedResponse(
        items=items, total=total, page=page, per_page=per_page, pages=pages
    )


@router.get("/{slug}", response_model=CaseDetail)
def get_case(slug: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    case = get_case_by_slug(db, slug)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return CaseDetail(
        id=case.id,
        slug=case.slug,
        headline=case.headline,
        primary_category=case.primary_category,
        status=case.status,
        confidence=case.confidence,
        municipalities=case.municipalities_json or [],
        first_seen_at=case.first_seen_at,
        updated_at=case.updated_at,
        summary_md=case.summary_md,
        confidence_reason=case.confidence_reason,
        permit_number=case.permit_number,
        entities=case.entities_json,
        locations=case.locations_json,
        evidence=[
            EvidenceItem(
                id=e.id, page=e.page, snippet=e.snippet,
                source_url=e.source_url, created_at=e.created_at,
            )
            for e in case.evidence
        ],
        events=[
            CaseEventItem(
                id=ev.id, event_type=ev.event_type, event_time=ev.event_time,
                payload=ev.payload_json, created_at=ev.created_at,
            )
            for ev in case.events
        ],
    )
