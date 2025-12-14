"""Seed script to configure all Lapland data sources with exact paths.

Based on manually collected data from Lapland_Data_Sources - Taulukko1.csv

Run with: python -m watchdog.seed_lapland_sources
"""

import json
from urllib.parse import urlparse

from watchdog.db.models import Source, get_session_factory, init_db


# All Lapland sources with their exact URLs for each document type
LAPLAND_SOURCES = [
    # CloudNC municipalities
    {
        "municipality": "Enontekiö",
        "platform": "cloudnc",
        "base_url": "https://enontekio.cloudnc.fi",
        "paths": {
            "meetings": "/fi-FI",
            "officer_decisions": "/fi-FI/Viranhaltijat",
            "announcements": "/fi-FI/Kuulutukset",
            "zoning": "/fi-FI/Kaavat",
        },
    },
    {
        "municipality": "Muonio",
        "platform": "cloudnc",
        "base_url": "https://muonio.cloudnc.fi",
        "paths": {
            "meetings": "/fi-FI",
            "officer_decisions": "/fi-FI/Viranhaltijat",
            "announcements": "/fi-FI/Kuulutukset",
        },
    },
    {
        "municipality": "Rovaniemi",
        "platform": "cloudnc",
        "base_url": "https://rovaniemi.cloudnc.fi",
        "paths": {
            "meetings": "/fi-FI",
            "officer_decisions": "/fi-FI/Viranhaltijat",
            "announcements": "/fi-FI/Kuulutukset",
        },
    },

    # Dynasty municipalities
    {
        "municipality": "Inari",
        "platform": "dynasty",
        "base_url": "https://inari.oncloudos.com",
        "paths": {
            "meetings": "/cgi/DREQUEST.PHP?page=meeting_frames",
            "officer_decisions": "/cgi/DREQUEST.PHP?page=official_frames",
            "announcements": "/cgi/DREQUEST.PHP?alo=1&page=announcement_search&tzo=-180",
        },
    },
    {
        "municipality": "Kemi",
        "platform": "dynasty",
        "base_url": "https://kemi.oncloudos.com",
        "paths": {
            "meetings": "/cgi/DREQUEST.PHP?page=meeting_frames",
            "announcements": "/cgi/DREQUEST.PHP?alo=1&page=announcement_search&tzo=-120",
        },
    },
    {
        "municipality": "Kemijärvi",
        "platform": "dynasty",
        "base_url": "https://kemijarvi.oncloudos.com",
        "paths": {
            "meetings": "/cgi/DREQUEST.PHP?page=meeting_frames",
            "officer_decisions": "/cgi/DREQUEST.PHP?page=official_frames",
            "announcements": "/cgi/DREQUEST.PHP?alo=1&page=announcement_search&tzo=-120",
        },
    },
    {
        "municipality": "Kittilä",
        "platform": "dynasty",
        "base_url": "https://dynasty10.kittila.fi",
        "paths": {
            "meetings": "/cgi/DREQUEST.PHP?page=meeting_frames",
            "officer_decisions": "/cgi/DREQUEST.PHP?page=official_frames",
            "announcements": "/cgi/DREQUEST.PHP?alo=1&page=announcement_search&tzo=-120",
        },
    },
    {
        "municipality": "Pelkosenniemi",
        "platform": "dynasty",
        "base_url": "https://paatoksetd10.pelkosenniemi.fi",
        "paths": {
            "meetings": "/cgi/DREQUEST.PHP?page=meeting_handlers&id=",
            "officer_decisions": "/cgi/DREQUEST.PHP?page=official_frames",
        },
    },
    {
        "municipality": "Ranua",
        "platform": "dynasty",
        "base_url": "https://paatoksetd10.ranua.fi",
        "paths": {
            "meetings": "/cgi/DREQUEST.PHP?page=meeting_frames",
            "officer_decisions": "/cgi/DREQUEST.PHP?page=official_frames",
        },
    },
    {
        "municipality": "Savukoski",
        "platform": "dynasty",
        "base_url": "https://paatoksetd10.savukoski.fi",
        "paths": {
            "meetings": "/cgi/DREQUEST.PHP?page=meeting_frames",
            "officer_decisions": "/cgi/DREQUEST.PHP?page=official_frames",
            "announcements": "/cgi/DREQUEST.PHP?alo=1&page=announcement_search&tzo=-120",
        },
    },
    {
        "municipality": "Simo",
        "platform": "dynasty",
        "base_url": "https://simo.oncloudos.com",
        "paths": {
            "meetings": "/cgi/DREQUEST.PHP?page=meeting_frames",
            "officer_decisions": "/cgi/DREQUEST.PHP?page=official_frames",
        },
    },
    {
        "municipality": "Tornio",
        "platform": "dynasty",
        "base_url": "https://tornio.oncloudos.com",
        "paths": {
            "meetings": "/cgi/DREQUEST.PHP?page=meeting_frames",
            "officer_decisions": "/cgi/DREQUEST.PHP?page=official_frames",
        },
    },

    # TWeb municipalities
    {
        "municipality": "Keminmaa",
        "platform": "tweb",
        "base_url": "https://keminmaa.tweb.fi",
        "paths": {
            "meetings": "/ktwebscr/pk_tek_tweb.htm",
            "agendas": "/ktwebscr/epj_tek_tweb.htm",
            "officer_decisions": "/ktwebscr/vparhaku_tweb.htm",
            "announcements": "/ktwebscr/kuullist_tweb.htm",
        },
    },
    {
        "municipality": "Kolari",
        "platform": "tweb",
        "base_url": "https://kolari.tweb.fi",
        "paths": {
            "meetings": "/ktwebscr/pk_tek_tweb.htm",
            "agendas": "/ktwebscr/epj_tek_tweb.htm",
            "officer_decisions": "/ktwebscr/vparhaku_tweb.htm",
            "announcements": "/ktwebscr/kuullist_tweb.htm",
        },
    },
    {
        "municipality": "Pello",
        "platform": "tweb",
        "base_url": "https://pello-julkaisu.triplancloud.fi",
        "paths": {
            "meetings": "/ktwebscr/pk_tek_tweb.htm",
            "agendas": "/ktwebscr/epj_tek_tweb.htm",
            "officer_decisions": "/ktwebscr/vparhaku_tweb.htm",
            "announcements": "/ktwebscr/kuullist_tweb.htm",
        },
    },
    {
        "municipality": "Posio",
        "platform": "tweb",
        "base_url": "https://posio.tweb.fi",
        "paths": {
            "meetings": "/ktwebscr/pk_tek_tweb.htm",
            "agendas": "/ktwebbin/dbisa.dll/ktwebscr/epj_tek_tweb.htm",
            "officer_decisions": "/ktwebscr/vparhaku_tweb.htm",
            "announcements": "/ktwebscr/kuullist_tweb.htm",
        },
    },
    {
        "municipality": "Salla",
        "platform": "tweb",
        "base_url": "http://salla.tweb.fi",
        "paths": {
            "meetings": "/ktwebbin/dbisa.dll/ktwebscr/pk_tek_tweb.htm",
            "agendas": "/ktwebbin/dbisa.dll/ktwebscr/epj_tek_tweb.htm",
            "officer_decisions": "/ktwebbin/dbisa.dll/ktwebscr/vparhaku_tweb.htm",
            "announcements": "/ktwebbin/dbisa.dll/ktwebscr/kuullist_tweb.htm",
        },
    },
    {
        "municipality": "Sodankylä",
        "platform": "tweb",
        "base_url": "https://sodankyla.tweb.fi",
        "paths": {
            "meetings": "/ktwebscr/pk_tek_tweb.htm",
            "agendas": "/ktwebscr/epj_tek_tweb.htm",
            "officer_decisions": "/ktwebscr/vparhaku_tweb.htm",
            "announcements": "/ktwebscr/kuullist_tweb.htm",
        },
    },
    {
        "municipality": "Tervola",
        "platform": "tweb",
        "base_url": "http://tervola.ktweb.fi",
        "paths": {
            "meetings": "/ktwebbin/dbisa.dll/ktwebscr/pk_tek.htm",
            "agendas": "/ktwebbin/dbisa.dll/ktwebscr/epj_tek.htm",
        },
    },
    {
        "municipality": "Ylitornio",
        "platform": "tweb",
        "base_url": "https://ylitornio.tweb.fi",
        "paths": {
            "meetings": "/ktwebscr/pk_tek_tweb.htm",
            "agendas": "/ktwebscr/epj_kokl_tweb.htm",
            "officer_decisions": "/ktwebscr/vparhaku_tweb.htm",
            "announcements": "/ktwebscr/kuullist_tweb.htm",
        },
    },

    # WordPress/Municipal website sources
    {
        "municipality": "Utsjoki",
        "platform": "municipal_website",
        "base_url": "https://www.utsjoki.fi",
        "paths": {
            "meetings": "/kunta-ja-paatoksenteko/paatoksenteko/esityslistat-ja-poytakirjat/",
            "officer_decisions": "/kunta-ja-paatoksenteko/paatoksenteko/viranhaltijapaatokset/",
        },
    },

    # Regional organizations
    {
        "municipality": "Lapin Liitto",
        "platform": "dynasty",
        "base_url": "https://lapinliittod10.oncloudos.com",
        "paths": {
            "meetings": "/cgi/DREQUEST.PHP?page=meeting_handlers&id=",
            "officer_decisions": "/cgi/DREQUEST.PHP?page=official_handlers&id=",
        },
    },
    {
        "municipality": "Lapin ELY-keskus",
        "platform": "municipal_website",
        "base_url": "https://www.ely-keskus.fi",
        "paths": {
            "announcements": "/-/lap-kuulutukset",
        },
    },
    {
        "municipality": "Lapin hyvinvointialue",
        "platform": "tweb",
        "base_url": "https://lapha-julkaisu.tweb.fi",
        "paths": {
            "meetings": "/ktwebscr/pk_tek_tweb.htm",
            "agendas": "/ktwebscr/epj_tek_tweb.htm",
            "officer_decisions": "/ktwebscr/vparhaku_tweb.htm",
            "announcements": "/ktwebscr/kuullist_tweb.htm",
        },
    },
]


def seed_sources():
    """Seed all Lapland sources into the database."""
    Session = get_session_factory()

    with Session() as session:
        added = 0
        updated = 0
        skipped = 0

        for source_data in LAPLAND_SOURCES:
            municipality = source_data["municipality"]
            platform = source_data["platform"]

            # Check if source exists
            existing = session.query(Source).filter_by(
                municipality=municipality,
            ).first()

            config_json = {
                "municipality": municipality,
                "paths": source_data["paths"],
            }

            if existing:
                # Update existing source
                existing.platform = platform
                existing.base_url = source_data["base_url"]
                existing.config_json = config_json
                existing.enabled = True
                updated += 1
                print(f"✓ Updated: {municipality} ({platform})")
            else:
                # Create new source
                source = Source(
                    municipality=municipality,
                    platform=platform,
                    base_url=source_data["base_url"],
                    enabled=True,
                    config_json=config_json,
                )
                session.add(source)
                added += 1
                print(f"✓ Added: {municipality} ({platform})")

        session.commit()

        print(f"\n📊 Summary:")
        print(f"   Added: {added}")
        print(f"   Updated: {updated}")
        print(f"   Total: {len(LAPLAND_SOURCES)} sources")


def main():
    """Main entry point."""
    print("🌲 Seeding Lapland data sources...")
    print("-" * 50)

    # Ensure database is initialized
    init_db()

    # Seed sources
    seed_sources()

    print("\n✅ Done! All Lapland sources have been configured.")
    print("   Run 'watchdog-cli health' to verify.")


if __name__ == "__main__":
    main()
