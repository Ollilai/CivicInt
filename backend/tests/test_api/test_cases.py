from civicint.models import Case, CaseStatus, Confidence


def _create_case(db_session, slug="test-case", headline="Test case"):
    case = Case(
        slug=slug,
        primary_category="extraction",
        headline=headline,
        summary_md="- Test summary",
        status=CaseStatus.PROPOSED,
        confidence=Confidence.HIGH,
        municipalities_json=["Rovaniemi"],
    )
    db_session.add(case)
    db_session.commit()
    return case


def test_list_cases_empty(client):
    response = client.get("/api/v1/cases")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_cases_with_data(client, db_session):
    _create_case(db_session)
    response = client.get("/api/v1/cases")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "test-case"


def test_get_case_by_slug(client, db_session):
    _create_case(db_session)
    response = client.get("/api/v1/cases/test-case")
    assert response.status_code == 200
    data = response.json()
    assert data["headline"] == "Test case"
    assert data["summary_md"] == "- Test summary"


def test_get_case_not_found(client):
    response = client.get("/api/v1/cases/nonexistent")
    assert response.status_code == 404
