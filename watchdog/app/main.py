"""FastAPI application for Watchdog MVP."""

import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from watchdog.config import get_settings
from watchdog.db.models import get_session_factory, init_db


# Paths
APP_DIR = Path(__file__).parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: ensure database exists
    init_db()
    
    # Ensure data directories exist
    settings = get_settings()
    Path(settings.storage_path).mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Shutdown: cleanup if needed


# Create app
app = FastAPI(
    title="Watchdog",
    description="Environmental document watchdog for Finnish municipalities",
    lifespan=lifespan,
)

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Static files
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Database dependency
def get_db():
    """Get database session."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Admin authentication dependency
def verify_admin_token(token: str = Query(None, alias="token")) -> bool:
    """
    Verify admin token for protected routes.

    SECURITY: Requires ADMIN_TOKEN to be set in environment.
    Uses constant-time comparison to prevent timing attacks.
    """
    settings = get_settings()

    if not settings.admin_token:
        raise HTTPException(
            status_code=503,
            detail="Admin access not configured. Set ADMIN_TOKEN in environment."
        )

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Admin token required. Add ?token=YOUR_TOKEN to URL."
        )

    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(token, settings.admin_token):
        raise HTTPException(status_code=403, detail="Invalid admin token.")

    return True


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    """Home page - redirect to feed or login."""
    # TODO: Check if user is authenticated
    return RedirectResponse(url="/feed")


@app.get("/feed", response_class=HTMLResponse)
async def feed(request: Request, db: Session = Depends(get_db)):
    """Case feed page."""
    from watchdog.db.models import Case, Source
    import json
    
    # Get recent cases
    cases = db.query(Case).order_by(Case.updated_at.desc()).limit(50).all()
    
    # Get ALL municipalities from Sources (not just those with cases)
    sources = db.query(Source).filter(Source.enabled == True).all()
    municipalities = sorted(set(s.municipality for s in sources))
    
    return templates.TemplateResponse(
        "feed.html",
        {
            "request": request,
            "cases": cases,
            "municipalities": municipalities,
            "title": "Tapaukset",
        }
    )


@app.get("/case/{case_id}", response_class=HTMLResponse)
async def dossier(request: Request, case_id: int, db: Session = Depends(get_db)):
    """Case dossier (detail) page."""
    from watchdog.db.models import Case
    
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return RedirectResponse(url="/feed")
    
    return templates.TemplateResponse(
        "dossier.html",
        {
            "request": request,
            "case": case,
            "title": case.headline,
        }
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_admin_token),
):
    """Admin dashboard. Requires admin token for access."""
    from watchdog.db.models import Source, Document, Case, LLMUsage
    from datetime import datetime
    
    # Stats
    sources = db.query(Source).all()
    doc_count = db.query(Document).count()
    case_count = db.query(Case).count()
    
    # LLM spend this month
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    llm_records = db.query(LLMUsage).filter(LLMUsage.created_at >= month_start).all()
    llm_spend = sum(r.estimated_cost_eur for r in llm_records)
    
    settings = get_settings()
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "sources": sources,
            "doc_count": doc_count,
            "case_count": case_count,
            "llm_spend": llm_spend,
            "llm_budget": settings.llm_monthly_budget,
            "title": "Admin Dashboard",
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
