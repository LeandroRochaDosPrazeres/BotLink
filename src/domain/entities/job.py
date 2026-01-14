"""
Job Entity - Represents a LinkedIn job posting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Job:
    """
    Job entity representing a LinkedIn job posting.
    
    Attributes:
        job_id: Unique LinkedIn job ID (e.g., "37481923")
        title: Job title
        company: Company name
        location: Job location
        description: Full job description text
        url: LinkedIn job URL
        is_remote: Whether the job is remote
        is_easy_apply: Whether the job supports Easy Apply
        questions: List of application questions extracted from the form
        scraped_at: When the job was scraped
    """
    
    job_id: str
    title: str
    company: str
    location: str
    description: str = ""
    url: str = ""
    is_remote: bool = False
    is_easy_apply: bool = True
    questions: list[dict] = field(default_factory=list)
    scraped_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate job data after initialization."""
        if not self.job_id:
            raise ValueError("job_id is required")
        if not self.title:
            raise ValueError("title is required")
        if not self.company:
            raise ValueError("company is required")

    @property
    def display_name(self) -> str:
        """Human-readable job display name."""
        return f"{self.title} @ {self.company}"

    def matches_filter(
        self,
        keywords: Optional[list[str]] = None,
        location: Optional[str] = None,
        remote_only: bool = False,
    ) -> bool:
        """
        Check if job matches the given filters.
        
        Args:
            keywords: List of keywords to match against title/description
            location: Location to match
            remote_only: Only match remote jobs
            
        Returns:
            True if job matches all provided filters
        """
        if remote_only and not self.is_remote:
            return False
            
        if location and location.lower() not in self.location.lower():
            return False
            
        if keywords:
            text = f"{self.title} {self.description}".lower()
            if not any(kw.lower() in text for kw in keywords):
                return False
                
        return True
