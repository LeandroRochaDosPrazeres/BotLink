"""
Storage Port - Abstract interface for data persistence.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Optional

from src.domain.entities import Application, ApplicationStatus
from src.domain.value_objects import Credentials, JobFilter


class StoragePort(ABC):
    """Abstract interface for data storage."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize storage connection."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close storage connection."""
        pass
    
    # Config
    @abstractmethod
    async def get_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a config value."""
        pass
    
    @abstractmethod
    async def set_config(self, key: str, value: str) -> None:
        """Set a config value."""
        pass
    
    # Credentials
    @abstractmethod
    async def save_credentials(self, credentials: Credentials) -> None:
        """Save credentials."""
        pass
    
    @abstractmethod
    async def get_credentials(self) -> Optional[Credentials]:
        """Get stored credentials."""
        pass
    
    # Job Filter
    @abstractmethod
    async def save_job_filter(self, job_filter: JobFilter) -> None:
        """Save job filter settings."""
        pass
    
    @abstractmethod
    async def get_job_filter(self) -> Optional[JobFilter]:
        """Get saved job filter."""
        pass
    
    # Applications
    @abstractmethod
    async def save_application(self, application: Application) -> int:
        """Save an application record."""
        pass
    
    @abstractmethod
    async def get_application(self, job_id: str) -> Optional[Application]:
        """Get an application by job_id."""
        pass
    
    @abstractmethod
    async def job_already_applied(self, job_id: str) -> bool:
        """Check if already applied to a job."""
        pass
    
    @abstractmethod
    async def get_applications(
        self,
        limit: int = 100,
        status: Optional[ApplicationStatus] = None,
        since: Optional[datetime] = None,
    ) -> list[Application]:
        """Get application records."""
        pass
    
    @abstractmethod
    async def get_today_count(self) -> int:
        """Get today's application count."""
        pass
    
    # Statistics
    @abstractmethod
    async def increment_daily_stats(self, dt: Optional[date] = None) -> None:
        """Increment daily counter."""
        pass
    
    @abstractmethod
    async def get_daily_stats(self, dt: Optional[date] = None) -> int:
        """Get daily application count."""
        pass
