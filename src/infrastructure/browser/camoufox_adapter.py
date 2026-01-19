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
from typing import Any, Optional, List, Dict, Callable

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
        """Start browser with persistent profile.
        
        Uses a separate Chromium instance with a persistent profile.
        The user's login session is saved between runs.
        Opens in a separate window - doesn't interfere with user's browser.
        """
        self._playwright = await async_playwright().start()
        
        # Use persistent profile directory
        profile_dir = Path("data/browser_profile")
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        # Launch Chromium with persistent context (keeps login!)
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=self.settings.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
            viewport={"width": 1366, "height": 768},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )
        
        # Get or create page
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()
            
        self._human = HumanSimulator(self._page)
        
        # Apply stealth patches
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
            await self._context.close()
            
        if self._playwright:
            await self._playwright.stop()
        
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
        self._human = None

    async def check_linkedin_logged_in(self, navigate: bool = True) -> bool:
        """Check if user is logged in to LinkedIn.
        
        Args:
            navigate: If True, navigate to LinkedIn first. Set to False when
                     user is in the middle of logging in to avoid refresh.
        
        Returns:
            True if logged in, False otherwise.
        """
        if not self._page:
            return False
        
        # Only navigate on first check, not during login wait
        if navigate:
            try:
                await self._page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(2)
            except Exception:
                pass
        
        # Check current URL
        current_url = self._page.url
        
        # If on login page, not logged in
        if "/login" in current_url or "/authwall" in current_url or "/uas/" in current_url or "/checkpoint" in current_url:
            return False
        
        # If on feed, we're logged in
        if "/feed" in current_url:
            return True
        
        # Check for logged-in indicators (without navigating)
        try:
            logged_in_selectors = [
                ".global-nav__me",  # Profile menu in nav
                ".search-global-typeahead",  # Search bar
                ".feed-shared-update-v2",  # Feed posts
            ]
            
            for selector in logged_in_selectors:
                element = await self._page.query_selector(selector)
                if element:
                    return True
                    
            return False
            
        except Exception:
            return False
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

    async def get_job_listings(self) -> List[Dict[str, Any]]:
        """
        Get all job listings from the current search results page.
        
        Returns:
            List of job dictionaries with title, company, url, and applied status.
        """
        jobs = []
        
        try:
            # Wait for job list to load - try multiple selectors
            job_list_selectors = [
                '.jobs-search-results-list',
                '.scaffold-layout__list-container',
                '[data-results-list]',
                'ul.scaffold-layout__list-container',
            ]
            
            list_found = False
            for selector in job_list_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    list_found = True
                    break
                except:
                    continue
            
            if not list_found:
                # Try waiting for any job card
                await asyncio.sleep(3)
            
            await asyncio.sleep(2)
            
            # Try multiple selectors for job cards
            job_card_selectors = [
                'li.jobs-search-results__list-item',
                'li.scaffold-layout__list-item',
                '[data-occludable-job-id]',
                '.job-card-container',
                'div[data-job-id]',
                'li[data-occludable-entity-urn]',
            ]
            
            job_cards = []
            for selector in job_card_selectors:
                job_cards = await self.page.query_selector_all(selector)
                if job_cards:
                    break
            
            if not job_cards:
                # Last resort: find all links to job views
                all_job_links = await self.page.query_selector_all('a[href*="/jobs/view/"]')
                for link in all_job_links:
                    try:
                        href = await link.get_attribute('href')
                        if href:
                            job_url = f"https://www.linkedin.com{href}" if href.startswith('/') else href
                            job_id = job_url.split('/view/')[1].split('/')[0].split('?')[0] if '/view/' in job_url else ""
                            
                            # Get text from link
                            text = await link.inner_text()
                            
                            jobs.append({
                                'id': job_id,
                                'title': text.strip()[:50] if text else "Vaga",
                                'company': "LinkedIn",
                                'url': job_url,
                                'already_applied': False,
                            })
                    except:
                        continue
                return jobs
            
            for card in job_cards:
                try:
                    # Get job ID from card attributes
                    job_id = ""
                    for attr in ['data-occludable-job-id', 'data-job-id']:
                        job_id = await card.get_attribute(attr)
                        if job_id:
                            break
                    
                    if not job_id:
                        # Try to get from URN
                        urn = await card.get_attribute('data-occludable-entity-urn')
                        if urn and 'jobPosting:' in urn:
                            job_id = urn.split('jobPosting:')[1]
                    
                    # Get job link
                    link_element = await card.query_selector('a[href*="/jobs/view/"]')
                    job_url = ""
                    if link_element:
                        href = await link_element.get_attribute('href')
                        if href:
                            job_url = f"https://www.linkedin.com{href}" if href.startswith('/') else href
                            if not job_id and '/view/' in job_url:
                                job_id = job_url.split('/view/')[1].split('/')[0].split('?')[0]
                    elif job_id:
                        job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
                    
                    # Get job title - try multiple selectors
                    title_selectors = [
                        '.job-card-list__title',
                        '.job-card-container__link strong',
                        'a[href*="/jobs/view/"] strong',
                        '.artdeco-entity-lockup__title',
                        'strong',
                    ]
                    job_title = "Sem título"
                    for sel in title_selectors:
                        title_el = await card.query_selector(sel)
                        if title_el:
                            job_title = await title_el.inner_text()
                            if job_title and job_title.strip():
                                break
                    
                    # Get company name - try multiple selectors
                    company_selectors = [
                        '.job-card-container__primary-description',
                        '.job-card-container__company-name',
                        '.artdeco-entity-lockup__subtitle',
                        '.job-card-container__subtitle span',
                    ]
                    company_name = "Empresa"
                    for sel in company_selectors:
                        company_el = await card.query_selector(sel)
                        if company_el:
                            company_name = await company_el.inner_text()
                            if company_name and company_name.strip():
                                break
                    
                    # Check if already applied
                    already_applied = False
                    card_text = await card.inner_text()
                    if card_text:
                        card_text_lower = card_text.lower()
                        if 'applied' in card_text_lower or 'candidatura enviada' in card_text_lower or 'candidatou' in card_text_lower:
                            already_applied = True
                    
                    if job_id or job_url:
                        jobs.append({
                            'id': job_id,
                            'title': job_title.strip(),
                            'company': company_name.strip().split('\n')[0],  # Get first line only
                            'url': job_url,
                            'already_applied': already_applied,
                        })
                    
                except Exception as e:
                    continue  # Skip problematic cards
                    
        except Exception as e:
            print(f"Error getting job listings: {e}")
        
        return jobs

    async def click_job_card(self, job: Dict[str, Any]) -> bool:
        """
        Click on a job card to open the job details.
        
        Args:
            job: Job dictionary with url or id.
            
        Returns:
            True if successfully clicked and loaded.
        """
        try:
            # Try multiple ways to find and click the job card
            if job.get('id'):
                # Try different selectors for job card
                card_selectors = [
                    f'[data-occludable-job-id="{job["id"]}"]',
                    f'[data-job-id="{job["id"]}"]',
                    f'li[data-occludable-entity-urn*="{job["id"]}"]',
                ]
                
                for selector in card_selectors:
                    card = await self.page.query_selector(selector)
                    if card:
                        # Click the link inside the card
                        link = await card.query_selector('a[href*="/jobs/view/"]')
                        if link:
                            await self.human.click_element(link)
                        else:
                            await self.human.click_element(card)
                        await asyncio.sleep(2)
                        return True
            
            # Fallback: navigate directly to job URL
            if job.get('url'):
                await self.page.goto(job['url'], wait_until="domcontentloaded")
                await asyncio.sleep(2)
                return True
                
            return False
            
        except Exception as e:
            print(f"Error clicking job card: {e}")
            return False

    async def apply_to_job(self, log_callback: Callable[[str, str], None] = None) -> Dict[str, Any]:
        """
        Apply to the currently selected job using Easy Apply.
        
        Args:
            log_callback: Optional function to log messages (message, level).
            
        Returns:
            Dictionary with success status and details.
        """
        def log(msg: str, level: str = "info"):
            if log_callback:
                log_callback(msg, level)
        
        result = {
            'success': False,
            'message': '',
            'job_title': '',
            'company': '',
        }
        
        try:
            # Get job title and company from detail view
            title_selectors = [
                '.job-details-jobs-unified-top-card__job-title',
                'h1.t-24',
                '.jobs-unified-top-card__job-title',
                'h1[class*="job-title"]',
            ]
            for sel in title_selectors:
                title_el = await self.page.query_selector(sel)
                if title_el:
                    result['job_title'] = await title_el.inner_text()
                    break
            if not result['job_title']:
                result['job_title'] = "Desconhecido"
            
            company_selectors = [
                '.job-details-jobs-unified-top-card__company-name',
                '.jobs-unified-top-card__company-name',
                '.job-details-jobs-unified-top-card__primary-description a',
            ]
            for sel in company_selectors:
                company_el = await self.page.query_selector(sel)
                if company_el:
                    result['company'] = await company_el.inner_text()
                    break
            if not result['company']:
                result['company'] = "Desconhecida"
            
            # Check if already applied
            page_text = await self.page.inner_text('body')
            if 'Candidatura enviada' in page_text or 'Applied' in page_text:
                # Check if it's about this job specifically
                applied_indicator = await self.page.query_selector('.jobs-apply-button--top-card[disabled]')
                if applied_indicator:
                    result['message'] = 'Já candidatado anteriormente'
                    return result
            
            # Find Easy Apply button
            easy_apply_selectors = [
                'button.jobs-apply-button',
                '.jobs-apply-button',
                'button[aria-label*="Apply"]',
                'button[aria-label*="Candidatura"]',
            ]
            
            easy_apply_btn = None
            for sel in easy_apply_selectors:
                easy_apply_btn = await self.page.query_selector(sel)
                if easy_apply_btn:
                    btn_text = await easy_apply_btn.inner_text()
                    if 'easy' in btn_text.lower() or 'candidatura' in btn_text.lower() or 'apply' in btn_text.lower():
                        break
                    easy_apply_btn = None
            
            if not easy_apply_btn:
                result['message'] = 'Botão Easy Apply não encontrado'
                return result
            
            # Check if button is disabled
            is_disabled = await easy_apply_btn.get_attribute('disabled')
            aria_disabled = await easy_apply_btn.get_attribute('aria-disabled')
            if is_disabled or aria_disabled == 'true':
                result['message'] = 'Já candidatado anteriormente'
                return result
            
            # Click Easy Apply
            await self.human.click_element(easy_apply_btn)
            await asyncio.sleep(2)
            
            # Handle the application modal/form
            max_steps = 15
            last_action = ""
            
            for step in range(max_steps):
                await asyncio.sleep(1.5)
                
                # First, check for "Salvar esta candidatura?" modal and dismiss it
                save_modal = await self.page.query_selector('text="Salvar esta candidatura?"')
                if save_modal:
                    discard_btn = await self.page.query_selector('button:has-text("Descartar")')
                    if discard_btn:
                        await discard_btn.click()
                        await asyncio.sleep(1)
                        continue
                
                # Check for success indicators
                success_indicators = [
                    'text="Candidatura enviada"',
                    'text="Application sent"',
                    'text="Sua candidatura foi enviada"',
                    'h2:has-text("Candidatura enviada")',
                ]
                
                for indicator in success_indicators:
                    success_el = await self.page.query_selector(indicator)
                    if success_el:
                        result['success'] = True
                        result['message'] = 'Candidatura enviada com sucesso!'
                        # Close success modal
                        close_btn = await self.page.query_selector('button[aria-label="Dismiss"]')
                        if not close_btn:
                            close_btn = await self.page.query_selector('button[aria-label="Fechar"]')
                        if not close_btn:
                            close_btn = await self.page.query_selector('[data-test-modal-close-btn]')
                        if close_btn:
                            await close_btn.click()
                        return result
                
                # Check for Submit/Send button (final step)
                submit_selectors = [
                    'button[aria-label="Enviar candidatura"]',
                    'button[aria-label="Submit application"]',
                    'button:has-text("Enviar candidatura")',
                    'button:has-text("Submit application")',
                ]
                
                for sel in submit_selectors:
                    submit_btn = await self.page.query_selector(sel)
                    if submit_btn:
                        is_disabled = await submit_btn.get_attribute('disabled')
                        if not is_disabled:
                            await self.human.click_element(submit_btn)
                            await asyncio.sleep(3)
                            result['success'] = True
                            result['message'] = 'Candidatura enviada com sucesso!'
                            # Try to close any success modal
                            await asyncio.sleep(1)
                            close_btn = await self.page.query_selector('button[aria-label="Dismiss"]')
                            if close_btn:
                                await close_btn.click()
                            return result
                
                # Check for Review button
                review_selectors = [
                    'button[aria-label="Revisar sua candidatura"]',
                    'button[aria-label="Review your application"]',
                    'button:has-text("Revisar")',
                    'button:has-text("Review")',
                ]
                
                for sel in review_selectors:
                    review_btn = await self.page.query_selector(sel)
                    if review_btn:
                        is_disabled = await review_btn.get_attribute('disabled')
                        if not is_disabled:
                            await self.human.click_element(review_btn)
                            last_action = "review"
                            await asyncio.sleep(1)
                            break
                else:
                    # Check for Next/Avançar button
                    next_selectors = [
                        'button[aria-label="Avançar"]',
                        'button[aria-label="Continue to next step"]',
                        'button[aria-label="Continuar para a próxima etapa"]',
                        'button:has-text("Avançar")',
                        'button:has-text("Next")',
                        'button:has-text("Continue")',
                    ]
                    
                    clicked_next = False
                    for sel in next_selectors:
                        next_btn = await self.page.query_selector(sel)
                        if next_btn:
                            is_disabled = await next_btn.get_attribute('disabled')
                            if not is_disabled:
                                await self.human.click_element(next_btn)
                                last_action = "next"
                                clicked_next = True
                                await asyncio.sleep(1)
                                break
                    
                    if not clicked_next and step > 5:
                        # Check for any primary button in the modal
                        primary_btn = await self.page.query_selector('.artdeco-modal button.artdeco-button--primary')
                        if primary_btn:
                            btn_text = await primary_btn.inner_text()
                            is_disabled = await primary_btn.get_attribute('disabled')
                            if not is_disabled and 'descartar' not in btn_text.lower():
                                await self.human.click_element(primary_btn)
                                last_action = f"primary: {btn_text}"
                                await asyncio.sleep(1)
                        elif step > 10:
                            # Stuck, try to close
                            result['message'] = 'Formulário requer informações adicionais'
                            close_btn = await self.page.query_selector('button[aria-label="Dismiss"]')
                            if not close_btn:
                                close_btn = await self.page.query_selector('.artdeco-modal__dismiss')
                            if close_btn:
                                await close_btn.click()
                            return result
            
            if not result['success'] and not result['message']:
                result['message'] = 'Timeout - formulário complexo'
                # Try to close modal
                close_btn = await self.page.query_selector('button[aria-label="Dismiss"]')
                if close_btn:
                    await close_btn.click()
                
        except Exception as e:
            result['message'] = f'Erro: {str(e)}'
            # Try to close any modal
            try:
                close_btn = await self.page.query_selector('button[aria-label="Dismiss"]')
                if close_btn:
                    await close_btn.click()
            except:
                pass
        
        return result

    async def scroll_job_list(self) -> None:
        """Scroll the job list to load more jobs."""
        try:
            job_list = await self.page.query_selector('.jobs-search-results-list')
            if job_list:
                await job_list.evaluate('el => el.scrollBy(0, 500)')
                await asyncio.sleep(1)
        except Exception:
            pass

    async def go_to_next_page(self) -> bool:
        """
        Go to the next page of job results.
        
        Returns:
            True if successfully navigated to next page.
        """
        try:
            # Find pagination
            next_btn = await self.page.query_selector('button[aria-label="Page 2"]')
            if not next_btn:
                # Try to find the next arrow
                next_btn = await self.page.query_selector('.artdeco-pagination__button--next')
            
            if next_btn:
                is_disabled = await next_btn.get_attribute('disabled')
                if not is_disabled:
                    await self.human.click_element(next_btn)
                    await asyncio.sleep(2)
                    return True
            
            return False
            
        except Exception:
            return False
