"""Tests for LLM budget checking."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from civicint.models import LLMUsage
from civicint.pipeline.budget import check_budget


class TestCheckBudget:
    def test_empty_usage_within_budget(self, db_session):
        within, spent, limit = check_budget(db_session)
        assert within is True
        assert spent == 0.0
        assert limit > 0

    def test_under_budget(self, db_session):
        usage = LLMUsage(
            model="gpt-4o-mini",
            stage="triage",
            prompt_tokens=1000,
            completion_tokens=100,
            estimated_cost_eur=0.50,
        )
        db_session.add(usage)
        db_session.commit()

        within, spent, limit = check_budget(db_session)
        assert within is True
        assert abs(spent - 0.50) < 1e-6

    def test_over_budget(self, db_session):
        with patch("civicint.pipeline.budget.get_settings") as mock_settings:
            mock_settings.return_value.llm_monthly_budget = 1.0

            usage = LLMUsage(
                model="gpt-4o",
                stage="case_builder",
                prompt_tokens=50000,
                completion_tokens=5000,
                estimated_cost_eur=2.0,
            )
            db_session.add(usage)
            db_session.commit()

            within, spent, limit = check_budget(db_session)
            assert within is False
            assert spent >= 2.0
            assert limit == 1.0

    def test_old_usage_not_counted(self, db_session):
        """Usage from a previous month should not count against current budget."""
        old_time = datetime.now(UTC) - timedelta(days=35)
        usage = LLMUsage(
            model="gpt-4o-mini",
            stage="triage",
            prompt_tokens=1000,
            completion_tokens=100,
            estimated_cost_eur=5.0,
        )
        db_session.add(usage)
        db_session.commit()

        # Manually backdate the record (SQLite doesn't support server_default well)
        usage.created_at = old_time
        db_session.commit()

        within, spent, _limit = check_budget(db_session)
        assert within is True
        assert spent == 0.0
