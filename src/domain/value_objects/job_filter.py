"""
JobFilter Value Object - Immutable job search filters.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class JobFilter:
    """
    Immutable value object for job search filters.
    
    Corresponds to FE-01 job panel configuration.
    
    Attributes:
        keywords: List of job title keywords to search
        location: Target location (city, state, country)
        remote_only: Filter for remote jobs only
        easy_apply_only: Filter for Easy Apply jobs only
    """
    
    keywords: tuple[str, ...] = field(default_factory=tuple)
    location: str = ""
    remote_only: bool = False
    easy_apply_only: bool = True

    def __post_init__(self) -> None:
        """Convert mutable lists to immutable tuples."""
        if isinstance(self.keywords, list):
            object.__setattr__(self, "keywords", tuple(self.keywords))

    @property
    def is_configured(self) -> bool:
        """Check if any filters are set."""
        return bool(self.keywords or self.location)

    @property
    def search_query(self) -> str:
        """Generate LinkedIn search query string."""
        return " OR ".join(self.keywords) if self.keywords else ""

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "keywords": list(self.keywords),
            "location": self.location,
            "remote_only": self.remote_only,
            "easy_apply_only": self.easy_apply_only,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobFilter":
        """Create JobFilter from dictionary."""
        return cls(
            keywords=tuple(data.get("keywords", [])),
            location=data.get("location", ""),
            remote_only=data.get("remote_only", False),
            easy_apply_only=data.get("easy_apply_only", True),
        )

    def with_keywords(self, keywords: list[str]) -> "JobFilter":
        """Create new filter with updated keywords."""
        return JobFilter(
            keywords=tuple(keywords),
            location=self.location,
            remote_only=self.remote_only,
            easy_apply_only=self.easy_apply_only,
        )

    def with_location(self, location: str) -> "JobFilter":
        """Create new filter with updated location."""
        return JobFilter(
            keywords=self.keywords,
            location=location,
            remote_only=self.remote_only,
            easy_apply_only=self.easy_apply_only,
        )
