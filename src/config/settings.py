"""
BOTLink Configuration Module

Environment-based configuration with fail-fast validation (GLOBAL_RULES §1.1).
All settings are loaded from environment variables with sensible defaults.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_prefix="BOTLINK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    env: Literal["development", "production"] = Field(
        default="development",
        description="Application environment",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )
    data_dir: Path = Field(
        default=Path("./data"),
        description="Directory for runtime data (db, cookies, etc.)",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(
        default="",
        alias="OPENAI_API_KEY",
        description="OpenAI API key for GPT-4o",
    )

    # OpSec Limits (RNF-01 to RNF-05)
    daily_limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum applications per day (RNF-01)",
    )
    warmup_enabled: bool = Field(
        default=True,
        description="Enable warm-up progression for new accounts (RNF-02)",
    )
    min_action_delay: float = Field(
        default=1.5,
        description="Minimum delay between actions in seconds (RNF-03)",
    )
    max_action_delay: float = Field(
        default=4.0,
        description="Maximum delay between actions in seconds (RNF-03)",
    )
    min_application_delay: float = Field(
        default=120.0,
        description="Minimum delay between applications in seconds (RNF-03)",
    )
    max_application_delay: float = Field(
        default=600.0,
        description="Maximum delay between applications in seconds (RNF-03)",
    )
    pause_after_applications: int = Field(
        default=10,
        description="Pause after this many applications (RNF-04)",
    )
    pause_duration_min: int = Field(
        default=15,
        description="Minimum pause duration in minutes (RNF-04)",
    )
    pause_duration_max: int = Field(
        default=30,
        description="Maximum pause duration in minutes (RNF-04)",
    )
    max_consecutive_errors: int = Field(
        default=3,
        description="Abort after this many consecutive errors (RNF-05)",
    )

    # Browser Settings
    headless: bool = Field(
        default=False,
        description="Run browser in headless mode",
    )
    use_camoufox: bool = Field(
        default=True,
        description="Use Camoufox for stealth browsing",
    )

    @field_validator("data_dir", mode="before")
    @classmethod
    def ensure_path(cls, v: str | Path) -> Path:
        """Convert string to Path."""
        return Path(v)

    def ensure_data_dir(self) -> None:
        """Create data directory if it doesn't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def database_path(self) -> Path:
        """Path to SQLite database."""
        return self.data_dir / "botlink.db"

    @property
    def auth_file_path(self) -> Path:
        """Path to authentication cookies file."""
        return self.data_dir / "auth.json"

    @property
    def encryption_key_path(self) -> Path:
        """Path to encryption key file."""
        return self.data_dir / ".key"


def get_settings() -> Settings:
    """
    Get validated settings instance.
    
    Raises:
        ValidationError: If required settings are missing or invalid.
    """
    settings = Settings()
    settings.ensure_data_dir()
    return settings


# Singleton instance for easy import
settings = get_settings()
