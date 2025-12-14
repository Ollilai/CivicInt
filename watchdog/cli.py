"""Watchdog CLI for admin tasks."""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

from watchdog.config import get_settings
from watchdog.db.models import Base, Source, get_engine, get_session_factory, init_db


def cmd_init_db(args):
    """Initialize the database."""
    print("Initializing database...")
    init_db()
    print("✓ Database tables created successfully.")


def detect_platform(url: str) -> str:
    """Detect platform type from URL."""
    if not url:
        return "unknown"
    url_lower = url.lower()
    if "cloudnc.fi" in url_lower:
        return "cloudnc"
    elif "oncloudos.com" in url_lower:
        return "dynasty"
    elif "dynasty" in url_lower:
        return "dynasty"
    elif "tweb" in url_lower or "ktweb" in url_lower:
        return "tweb"
    elif ".fi" in url_lower:
        return "web"  # Generic web scraper
    return "unknown"


def cmd_seed_lapland(args):
    """Seed Lapland municipality sources from CSV."""
    # Find the CSV file
    project_root = Path(__file__).parent.parent
    csv_path = project_root / "Lapland_Data_Sources - Taulukko1.csv"
    
    if not csv_path.exists():
        print(f"✗ CSV file not found: {csv_path}")
        return
    
    print(f"Reading sources from: {csv_path}")
    
    Session = get_session_factory()
    added_count = 0
    skipped_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        with Session() as session:
            for row in reader:
                municipality = row['Kunta'].strip()
                
                # Each column represents a different source type
                source_types = [
                    ('esityslistat', row.get('Esityslistat', '').strip()),
                    ('poytakirjat', row.get('Pöytäkirjat', '').strip()),
                    ('viranhaltija', row.get('Viranhaltijapäätökset', '').strip()),
                    ('kuulutukset', row.get('Kuulutukset', '').strip()),
                    ('kaavat', row.get('Kaavat', '').strip()),
                ]
                
                for source_type, url in source_types:
                    if not url:
                        continue
                    
                    platform = detect_platform(url)
                    
                    # Check if source already exists
                    existing = session.query(Source).filter_by(
                        municipality=municipality,
                        base_url=url
                    ).first()
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    source = Source(
                        municipality=municipality,
                        platform=platform,
                        base_url=url,
                        enabled=True,
                        config_json={'source_type': source_type}
                    )
                    session.add(source)
                    added_count += 1
                    print(f"  + {municipality} ({source_type}): {platform}")
                
            session.commit()
    
    print(f"\n✓ Seeding complete: {added_count} added, {skipped_count} skipped (already exist)")


def cmd_health(args):
    """Check connector health."""
    Session = get_session_factory()
    with Session() as session:
        sources = session.query(Source).all()
        
        if not sources:
            print("No sources configured. Add sources with 'add-source' command.")
            return
        
        print(f"\n{'Municipality':<20} {'Platform':<10} {'Status':<10} {'Last Success':<20} {'Errors'}")
        print("-" * 80)
        
        for source in sources:
            status = "✓ OK" if source.consecutive_failures == 0 else f"✗ {source.consecutive_failures} fails"
            last_success = source.last_success_at.strftime("%Y-%m-%d %H:%M") if source.last_success_at else "Never"
            print(f"{source.municipality:<20} {source.platform:<10} {status:<10} {last_success:<20}")


def cmd_add_source(args):
    """Add a new source."""
    Session = get_session_factory()
    with Session() as session:
        # Check if source already exists
        existing = session.query(Source).filter_by(
            municipality=args.municipality,
            platform=args.platform
        ).first()
        
        if existing:
            print(f"Source for {args.municipality} ({args.platform}) already exists.")
            return
        
        source = Source(
            municipality=args.municipality,
            platform=args.platform,
            base_url=args.base_url,
            enabled=True,
        )
        session.add(source)
        session.commit()
        print(f"✓ Added source: {args.municipality} ({args.platform})")


def cmd_run_pipeline(args):
    """Run the processing pipeline."""
    print("Running pipeline...")
    # Import here to avoid circular imports
    from watchdog.pipeline import discover, fetch, extract, triage, case_builder
    
    stage = args.stage or "all"
    
    if stage in ("all", "discover"):
        print("→ Running discovery...")
        discover.run()
    
    if stage in ("all", "fetch"):
        print("→ Running fetch...")
        fetch.run()
    
    if stage in ("all", "extract"):
        print("→ Running extraction...")
        extract.run()
    
    if stage in ("all", "triage"):
        print("→ Running triage...")
        triage.run()
    
    if stage in ("all", "build"):
        print("→ Running case builder...")
        case_builder.run()
    
    print("✓ Pipeline complete.")


def cmd_stats(args):
    """Show database statistics."""
    from watchdog.db.models import Document, File, Case, User, LLMUsage
    
    Session = get_session_factory()
    with Session() as session:
        sources = session.query(Source).count()
        documents = session.query(Document).count()
        files = session.query(File).count()
        cases = session.query(Case).count()
        users = session.query(User).count()
        
        # LLM spend this month
        from datetime import datetime
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        llm_spend = session.query(LLMUsage).filter(
            LLMUsage.created_at >= month_start
        ).with_entities(
            LLMUsage.estimated_cost_eur
        ).all()
        total_spend = sum(r[0] for r in llm_spend) if llm_spend else 0.0
        
        settings = get_settings()
        budget = settings.llm_monthly_budget
        
        print(f"\n📊 Watchdog Statistics")
        print("-" * 40)
        print(f"Sources:    {sources}")
        print(f"Documents:  {documents}")
        print(f"Files:      {files}")
        print(f"Cases:      {cases}")
        print(f"Users:      {users}")
        print(f"\n💰 LLM Spend (this month): €{total_spend:.2f} / €{budget:.2f}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="watchdog-cli",
        description="Watchdog admin CLI"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # init-db
    parser_init = subparsers.add_parser("init-db", help="Initialize database")
    parser_init.set_defaults(func=cmd_init_db)
    
    # health
    parser_health = subparsers.add_parser("health", help="Check connector health")
    parser_health.set_defaults(func=cmd_health)
    
    # seed-lapland
    parser_seed = subparsers.add_parser("seed-lapland", help="Seed Lapland municipality sources from CSV")
    parser_seed.set_defaults(func=cmd_seed_lapland)
    
    # add-source
    parser_add = subparsers.add_parser("add-source", help="Add a new source")
    parser_add.add_argument("--municipality", "-m", required=True, help="Municipality name")
    parser_add.add_argument("--platform", "-p", required=True, choices=["cloudnc", "dynasty", "tweb", "pdf"])
    parser_add.add_argument("--base-url", "-u", required=True, help="Base URL for the source")
    parser_add.set_defaults(func=cmd_add_source)
    
    # run-pipeline
    parser_run = subparsers.add_parser("run-pipeline", help="Run processing pipeline")
    parser_run.add_argument("--stage", "-s", choices=["discover", "fetch", "extract", "triage", "build", "all"])
    parser_run.set_defaults(func=cmd_run_pipeline)
    
    # stats
    parser_stats = subparsers.add_parser("stats", help="Show database statistics")
    parser_stats.set_defaults(func=cmd_stats)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
