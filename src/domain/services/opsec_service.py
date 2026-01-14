"""
OpSec Service - Operational Security for Rate Limiting and Anti-Detection.

Implements RNF-01 to RNF-05 from the PRD:
- RNF-01: Daily limit (40-50 applications)
- RNF-02: Warm-up progression for new accounts
- RNF-03: Random delays between actions
- RNF-04: Mandatory pauses every 10 applications
- RNF-05: Abort on consecutive errors
"""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from src.config.settings import Settings


@dataclass
class OpSecState:
    """Current operational security state."""
    
    today: date = field(default_factory=date.today)
    applications_today: int = 0
    consecutive_errors: int = 0
    account_age_days: int = 0
    last_application_time: Optional[datetime] = None
    is_paused: bool = False
    pause_until: Optional[datetime] = None


class OpSecService:
    """
    Operational Security service for safe automation.
    
    This service enforces rate limits, delays, and anti-detection
    measures to avoid LinkedIn account blocking.
    """
    
    # Warm-up progression: day -> max applications
    WARMUP_SCHEDULE = {
        1: 10,
        2: 20,
        3: 30,
    }
    DEFAULT_LIMIT = 40

    def __init__(self, settings: Settings) -> None:
        """Initialize OpSec service with settings."""
        self.settings = settings
        self.state = OpSecState()

    def get_daily_limit(self) -> int:
        """
        Get the daily application limit based on account age (RNF-01, RNF-02).
        
        Returns:
            Maximum allowed applications for today.
        """
        if not self.settings.warmup_enabled:
            return self.settings.daily_limit
            
        if self.state.account_age_days in self.WARMUP_SCHEDULE:
            return self.WARMUP_SCHEDULE[self.state.account_age_days]
            
        return min(self.DEFAULT_LIMIT, self.settings.daily_limit)

    def can_apply(self) -> tuple[bool, str]:
        """
        Check if we can submit another application.
        
        Returns:
            Tuple of (can_apply, reason_if_blocked)
        """
        # Check if we need to reset daily counter
        if self.state.today != date.today():
            self.state.today = date.today()
            self.state.applications_today = 0
            self.state.consecutive_errors = 0
            
        # Check paused state
        if self.state.is_paused:
            if self.state.pause_until and datetime.now() < self.state.pause_until:
                remaining = (self.state.pause_until - datetime.now()).seconds // 60
                return False, f"Pausa obrigatória. Retorno em {remaining} minutos."
            else:
                self.state.is_paused = False
                self.state.pause_until = None
        
        # Check daily limit (RNF-01)
        limit = self.get_daily_limit()
        if self.state.applications_today >= limit:
            return False, f"Limite diário atingido ({limit} candidaturas)."
            
        # Check consecutive errors (RNF-05)
        if self.state.consecutive_errors >= self.settings.max_consecutive_errors:
            return False, f"Muitos erros consecutivos ({self.state.consecutive_errors}). Sessão abortada."
            
        # Check if pause is needed (RNF-04)
        if (
            self.state.applications_today > 0
            and self.state.applications_today % self.settings.pause_after_applications == 0
        ):
            pause_minutes = random.randint(
                self.settings.pause_duration_min,
                self.settings.pause_duration_max,
            )
            self.state.is_paused = True
            self.state.pause_until = datetime.now() + asyncio.timedelta(
                minutes=pause_minutes
            ) if hasattr(asyncio, 'timedelta') else datetime.now()
            # Fallback: use datetime.timedelta
            from datetime import timedelta
            self.state.pause_until = datetime.now() + timedelta(minutes=pause_minutes)
            return False, f"Pausa de {pause_minutes} minutos após {self.settings.pause_after_applications} candidaturas."
            
        return True, ""

    async def wait_before_action(self) -> float:
        """
        Wait random delay before performing an action (RNF-03).
        
        Returns:
            Actual delay in seconds.
        """
        delay = random.uniform(
            self.settings.min_action_delay,
            self.settings.max_action_delay,
        )
        await asyncio.sleep(delay)
        return delay

    async def wait_before_application(self) -> float:
        """
        Wait random delay before submitting application (RNF-03).
        
        Returns:
            Actual delay in seconds.
        """
        delay = random.uniform(
            self.settings.min_application_delay,
            self.settings.max_application_delay,
        )
        await asyncio.sleep(delay)
        return delay

    def record_success(self) -> None:
        """Record a successful application."""
        self.state.applications_today += 1
        self.state.consecutive_errors = 0
        self.state.last_application_time = datetime.now()

    def record_failure(self) -> None:
        """Record a failed application."""
        self.state.consecutive_errors += 1
        self.state.last_application_time = datetime.now()

    def record_skip(self) -> None:
        """Record a skipped job (doesn't count toward limits)."""
        self.state.consecutive_errors = 0

    def set_account_age(self, days: int) -> None:
        """Set the account age for warm-up calculation."""
        self.state.account_age_days = days

    def get_status(self) -> dict:
        """Get current OpSec status for display."""
        limit = self.get_daily_limit()
        return {
            "applications_today": self.state.applications_today,
            "daily_limit": limit,
            "remaining": limit - self.state.applications_today,
            "consecutive_errors": self.state.consecutive_errors,
            "is_paused": self.state.is_paused,
            "account_age_days": self.state.account_age_days,
            "warmup_active": (
                self.settings.warmup_enabled
                and self.state.account_age_days in self.WARMUP_SCHEDULE
            ),
        }

    def reset_daily(self) -> None:
        """Reset daily counters (for testing or manual reset)."""
        self.state.applications_today = 0
        self.state.consecutive_errors = 0
        self.state.today = date.today()

    def force_pause(self, minutes: int) -> None:
        """Force a pause for the specified minutes."""
        from datetime import timedelta
        self.state.is_paused = True
        self.state.pause_until = datetime.now() + timedelta(minutes=minutes)
