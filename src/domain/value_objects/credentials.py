"""
Credentials Value Object - Immutable encrypted credentials.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Credentials:
    """
    Immutable value object for LinkedIn credentials.
    
    Credentials are stored encrypted; this object holds either
    encrypted or decrypted values depending on context.
    
    Attributes:
        username: LinkedIn email/username
        password: LinkedIn password
        is_encrypted: Whether the password is currently encrypted
    """
    
    username: str
    password: str
    is_encrypted: bool = False

    def __post_init__(self) -> None:
        """Validate credentials."""
        if not self.username:
            raise ValueError("Username is required")
        if not self.password:
            raise ValueError("Password is required")

    @property
    def is_valid(self) -> bool:
        """Check if credentials appear valid (non-empty)."""
        return bool(self.username and self.password)

    def masked(self) -> "Credentials":
        """Return credentials with masked password for display."""
        masked_pw = "*" * min(len(self.password), 8) if self.password else ""
        return Credentials(
            username=self.username,
            password=masked_pw,
            is_encrypted=self.is_encrypted,
        )

    def with_encrypted_password(self, encrypted: str) -> "Credentials":
        """Create new credentials with encrypted password."""
        return Credentials(
            username=self.username,
            password=encrypted,
            is_encrypted=True,
        )

    def with_decrypted_password(self, decrypted: str) -> "Credentials":
        """Create new credentials with decrypted password."""
        return Credentials(
            username=self.username,
            password=decrypted,
            is_encrypted=False,
        )
