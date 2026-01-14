"""
Crypto Service - Credential encryption using Fernet.

Provides symmetric encryption for storing LinkedIn credentials locally.
Implements FE-02 requirement for encrypted credential storage.
"""

from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from src.domain.value_objects import Credentials


class CryptoService:
    """
    Cryptographic service for credential encryption.
    
    Uses Fernet symmetric encryption from the cryptography library.
    The encryption key is stored locally in a separate file.
    """
    
    def __init__(self, key_path: Path) -> None:
        """
        Initialize the crypto service.
        
        Args:
            key_path: Path to store/load the encryption key.
        """
        self.key_path = key_path
        self._fernet: Optional[Fernet] = None

    def initialize(self) -> None:
        """Initialize or load the encryption key."""
        if self.key_path.exists():
            key = self.key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            self.key_path.write_bytes(key)
            # Restrict file permissions (Unix only)
            try:
                self.key_path.chmod(0o600)
            except OSError:
                pass  # Windows doesn't support chmod
                
        self._fernet = Fernet(key)

    @property
    def fernet(self) -> Fernet:
        """Get the Fernet instance."""
        if not self._fernet:
            raise RuntimeError("CryptoService not initialized. Call initialize() first.")
        return self._fernet

    def encrypt(self, data: str) -> str:
        """
        Encrypt a string.
        
        Args:
            data: Plain text to encrypt.
            
        Returns:
            Base64-encoded encrypted string.
        """
        encrypted = self.fernet.encrypt(data.encode("utf-8"))
        return encrypted.decode("utf-8")

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt a string.
        
        Args:
            encrypted_data: Base64-encoded encrypted string.
            
        Returns:
            Decrypted plain text.
            
        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data).
        """
        decrypted = self.fernet.decrypt(encrypted_data.encode("utf-8"))
        return decrypted.decode("utf-8")

    def try_decrypt(self, encrypted_data: str) -> Optional[str]:
        """
        Try to decrypt a string, returning None on failure.
        
        Args:
            encrypted_data: Base64-encoded encrypted string.
            
        Returns:
            Decrypted plain text or None if decryption fails.
        """
        try:
            return self.decrypt(encrypted_data)
        except (InvalidToken, Exception):
            return None

    def encrypt_credentials(self, credentials: Credentials) -> Credentials:
        """
        Encrypt credentials password.
        
        Args:
            credentials: Credentials with plain text password.
            
        Returns:
            New Credentials with encrypted password.
        """
        if credentials.is_encrypted:
            return credentials
            
        encrypted_password = self.encrypt(credentials.password)
        return credentials.with_encrypted_password(encrypted_password)

    def decrypt_credentials(self, credentials: Credentials) -> Credentials:
        """
        Decrypt credentials password.
        
        Args:
            credentials: Credentials with encrypted password.
            
        Returns:
            New Credentials with decrypted password.
            
        Raises:
            InvalidToken: If decryption fails.
        """
        if not credentials.is_encrypted:
            return credentials
            
        decrypted_password = self.decrypt(credentials.password)
        return credentials.with_decrypted_password(decrypted_password)

    def try_decrypt_credentials(self, credentials: Credentials) -> Optional[Credentials]:
        """
        Try to decrypt credentials, returning None on failure.
        
        Args:
            credentials: Credentials with encrypted password.
            
        Returns:
            New Credentials with decrypted password or None if decryption fails.
        """
        try:
            return self.decrypt_credentials(credentials)
        except (InvalidToken, Exception):
            return None
