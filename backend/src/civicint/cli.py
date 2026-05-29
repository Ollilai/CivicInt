"""CivicInt CLI — management commands for the municipal document watchdog."""

import asyncio

import click

from civicint.config import get_settings


def _make_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    settings = get_settings()
    engine = create_engine(settings.database_url)
    return sessionmaker(bind=engine)


@click.group()
def main():
    """CivicInt: Finnish municipal document watchdog."""


@main.command()
def init_db():
    """Create all database tables (dev shortcut — use Alembic for production)."""
    from sqlalchemy import create_engine

    from civicint.models import Base

    settings = get_settings()
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    click.echo("Database tables created.")


@main.command()
def seed_lapland():
    """Seed Lapland municipality sources (19 supported platforms)."""
    from civicint.models import Source

    SOURCES = [
        {
            "municipality": "Enontekiö",
            "region": "Lappi",
            "platform": "cloudnc",
            "base_url": "https://enontekio.cloudnc.fi",
            "extra_config": {"municipality": "Enontekiö"},
        },
        {
            "municipality": "Inari",
            "region": "Lappi",
            "platform": "dynasty",
            "base_url": "https://inari.oncloudos.com",
            "extra_config": {"municipality": "Inari"},
        },
        {
            "municipality": "Kemi",
            "region": "Lappi",
            "platform": "dynasty",
            "base_url": "https://kemi.oncloudos.com",
            "extra_config": {"municipality": "Kemi"},
        },
        {
            "municipality": "Kemijärvi",
            "region": "Lappi",
            "platform": "dynasty",
            "base_url": "https://kemijarvi.oncloudos.com",
            "extra_config": {"municipality": "Kemijärvi"},
        },
        {
            "municipality": "Keminmaa",
            "region": "Lappi",
            "platform": "tweb",
            "base_url": "https://keminmaa.tweb.fi",
            "extra_config": {"municipality": "Keminmaa"},
        },
        {
            "municipality": "Kittilä",
            "region": "Lappi",
            "platform": "dynasty",
            "base_url": "https://dynasty10.kittila.fi",
            "extra_config": {"municipality": "Kittilä"},
        },
        {
            "municipality": "Kolari",
            "region": "Lappi",
            "platform": "tweb",
            "base_url": "https://kolari.tweb.fi",
            "extra_config": {"municipality": "Kolari"},
        },
        {
            "municipality": "Muonio",
            "region": "Lappi",
            "platform": "cloudnc",
            "base_url": "https://muonio.cloudnc.fi",
            "extra_config": {"municipality": "Muonio"},
        },
        {
            "municipality": "Pello",
            "region": "Lappi",
            "platform": "tweb",
            "base_url": "https://pello-julkaisu.triplancloud.fi",
            "extra_config": {"municipality": "Pello"},
        },
        {
            "municipality": "Pelkosenniemi",
            "region": "Lappi",
            "platform": "dynasty",
            "base_url": "https://paatoksetd10.pelkosenniemi.fi",
            "extra_config": {"municipality": "Pelkosenniemi"},
        },
        {
            "municipality": "Posio",
            "region": "Lappi",
            "platform": "tweb",
            "base_url": "https://posio.tweb.fi",
            "extra_config": {"municipality": "Posio"},
        },
        {
            "municipality": "Ranua",
            "region": "Lappi",
            "platform": "dynasty",
            "base_url": "https://paatoksetd10.ranua.fi",
            "extra_config": {"municipality": "Ranua"},
        },
        {
            "municipality": "Rovaniemi",
            "region": "Lappi",
            "platform": "cloudnc",
            "base_url": "https://rovaniemi.cloudnc.fi",
            "extra_config": {"municipality": "Rovaniemi"},
        },
        {
            "municipality": "Savukoski",
            "region": "Lappi",
            "platform": "dynasty",
            "base_url": "https://paatoksetd10.savukoski.fi",
            "extra_config": {"municipality": "Savukoski"},
        },
        {
            "municipality": "Simo",
            "region": "Lappi",
            "platform": "dynasty",
            "base_url": "https://simo.oncloudos.com",
            "extra_config": {"municipality": "Simo"},
        },
        {
            "municipality": "Sodankylä",
            "region": "Lappi",
            "platform": "tweb",
            "base_url": "https://sodankyla.tweb.fi",
            "extra_config": {"municipality": "Sodankylä"},
        },
        {
            "municipality": "Tervola",
            "region": "Lappi",
            "platform": "tweb",
            "base_url": "https://tervola.ktweb.fi",
            "extra_config": {"municipality": "Tervola"},
        },
        {
            "municipality": "Tornio",
            "region": "Lappi",
            "platform": "dynasty",
            "base_url": "https://tornio.oncloudos.com",
            "extra_config": {"municipality": "Tornio"},
        },
        {
            "municipality": "Ylitornio",
            "region": "Lappi",
            "platform": "tweb",
            "base_url": "https://ylitornio.tweb.fi",
            "extra_config": {"municipality": "Ylitornio"},
        },
    ]

    factory = _make_session()
    with factory() as session:
        added = 0
        skipped = 0
        for src in SOURCES:
            existing = (
                session.query(Source)
                .filter_by(municipality=src["municipality"], platform=src["platform"])
                .first()
            )
            if existing:
                skipped += 1
                continue
            session.add(Source(**src))
            added += 1

        session.commit()
        click.echo(f"Seeded {added} sources, skipped {skipped} existing.")


@main.command()
@click.option("--source-id", type=int, help="Run discovery for a specific source ID only.")
def discover(source_id):
    """Run document discovery for enabled sources."""
    from civicint.pipeline.discover import run_discover, run_discover_all

    factory = _make_session()
    with factory() as session:
        if source_id:
            count = asyncio.run(run_discover(source_id, session))
            session.commit()
            click.echo(f"Discovered {count} new documents from source {source_id}.")
        else:
            total = asyncio.run(run_discover_all(session))
            session.commit()
            click.echo(f"Discovered {total} new documents total.")


@main.command()
@click.option("--document-id", type=int, help="Fetch files for a specific document.")
def fetch(document_id):
    """Download pending files from discovered documents."""
    from civicint.models import Document, DocumentStatus
    from civicint.pipeline.fetch import run_fetch

    factory = _make_session()
    with factory() as session:
        if document_id:
            asyncio.run(run_fetch(document_id, session))
            session.commit()
            click.echo(f"Fetched files for document {document_id}.")
        else:
            docs = session.query(Document).filter_by(status=DocumentStatus.NEW).all()
            count = 0
            for doc in docs:
                try:
                    asyncio.run(run_fetch(doc.id, session))
                    count += 1
                except Exception as e:
                    click.echo(f"  Fetch error (doc {doc.id}): {e}", err=True)
            session.commit()
            click.echo(f"Fetched files for {count} documents.")


@main.command()
@click.option("--document-id", type=int, help="Extract text from a specific document.")
def extract(document_id):
    """Extract text from downloaded PDFs."""
    from civicint.models import Document, DocumentStatus
    from civicint.pipeline.extract import run_extract

    factory = _make_session()
    with factory() as session:
        if document_id:
            run_extract(document_id, session)
            session.commit()
            click.echo(f"Extracted text for document {document_id}.")
        else:
            docs = session.query(Document).filter_by(status=DocumentStatus.FETCHED).all()
            count = 0
            for doc in docs:
                try:
                    run_extract(doc.id, session)
                    count += 1
                except Exception as e:
                    click.echo(f"  Extract error (doc {doc.id}): {e}", err=True)
            session.commit()
            click.echo(f"Extracted text from {count} documents.")


@main.command()
@click.option("--document-id", type=int, help="Triage a specific document.")
def triage(document_id):
    """Run LLM triage on extracted documents."""
    from civicint.models import Document, DocumentStatus
    from civicint.pipeline.triage import run_triage

    factory = _make_session()
    with factory() as session:
        if document_id:
            run_triage(document_id, session)
            session.commit()
            click.echo(f"Triaged document {document_id}.")
        else:
            docs = session.query(Document).filter_by(status=DocumentStatus.EXTRACTED).all()
            count = 0
            for doc in docs:
                try:
                    run_triage(doc.id, session)
                    count += 1
                except Exception as e:
                    click.echo(f"  Triage error (doc {doc.id}): {e}", err=True)
            session.commit()
            click.echo(f"Triaged {count} documents.")


@main.command()
@click.option("--document-id", type=int, help="Build case from a specific document.")
def build_cases(document_id):
    """Build cases from triaged documents."""
    from civicint.models import Document, DocumentStatus
    from civicint.pipeline.case_builder import run_case_builder

    factory = _make_session()
    with factory() as session:
        if document_id:
            case_id = run_case_builder(document_id, session)
            session.commit()
            click.echo(f"Built/updated case {case_id} from document {document_id}.")
        else:
            docs = (
                session.query(Document)
                .filter_by(status=DocumentStatus.TRIAGED)
                .filter(Document.triage_score >= 0.6)
                .all()
            )
            count = 0
            for doc in docs:
                try:
                    run_case_builder(doc.id, session)
                    count += 1
                except Exception as e:
                    click.echo(f"  Case builder error (doc {doc.id}): {e}", err=True)
            session.commit()
            click.echo(f"Built/updated {count} cases.")


@main.command()
def run_pipeline():
    """Run the full pipeline: discover -> fetch -> extract -> triage -> build_cases."""
    from civicint.models import Document, DocumentStatus, Source
    from civicint.pipeline.case_builder import run_case_builder
    from civicint.pipeline.discover import run_discover
    from civicint.pipeline.extract import run_extract
    from civicint.pipeline.fetch import run_fetch
    from civicint.pipeline.triage import run_triage

    factory = _make_session()

    with factory() as session:
        sources = session.query(Source).filter_by(enabled=True).all()
        click.echo(f"Running pipeline for {len(sources)} sources...")

        # Stage 1: Discover
        total_new = 0
        for source in sources:
            try:
                count = asyncio.run(run_discover(source.id, session))
                total_new += count
            except Exception as e:
                click.echo(f"  Discovery error ({source.municipality}): {e}", err=True)
        session.commit()
        click.echo(f"Discovered {total_new} new documents.")

    with factory() as session:
        # Stage 2: Fetch
        new_docs = session.query(Document).filter_by(status=DocumentStatus.NEW).all()
        for doc in new_docs:
            try:
                asyncio.run(run_fetch(doc.id, session))
            except Exception as e:
                click.echo(f"  Fetch error (doc {doc.id}): {e}", err=True)
        session.commit()
        click.echo(f"Fetched {len(new_docs)} documents.")

    with factory() as session:
        # Stage 3: Extract
        fetched = session.query(Document).filter_by(status=DocumentStatus.FETCHED).all()
        for doc in fetched:
            try:
                run_extract(doc.id, session)
            except Exception as e:
                click.echo(f"  Extract error (doc {doc.id}): {e}", err=True)
        session.commit()
        click.echo(f"Extracted text from {len(fetched)} documents.")

    with factory() as session:
        # Stage 4: Triage
        extracted = session.query(Document).filter_by(status=DocumentStatus.EXTRACTED).all()
        for doc in extracted:
            try:
                run_triage(doc.id, session)
            except Exception as e:
                click.echo(f"  Triage error (doc {doc.id}): {e}", err=True)
        session.commit()
        click.echo(f"Triaged {len(extracted)} documents.")

    with factory() as session:
        # Stage 5: Build cases
        triaged = (
            session.query(Document)
            .filter_by(status=DocumentStatus.TRIAGED)
            .filter(Document.triage_score >= 0.6)
            .all()
        )
        cases_built = 0
        for doc in triaged:
            try:
                result = run_case_builder(doc.id, session)
                if result:
                    cases_built += 1
            except Exception as e:
                click.echo(f"  Case builder error (doc {doc.id}): {e}", err=True)
        session.commit()
        click.echo(f"Built/updated {cases_built} cases.")

    click.echo("Pipeline complete.")


@main.command()
def stats():
    """Show pipeline statistics and LLM spend."""
    from civicint.services.pipeline_service import get_llm_spend, get_pipeline_stats

    factory = _make_session()
    with factory() as session:
        pipeline = get_pipeline_stats(session)
        spend = get_llm_spend(session)

    click.echo("\n--- Pipeline Stats ---")
    click.echo(f"Sources: {pipeline['total_sources']} ({pipeline['enabled_sources']} enabled)")
    click.echo(f"Documents: {pipeline['total_documents']}")
    for status, count in pipeline.get("documents_by_status", {}).items():
        click.echo(f"  {status}: {count}")
    click.echo(f"Cases: {pipeline['total_cases']}")
    click.echo(f"Files: {pipeline['total_files']}")

    click.echo(f"\n--- LLM Spend ({spend['month']}) ---")
    click.echo(f"Total: {spend['total_cost_eur']:.4f} EUR / {spend['budget_eur']:.2f} EUR budget")
    click.echo(f"  Triage: {spend['triage_cost']:.4f} EUR ({spend['documents_triaged']} docs)")
    cb_cost = spend['case_builder_cost']
    click.echo(f"  Case builder: {cb_cost:.4f} EUR ({spend['cases_built']} cases)")


if __name__ == "__main__":
    main()
