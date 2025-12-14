# Watchdog MVP

Environmental document watchdog for Finnish municipalities. Automatically monitors municipal decision documents and surfaces high-signal environmental cases.

## Quick Start

```bash
# Install dependencies
pip install -e .

# Copy environment template
cp .env.example .env
# Edit .env with your settings

# Initialize database
python -m watchdog.cli init-db

# Run development server
uvicorn watchdog.app.main:app --reload
```

## Project Structure

```
watchdog/
├── app/           # FastAPI web application
├── connectors/    # Platform-specific scrapers
├── pipeline/      # Document processing pipeline
├── db/            # Database models & migrations
└── cli.py         # Admin CLI tools
```

## Configuration

See `.env.example` for all configuration options.

## License

Private - All rights reserved.
