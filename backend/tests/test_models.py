from civicint.models import (
    Base,
    Case,
    Document,
    DocumentStatus,
    Evidence,
    File,
    FileText,
    LLMUsage,
    Source,
    User,
)


def test_source_model_has_required_columns():
    cols = {c.name for c in Source.__table__.columns}
    assert "municipality" in cols
    assert "platform" in cols
    assert "base_url" in cols
    assert "region" in cols
    assert "scrape_interval_minutes" in cols
    assert "extra_config" in cols


def test_document_has_unique_constraint():
    constraints = Document.__table__.constraints
    col_sets = [
        {c.name for c in constraint.columns}
        for constraint in constraints
        if hasattr(constraint, "columns")
    ]
    assert {"source_id", "external_id"} in col_sets


def test_document_status_enum():
    assert DocumentStatus.NEW.value == "new"
    assert DocumentStatus.BUDGET_PAUSED.value == "budget_paused"


def test_file_text_is_separate_table():
    assert FileText.__tablename__ == "file_texts"
    cols = {c.name for c in FileText.__table__.columns}
    assert "content" in cols
    assert "extraction_method" in cols
    assert "char_count" in cols


def test_case_has_slug():
    cols = {c.name for c in Case.__table__.columns}
    assert "slug" in cols
    assert "permit_number" in cols


def test_all_models_inherit_from_base():
    for model in [Source, Document, File, FileText, Case, Evidence, LLMUsage, User]:
        assert issubclass(model, Base)
