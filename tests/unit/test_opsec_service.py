"""
Unit tests for OpSecService.

Tests for RNF-01 to RNF-05 compliance.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from src.config.settings import Settings
from src.domain.services.opsec_service import OpSecService, OpSecState


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        daily_limit=50,
        warmup_enabled=True,
        max_consecutive_errors=3,
        pause_after_applications=10,
        pause_duration_min=15,
        pause_duration_max=30,
        min_action_delay=1.5,
        max_action_delay=4.0,
        min_application_delay=120.0,
        max_application_delay=600.0,
    )


@pytest.fixture
def opsec(settings: Settings) -> OpSecService:
    """Create OpSec service instance."""
    return OpSecService(settings)


class TestDailyLimit:
    """Tests for RNF-01: Daily limit."""
    
    def test_can_apply_when_under_limit(self, opsec: OpSecService):
        """Should allow applications when under daily limit."""
        opsec.state.applications_today = 11  # Use non-multiple of 10 to avoid pause trigger
        can_apply, reason = opsec.can_apply()
        assert can_apply is True
        assert reason == ""
    
    def test_cannot_apply_when_at_limit(self, opsec: OpSecService):
        """Should block applications when at daily limit."""
        opsec.state.applications_today = 50
        can_apply, reason = opsec.can_apply()
        assert can_apply is False
        assert "Limite diário" in reason
    
    def test_resets_counter_on_new_day(self, opsec: OpSecService):
        """Should reset counter when day changes."""
        opsec.state.applications_today = 50
        opsec.state.today = date.today() - timedelta(days=1)
        
        can_apply, _ = opsec.can_apply()
        
        assert opsec.state.applications_today == 0
        assert opsec.state.today == date.today()


class TestWarmup:
    """Tests for RNF-02: Account warm-up."""
    
    def test_warmup_day_1_limit(self, opsec: OpSecService):
        """Day 1 should limit to 10 applications."""
        opsec.state.account_age_days = 1
        limit = opsec.get_daily_limit()
        assert limit == 10
    
    def test_warmup_day_2_limit(self, opsec: OpSecService):
        """Day 2 should limit to 20 applications."""
        opsec.state.account_age_days = 2
        limit = opsec.get_daily_limit()
        assert limit == 20
    
    def test_warmup_day_3_limit(self, opsec: OpSecService):
        """Day 3 should limit to 30 applications."""
        opsec.state.account_age_days = 3
        limit = opsec.get_daily_limit()
        assert limit == 30
    
    def test_warmup_day_4_plus(self, opsec: OpSecService):
        """Day 4+ should use default limit."""
        opsec.state.account_age_days = 4
        limit = opsec.get_daily_limit()
        assert limit == 40  # DEFAULT_LIMIT


class TestRecordApplications:
    """Tests for application recording."""
    
    def test_record_success_increments_counter(self, opsec: OpSecService):
        """Recording success should increment counter."""
        initial = opsec.state.applications_today
        opsec.record_success()
        assert opsec.state.applications_today == initial + 1
    
    def test_record_success_resets_errors(self, opsec: OpSecService):
        """Recording success should reset consecutive errors."""
        opsec.state.consecutive_errors = 2
        opsec.record_success()
        assert opsec.state.consecutive_errors == 0
    
    def test_record_failure_increments_errors(self, opsec: OpSecService):
        """Recording failure should increment consecutive errors."""
        opsec.record_failure()
        assert opsec.state.consecutive_errors == 1


class TestConsecutiveErrors:
    """Tests for RNF-05: Abort on consecutive errors."""
    
    def test_blocks_after_max_errors(self, opsec: OpSecService):
        """Should block after max consecutive errors."""
        opsec.state.consecutive_errors = 3
        can_apply, reason = opsec.can_apply()
        assert can_apply is False
        assert "erros consecutivos" in reason


class TestStatus:
    """Tests for status reporting."""
    
    def test_get_status_returns_correct_values(self, opsec: OpSecService):
        """Status should return current state values."""
        opsec.state.applications_today = 25
        opsec.state.consecutive_errors = 1
        opsec.state.account_age_days = 2
        
        status = opsec.get_status()
        
        assert status["applications_today"] == 25
        assert status["daily_limit"] == 20  # warmup day 2
        assert status["remaining"] == -5  # over limit due to warmup
        assert status["consecutive_errors"] == 1
        assert status["warmup_active"] is True
