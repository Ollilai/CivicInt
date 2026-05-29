
from sqlalchemy import func
from sqlalchemy.orm import Session

from civicint.models import Case, Source


def list_sources(db: Session) -> list[Source]:
    return db.query(Source).order_by(Source.municipality).all()


def get_municipalities(db: Session) -> list[dict]:
    results = (
        db.query(
            Source.municipality,
            Source.region,
            func.count(Source.id).label("source_count"),
        )
        .filter(Source.enabled.is_(True))
        .group_by(Source.municipality, Source.region)
        .order_by(Source.municipality)
        .all()
    )

    municipalities = []
    for row in results:
        case_count = (
            db.query(func.count(Case.id))
            .filter(Case.municipalities_json.contains([row.municipality]))
            .scalar()
        )
        municipalities.append({
            "name": row.municipality,
            "region": row.region,
            "source_count": row.source_count,
            "case_count": case_count or 0,
        })
    return municipalities


def create_source(db: Session, *, municipality: str, region: str | None, platform: str,
                  base_url: str, scrape_interval_minutes: int = 120,
                  extra_config: dict | None = None) -> Source:
    source = Source(
        municipality=municipality,
        region=region,
        platform=platform,
        base_url=base_url,
        scrape_interval_minutes=scrape_interval_minutes,
        extra_config=extra_config,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source
