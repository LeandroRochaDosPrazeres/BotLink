"""
AI Port - Abstract interface for AI operations.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.infrastructure.ai.prompt_builder import PromptResult


class AIPort(ABC):
    """Abstract interface for AI operations."""
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the AI service."""
        pass
    
    @abstractmethod
    async def answer_text_question(
        self,
        prompt: PromptResult,
    ) -> tuple[str, int]:
        """Answer a text question. Returns (answer, tokens_used)."""
        pass
    
    @abstractmethod
    async def get_selected_option(
        self,
        prompt: PromptResult,
        options: list[str],
    ) -> tuple[str, int]:
        """Select an option. Returns (selected_option, tokens_used)."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if AI service is available."""
        pass
