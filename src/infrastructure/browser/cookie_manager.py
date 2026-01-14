"""
Cookie Manager - Session persistence for LinkedIn.

Implements BE-01: Cookie management with auth.json.
Saves and loads browser cookies to avoid repeated logins.
"""

import json
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import BrowserContext


class CookieManager:
    """
    Manages browser session cookies for LinkedIn.
    
    Persists cookies to auth.json after successful login,
    and restores them on subsequent runs to avoid re-authentication.
    """
    
    def __init__(self, auth_file_path: Path) -> None:
        """
        Initialize cookie manager.
        
        Args:
            auth_file_path: Path to the auth.json file for cookie storage.
        """
        self.auth_file_path = auth_file_path

    def has_saved_session(self) -> bool:
        """Check if there's a saved session available."""
        return self.auth_file_path.exists()

    async def save_cookies(self, context: BrowserContext) -> None:
        """
        Save current browser cookies to file.
        
        Args:
            context: Playwright browser context.
        """
        cookies = await context.cookies()
        storage_state = await context.storage_state()
        
        data = {
            "cookies": cookies,
            "storage_state": storage_state,
        }
        
        self.auth_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.auth_file_path.write_text(json.dumps(data, indent=2))
        
        # Restrict permissions
        try:
            self.auth_file_path.chmod(0o600)
        except OSError:
            pass

    async def load_cookies(self, context: BrowserContext) -> bool:
        """
        Load saved cookies into browser context.
        
        Args:
            context: Playwright browser context.
            
        Returns:
            True if cookies were loaded successfully.
        """
        if not self.has_saved_session():
            return False
            
        try:
            data = json.loads(self.auth_file_path.read_text())
            cookies = data.get("cookies", [])
            
            if cookies:
                await context.add_cookies(cookies)
                return True
                
        except (json.JSONDecodeError, KeyError, OSError):
            return False
            
        return False

    def get_storage_state_path(self) -> Optional[str]:
        """
        Get path to storage state file if it exists.
        
        Returns:
            Absolute path to auth file or None.
        """
        if self.has_saved_session():
            return str(self.auth_file_path.absolute())
        return None

    def clear_session(self) -> None:
        """Delete saved session cookies."""
        if self.auth_file_path.exists():
            self.auth_file_path.unlink()

    def get_session_info(self) -> dict[str, Any]:
        """
        Get information about the saved session.
        
        Returns:
            Dictionary with session metadata.
        """
        if not self.has_saved_session():
            return {
                "exists": False,
                "path": str(self.auth_file_path),
            }
            
        try:
            data = json.loads(self.auth_file_path.read_text())
            cookies = data.get("cookies", [])
            
            # Find LinkedIn session cookies
            linkedin_cookies = [
                c for c in cookies
                if "linkedin" in c.get("domain", "").lower()
            ]
            
            return {
                "exists": True,
                "path": str(self.auth_file_path),
                "cookie_count": len(cookies),
                "linkedin_cookies": len(linkedin_cookies),
                "has_li_at": any(
                    c.get("name") == "li_at" for c in linkedin_cookies
                ),
            }
            
        except (json.JSONDecodeError, OSError):
            return {
                "exists": True,
                "path": str(self.auth_file_path),
                "error": "Failed to read session file",
            }
