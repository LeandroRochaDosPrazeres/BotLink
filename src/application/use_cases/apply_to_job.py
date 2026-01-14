"""
Apply to Job Use Case - Full job application workflow.

Handles the complete Easy Apply flow including:
- Opening job listing
- Parsing form fields
- Getting AI answers
- Filling and submitting the form
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.domain.entities import Job, Candidate, Application, ApplicationStatus
from src.infrastructure.browser import CamoufoxAdapter
from src.infrastructure.ai import OpenAIAdapter, PromptBuilder
from src.infrastructure.parsers import JobParser


logger = logging.getLogger(__name__)


class ApplicationResult(Enum):
    """Result of an application attempt."""
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"
    ALREADY_APPLIED = "already_applied"


@dataclass
class ApplyResult:
    """Detailed result of application attempt."""
    result: ApplicationResult
    job: Optional[Job] = None
    message: str = ""
    tokens_used: int = 0


class ApplyToJobUseCase:
    """
    Use case for applying to a single job.
    
    Orchestrates the full Easy Apply flow:
    1. Parse job listing
    2. Click Easy Apply
    3. For each form page:
       a. Parse form fields
       b. Get AI answers for questions
       c. Fill in answers
       d. Click Next/Submit
    4. Confirm submission
    """
    
    # Selectors
    EASY_APPLY_BUTTON = 'button.jobs-apply-button'
    NEXT_BUTTON = 'button[aria-label="Continue to next step"]'
    REVIEW_BUTTON = 'button[aria-label="Review your application"]'
    SUBMIT_BUTTON = 'button[aria-label="Submit application"]'
    CLOSE_BUTTON = 'button[aria-label="Dismiss"]'
    
    MAX_FORM_PAGES = 10  # Safety limit

    def __init__(
        self,
        browser: CamoufoxAdapter,
        ai: OpenAIAdapter,
        candidate: Candidate,
    ) -> None:
        """
        Initialize the use case.
        
        Args:
            browser: Browser adapter.
            ai: AI adapter.
            candidate: Candidate profile for AI context.
        """
        self.browser = browser
        self.ai = ai
        self.candidate = candidate
        self.prompt_builder = PromptBuilder(candidate)
        self.job_parser = JobParser(browser.page)

    async def execute(self, job_url: Optional[str] = None) -> ApplyResult:
        """
        Execute the job application.
        
        Args:
            job_url: URL of the job to apply to (uses current page if None).
            
        Returns:
            ApplyResult with outcome details.
        """
        total_tokens = 0
        
        try:
            # Navigate to job if URL provided
            if job_url:
                await self.browser.navigate(job_url)
                await asyncio.sleep(2)
            
            # Parse job listing
            job = await self.job_parser.parse_job_listing()
            if not job:
                return ApplyResult(
                    result=ApplicationResult.FAILED,
                    message="Não foi possível parsear a vaga",
                )
            
            # Click Easy Apply button
            if not await self._click_easy_apply():
                return ApplyResult(
                    result=ApplicationResult.SKIPPED,
                    job=job,
                    message="Botão Easy Apply não encontrado",
                )
            
            await asyncio.sleep(2)
            
            # Process form pages
            for page_num in range(self.MAX_FORM_PAGES):
                logger.info(f"Processing form page {page_num + 1}")
                
                # Parse current form fields
                fields = await self.job_parser.parse_form_fields()
                
                # Answer each field
                for field in fields:
                    if field.field_type == "file":
                        # Handle file upload
                        if self.candidate.resume_path:
                            await self.browser.upload_file_invisible(
                                self.candidate.resume_path,
                            )
                    elif field.field_type in ("select", "radio"):
                        # Answer select/radio with AI
                        prompt = self.prompt_builder.build_for_select_question(
                            field.label,
                            field.options,
                            job,
                        )
                        selected, tokens = await self.ai.get_selected_option(
                            prompt,
                            field.options,
                        )
                        total_tokens += tokens
                        await self._fill_select_field(field.name, selected)
                    elif field.field_type in ("text", "textarea"):
                        # Answer text with AI
                        prompt = self.prompt_builder.build_for_text_question(
                            field.label,
                            job,
                        )
                        response = await self.ai.answer_text_question(prompt)
                        total_tokens += response.tokens_used
                        await self._fill_text_field(field.name, response.content)
                
                await asyncio.sleep(1)
                
                # Try to proceed to next step
                if await self._click_submit():
                    # Application submitted!
                    await self._close_modal()
                    return ApplyResult(
                        result=ApplicationResult.SUCCESS,
                        job=job,
                        message="Candidatura enviada com sucesso",
                        tokens_used=total_tokens,
                    )
                elif await self._click_review():
                    # Go to review page, then submit
                    await asyncio.sleep(1)
                    if await self._click_submit():
                        await self._close_modal()
                        return ApplyResult(
                            result=ApplicationResult.SUCCESS,
                            job=job,
                            message="Candidatura enviada com sucesso",
                            tokens_used=total_tokens,
                        )
                elif await self._click_next():
                    # Continue to next form page
                    await asyncio.sleep(1)
                    continue
                else:
                    # No navigation button found
                    break
            
            return ApplyResult(
                result=ApplicationResult.FAILED,
                job=job,
                message="Fluxo de formulário não completado",
                tokens_used=total_tokens,
            )
            
        except Exception as e:
            logger.error(f"Application failed: {e}")
            return ApplyResult(
                result=ApplicationResult.FAILED,
                message=str(e),
                tokens_used=total_tokens,
            )

    async def _click_easy_apply(self) -> bool:
        """Click the Easy Apply button."""
        try:
            button = await self.browser.page.wait_for_selector(
                self.EASY_APPLY_BUTTON,
                timeout=5000,
            )
            if button:
                await self.browser.human.click_element(button)
                return True
        except Exception:
            pass
        return False

    async def _click_next(self) -> bool:
        """Click the Next button."""
        try:
            button = await self.browser.page.query_selector(self.NEXT_BUTTON)
            if button:
                await self.browser.human.click_element(button)
                return True
        except Exception:
            pass
        return False

    async def _click_review(self) -> bool:
        """Click the Review button."""
        try:
            button = await self.browser.page.query_selector(self.REVIEW_BUTTON)
            if button:
                await self.browser.human.click_element(button)
                return True
        except Exception:
            pass
        return False

    async def _click_submit(self) -> bool:
        """Click the Submit button."""
        try:
            button = await self.browser.page.query_selector(self.SUBMIT_BUTTON)
            if button:
                await self.browser.human.click_element(button)
                return True
        except Exception:
            pass
        return False

    async def _close_modal(self) -> None:
        """Close the confirmation modal."""
        try:
            button = await self.browser.page.query_selector(self.CLOSE_BUTTON)
            if button:
                await asyncio.sleep(1)
                await self.browser.human.click_element(button)
        except Exception:
            pass

    async def _fill_text_field(self, name: str, value: str) -> None:
        """Fill a text input field."""
        try:
            selector = f'input[name="{name}"], textarea[name="{name}"]'
            element = await self.browser.page.query_selector(selector)
            if element:
                await self.browser.human.click_element(element)
                await element.fill("")  # Clear first
                await self.browser.human.type_text(value)
        except Exception as e:
            logger.warning(f"Failed to fill field {name}: {e}")

    async def _fill_select_field(self, name: str, value: str) -> None:
        """Fill a select dropdown."""
        try:
            selector = f'select[name="{name}"]'
            element = await self.browser.page.query_selector(selector)
            if element:
                await element.select_option(label=value)
        except Exception as e:
            logger.warning(f"Failed to select {name}: {e}")
