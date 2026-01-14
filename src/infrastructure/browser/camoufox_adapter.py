"""
Camoufox Adapter - Stealth browser automation with Playwright.

Primary browser adapter implementing:
- BE-01: Cookie management (via CookieManager)
- BE-02: Human simulation (via HumanSimulator)
- BE-03: Invisible file upload

Uses Camoufox (Firefox fork) for fingerprint evasion when available,
with fallback to regular Firefox.
"""

import asyncio
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from src.config.settings import Settings
from .cookie_manager import CookieManager
from .human_simulator import HumanSimulator


class CamoufoxAdapter:
    """
    Stealth browser adapter using Playwright with Camoufox.
    
    Provides high-level browser automation with anti-detection features.
    """
    
    # LinkedIn URLs
    LINKEDIN_BASE = "https://www.linkedin.com"
    LINKEDIN_LOGIN = "https://www.linkedin.com/login"
    LINKEDIN_JOBS = "https://www.linkedin.com/jobs"
    LINKEDIN_FEED = "https://www.linkedin.com/feed"
    
    # Selectors
    SELECTOR_LOGIN_EMAIL = 'input[name="session_key"]'
    SELECTOR_LOGIN_PASSWORD = 'input[name="session_password"]'
    SELECTOR_LOGIN_BUTTON = 'button[type="submit"]'
    SELECTOR_EASY_APPLY_BUTTON = 'button.jobs-apply-button'
    SELECTOR_SUBMIT_BUTTON = 'button[aria-label="Submit application"]'
    SELECTOR_NEXT_BUTTON = 'button[aria-label="Continue to next step"]'
    SELECTOR_REVIEW_BUTTON = 'button[aria-label="Review your application"]'

    def __init__(
        self,
        settings: Settings,
        cookie_manager: CookieManager,
    ) -> None:
        """
        Initialize the adapter.
        
        Args:
            settings: Application settings.
            cookie_manager: Cookie manager for session persistence.
        """
        self.settings = settings
        self.cookie_manager = cookie_manager
        
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._human: Optional[HumanSimulator] = None

    async def start(self) -> None:
        """Start the browser and create a new context."""
        self._playwright = await async_playwright().start()
        
        # Try Camoufox first, fallback to Firefox
        browser_type = self._playwright.firefox
        
        launch_options: dict[str, Any] = {
            "headless": self.settings.headless,
        }
        
        # Add Camoufox-specific options if available
        if self.settings.use_camoufox:
            launch_options["args"] = [
                "--disable-blink-features=AutomationControlled",
            ]
        
        self._browser = await browser_type.launch(**launch_options)
        
        # Create context with anti-detection settings
        context_options: dict[str, Any] = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
                "Gecko/20100101 Firefox/121.0"
            ),
            "locale": "pt-BR",
            "timezone_id": "America/Sao_Paulo",
        }
        
        # Load existing session if available
        if self.cookie_manager.has_saved_session():
            storage_state = self.cookie_manager.get_storage_state_path()
            if storage_state:
                context_options["storage_state"] = storage_state
        
        self._context = await self._browser.new_context(**context_options)
        self._page = await self._context.new_page()
        self._human = HumanSimulator(self._page)
        
        # Additional stealth measures
        await self._apply_stealth_patches()

    async def _apply_stealth_patches(self) -> None:
        """Apply JavaScript patches to avoid detection."""
        if not self._page:
            return
            
        # Hide webdriver property
        await self._page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override permissions query
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

    async def stop(self) -> None:
        """Stop the browser and clean up resources."""
        if self._context:
            # Save cookies before closing
            await self.cookie_manager.save_cookies(self._context)
            await self._context.close()
            
        if self._browser:
            await self._browser.close()
            
        if self._playwright:
            await self._playwright.stop()
        
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
        self._human = None

    @property
    def page(self) -> Page:
        """Get the current page."""
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    @property
    def human(self) -> HumanSimulator:
        """Get the human simulator."""
        if not self._human:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._human

    async def navigate(self, url: str) -> None:
        """Navigate to a URL with human-like delay."""
        await self.human.wait_human(0.5, 1.5)
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.human.random_scroll()

    async def is_logged_in(self) -> bool:
        """Check if currently logged into LinkedIn."""
        try:
            await self.page.goto(self.LINKEDIN_FEED, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            # Check for login page redirect
            current_url = self.page.url
            if "login" in current_url or "authwall" in current_url:
                return False
                
            # Check for feed elements
            feed_element = await self.page.query_selector('div[data-view-name="feed-root"]')
            return feed_element is not None
            
        except Exception:
            return False

    async def login(self, username: str, password: str) -> bool:
        """
        Log into LinkedIn with credentials.
        
        Args:
            username: LinkedIn email.
            password: LinkedIn password.
            
        Returns:
            True if login was successful.
        """
        try:
            await self.navigate(self.LINKEDIN_LOGIN)
            await asyncio.sleep(2)
            
            # Find and fill email
            email_input = await self.page.wait_for_selector(
                self.SELECTOR_LOGIN_EMAIL,
                timeout=10000,
            )
            if email_input:
                await self.human.click_element(email_input)
                await self.human.type_text(username)
            
            await self.human.wait_human(0.5, 1.0)
            
            # Find and fill password
            password_input = await self.page.wait_for_selector(
                self.SELECTOR_LOGIN_PASSWORD,
            )
            if password_input:
                await self.human.click_element(password_input)
                await self.human.type_text(password)
            
            await self.human.wait_human(0.5, 1.0)
            
            # Click login button
            login_button = await self.page.wait_for_selector(
                self.SELECTOR_LOGIN_BUTTON,
            )
            if login_button:
                await self.human.click_element(login_button)
            
            # Wait for navigation
            await asyncio.sleep(5)
            
            # Verify login
            is_logged = await self.is_logged_in()
            
            if is_logged and self._context:
                await self.cookie_manager.save_cookies(self._context)
                
            return is_logged
            
        except Exception as e:
            print(f"Login failed: {e}")
            return False

    async def search_jobs(
        self,
        keywords: list[str],
        location: str = "",
        remote_only: bool = False,
    ) -> str:
        """
        Navigate to LinkedIn job search with filters.
        
        Args:
            keywords: Search keywords.
            location: Location filter.
            remote_only: Only remote jobs.
            
        Returns:
            URL of the search results page.
        """
        search_query = " ".join(keywords)
        url = f"{self.LINKEDIN_JOBS}/search/?keywords={search_query}"
        
        if location:
            url += f"&location={location}"
        if remote_only:
            url += "&f_WRA=1"  # LinkedIn remote filter
        
        # Easy Apply filter
        url += "&f_AL=true"
        
        await self.navigate(url)
        return url

    async def upload_file_invisible(
        self,
        file_path: Path,
        input_selector: str = 'input[type="file"]',
    ) -> bool:
        """
        Upload file without opening file dialog (BE-03).
        
        Args:
            file_path: Path to the file to upload.
            input_selector: CSS selector for the file input.
            
        Returns:
            True if upload was successful.
        """
        try:
            # Find the file input (may be hidden)
            file_input = await self.page.query_selector(input_selector)
            
            if file_input:
                await file_input.set_input_files(str(file_path))
                return True
            
            # Try to find any file input
            file_inputs = await self.page.query_selector_all('input[type="file"]')
            if file_inputs:
                await file_inputs[0].set_input_files(str(file_path))
                return True
                
            return False
            
        except Exception:
            return False

    async def take_screenshot(self, path: Path) -> None:
        """Take a screenshot for debugging."""
        await self.page.screenshot(path=str(path))

    async def get_page_content(self) -> str:
        """Get the current page HTML content."""
        return await self.page.content()
