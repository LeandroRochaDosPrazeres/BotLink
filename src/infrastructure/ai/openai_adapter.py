"""
OpenAI Adapter - GPT-4o integration with JSON mode.

Implements BE-06: Force AI responses in JSON format for form filling.
"""

import json
from dataclasses import dataclass
from typing import Any, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel

from src.config.settings import Settings
from .prompt_builder import PromptResult


@dataclass
class AIResponse:
    """Response from the AI."""
    content: str
    json_data: Optional[dict] = None
    tokens_used: int = 0
    model: str = ""


class OpenAIAdapter:
    """
    OpenAI API adapter for GPT-4o.
    
    Features:
    - Structured outputs (JSON mode)
    - Token tracking for cost control
    - Async API calls
    """
    
    DEFAULT_MODEL = "gpt-4o"
    MAX_TOKENS = 1000

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the adapter.
        
        Args:
            settings: Application settings with API key.
        """
        self.settings = settings
        self._client: Optional[AsyncOpenAI] = None

    def initialize(self) -> None:
        """Initialize the OpenAI client."""
        if not self.settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
            
        self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    @property
    def client(self) -> AsyncOpenAI:
        """Get the OpenAI client."""
        if not self._client:
            raise RuntimeError("OpenAI adapter not initialized. Call initialize() first.")
        return self._client

    async def complete(
        self,
        prompt: PromptResult | str,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> AIResponse | str:
        """
        Send a completion request to GPT-4o.
        
        Args:
            prompt: The prompt to send (PromptResult or plain string).
            json_mode: Whether to force JSON output.
            max_tokens: Maximum response tokens.
            
        Returns:
            AIResponse with content and token usage, or string if prompt was string.
        """
        # Handle string prompts (simple mode)
        if isinstance(prompt, str):
            try:
                if not self._client:
                    self.initialize()
                
                response = await self.client.chat.completions.create(
                    model=self.DEFAULT_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant for job applications. Be concise and professional."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=max_tokens or 100,
                    temperature=0.7,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                print(f"OpenAI error: {e}")
                return ""
        
        # Handle PromptResult prompts (structured mode)
        messages = [
            {"role": "system", "content": prompt.system_prompt},
            {"role": "user", "content": prompt.user_prompt},
        ]
        
        kwargs: dict[str, Any] = {
            "model": self.DEFAULT_MODEL,
            "messages": messages,
            "max_tokens": max_tokens or self.MAX_TOKENS,
            "temperature": 0.7,
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = await self.client.chat.completions.create(**kwargs)
        
        content = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else 0
        
        # Try to parse JSON if in json_mode
        json_data = None
        if json_mode:
            try:
                json_data = json.loads(content)
            except json.JSONDecodeError:
                pass
        
        return AIResponse(
            content=content,
            json_data=json_data,
            tokens_used=tokens_used,
            model=self.DEFAULT_MODEL,
        )

    async def answer_text_question(
        self,
        prompt: PromptResult,
    ) -> AIResponse:
        """Answer a text question (free-form response)."""
        return await self.complete(prompt, json_mode=False)

    async def answer_select_question(
        self,
        prompt: PromptResult,
    ) -> AIResponse:
        """Answer a select/radio question (JSON response with selected option)."""
        return await self.complete(prompt, json_mode=True)

    async def get_selected_option(
        self,
        prompt: PromptResult,
        options: list[str],
    ) -> tuple[str, int]:
        """
        Get the selected option from a list.
        
        Args:
            prompt: The prompt to send.
            options: Available options.
            
        Returns:
            Tuple of (selected_option, tokens_used).
        """
        response = await self.answer_select_question(prompt)
        
        if response.json_data and "selected_option" in response.json_data:
            selected = response.json_data["selected_option"]
            # Find closest match in options
            for opt in options:
                if opt.lower() == selected.lower():
                    return opt, response.tokens_used
            # Return first close match
            for opt in options:
                if selected.lower() in opt.lower() or opt.lower() in selected.lower():
                    return opt, response.tokens_used
        
        # Default to first option if parsing fails
        return options[0] if options else "", response.tokens_used

    async def health_check(self) -> bool:
        """Check if the API is accessible."""
        try:
            response = await self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
            )
            return bool(response.choices)
        except Exception:
            return False


class StructuredAnswerSchema(BaseModel):
    """Schema for structured answer responses."""
    selected_option: str


class CoverLetterSchema(BaseModel):
    """Schema for cover letter generation."""
    content: str
    key_points: list[str]
