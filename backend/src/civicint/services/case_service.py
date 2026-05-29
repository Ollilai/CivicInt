from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from civicint.models import Bookmark, Case, CaseStatus, Confidence


def list_cases(
    db: Session,
    *,
    municipality: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[CaseStatus] = None,
    confidence: Optional[Confidence] = None,
    search: Optional[str] = None,
    user_id: Optional[int] = None,
    bookmarked: bool = False,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Case], int]:
    query = db.query(Case)

    if municipality:
        query = query.filter(Case.municipalities_json.contains([municipality]))
    if category:
        query = query.filter(Case.primary_category == category)
    if status:
        query = query.filter(Case.status == status)
    if confidence:
        query = query.filter(Case.confidence == confidence)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(Case.headline.ilike(pattern), Case.summary_md.ilike(pattern))
        )
    if bookmarked and user_id:
        query = query.join(Bookmark).filter(Bookmark.user_id == user_id)

    total = query.count()
    cases = (
        query.order_by(Case.updated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return cases, total


def get_case_by_slug(db: Session, slug: str) -> Optional[Case]:
    return (
        db.query(Case)
        .options(joinedload(Case.evidence), joinedload(Case.events))
        .filter(Case.slug == slug)
        .first()
    )


def toggle_bookmark(
    db: Session, user_id: int, case_id: int, note: Optional[str] = None
) -> bool:
    existing = (
        db.query(Bookmark)
        .filter(Bookmark.user_id == user_id, Bookmark.case_id == case_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
        return False
    bookmark = Bookmark(user_id=user_id, case_id=case_id, note=note)
    db.add(bookmark)
    db.commit()
    return True
