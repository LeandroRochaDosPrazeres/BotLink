"""
Browser Port - Abstract interface for browser operations.

Following Clean Architecture, this defines the contract that
any browser adapter must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BrowserPort(ABC):
    """Abstract interface for browser automation."""
    
    @abstractmethod
    async def start(self) -> None:
        """Start the browser."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the browser."""
        pass
    
    @abstractmethod
    async def is_logged_in(self) -> bool:
        """Check if logged into LinkedIn."""
        pass
    
    @abstractmethod
    async def login(self, username: str, password: str) -> bool:
        """Log into LinkedIn."""
        pass
    
    @abstractmethod
    async def navigate(self, url: str) -> None:
        """Navigate to a URL."""
        pass
    
    @abstractmethod
    async def search_jobs(
        self,
        keywords: list[str],
        location: str = "",
        remote_only: bool = False,
    ) -> str:
        """Search for jobs and return the results URL."""
        pass
    
    @abstractmethod
    async def upload_file_invisible(
        self,
        file_path: Path,
        input_selector: str = 'input[type="file"]',
    ) -> bool:
        """Upload a file without dialog."""
        pass
    
    @abstractmethod
    async def take_screenshot(self, path: Path) -> None:
        """Take a screenshot."""
        pass
    
    @abstractmethod
    async def get_page_content(self) -> str:
        """Get current page HTML."""
        pass
