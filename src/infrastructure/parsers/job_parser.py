"""
Job Parser - LinkedIn job page and form extraction.

Implements BE-04: Extract questions and options from Easy Apply forms.
Parses job descriptions, requirements, and application form fields.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from playwright.async_api import Page, ElementHandle

from src.domain.entities import Job


@dataclass
class FormField:
    """Represents a form field in the Easy Apply form."""
    
    field_type: str  # text, select, radio, checkbox, file, textarea
    label: str
    name: str = ""
    options: list[str] = field(default_factory=list)
    required: bool = False
    current_value: str = ""


class JobParser:
    """
    Parser for LinkedIn job postings and Easy Apply forms.
    
    Extracts job details and form fields for AI processing.
    """
    
    # Selectors for job details
    SELECTOR_JOB_TITLE = 'h1.job-title, h1.jobs-unified-top-card__job-title'
    SELECTOR_COMPANY = '.job-company-name, .jobs-unified-top-card__company-name'
    SELECTOR_LOCATION = '.job-location, .jobs-unified-top-card__bullet'
    SELECTOR_DESCRIPTION = '.job-description, .jobs-description__content'
    SELECTOR_JOB_ID = 'input[name="jobId"], [data-job-id]'
    
    # Selectors for Easy Apply form
    SELECTOR_FORM_SECTION = '.jobs-easy-apply-content, .jobs-easy-apply-form-section'
    SELECTOR_FORM_LABEL = 'label'
    SELECTOR_TEXT_INPUT = 'input[type="text"], input[type="email"], input[type="tel"]'
    SELECTOR_SELECT = 'select'
    SELECTOR_RADIO = 'input[type="radio"]'
    SELECTOR_CHECKBOX = 'input[type="checkbox"]'
    SELECTOR_TEXTAREA = 'textarea'
    SELECTOR_FILE_INPUT = 'input[type="file"]'

    def __init__(self, page: Page) -> None:
        """Initialize with Playwright page."""
        self.page = page

    async def parse_job_listing(self) -> Optional[Job]:
        """
        Parse the current job listing page.
        
        Returns:
            Job entity with extracted details, or None if parsing fails.
        """
        try:
            # Get job ID from URL or page
            job_id = await self._extract_job_id()
            if not job_id:
                return None
            
            # Get title
            title_elem = await self.page.query_selector(self.SELECTOR_JOB_TITLE)
            title = await title_elem.inner_text() if title_elem else "Unknown"
            
            # Get company
            company_elem = await self.page.query_selector(self.SELECTOR_COMPANY)
            company = await company_elem.inner_text() if company_elem else "Unknown"
            
            # Get location
            location_elem = await self.page.query_selector(self.SELECTOR_LOCATION)
            location = await location_elem.inner_text() if location_elem else ""
            
            # Get description
            desc_elem = await self.page.query_selector(self.SELECTOR_DESCRIPTION)
            description = await desc_elem.inner_text() if desc_elem else ""
            
            # Check for remote indicators
            is_remote = any(
                word in (description.lower() + location.lower())
                for word in ["remote", "remoto", "home office", "trabalho remoto"]
            )
            
            return Job(
                job_id=job_id,
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                description=description.strip(),
                url=self.page.url,
                is_remote=is_remote,
                is_easy_apply=True,  # We're on Easy Apply flow
            )
            
        except Exception as e:
            print(f"Failed to parse job listing: {e}")
            return None

    async def _extract_job_id(self) -> Optional[str]:
        """Extract job ID from URL or page."""
        # Try URL first
        url = self.page.url
        match = re.search(r'/jobs/view/(\d+)', url)
        if match:
            return match.group(1)
        
        match = re.search(r'currentJobId=(\d+)', url)
        if match:
            return match.group(1)
        
        # Try page element
        elem = await self.page.query_selector('[data-job-id]')
        if elem:
            return await elem.get_attribute('data-job-id')
        
        return None

    async def parse_form_fields(self) -> list[FormField]:
        """
        Parse the current Easy Apply form fields.
        
        Returns:
            List of FormField objects with labels and options.
        """
        fields: list[FormField] = []
        
        try:
            # Find form section
            form_section = await self.page.query_selector(self.SELECTOR_FORM_SECTION)
            if not form_section:
                form_section = self.page
            
            # Parse text inputs
            text_inputs = await form_section.query_selector_all(self.SELECTOR_TEXT_INPUT)
            for input_elem in text_inputs:
                field = await self._parse_text_input(input_elem)
                if field:
                    fields.append(field)
            
            # Parse textareas
            textareas = await form_section.query_selector_all(self.SELECTOR_TEXTAREA)
            for textarea_elem in textareas:
                field = await self._parse_textarea(textarea_elem)
                if field:
                    fields.append(field)
            
            # Parse select dropdowns
            selects = await form_section.query_selector_all(self.SELECTOR_SELECT)
            for select_elem in selects:
                field = await self._parse_select(select_elem)
                if field:
                    fields.append(field)
            
            # Parse radio button groups
            radio_groups = await self._find_radio_groups(form_section)
            fields.extend(radio_groups)
            
            # Parse file inputs
            file_inputs = await form_section.query_selector_all(self.SELECTOR_FILE_INPUT)
            for file_elem in file_inputs:
                field = await self._parse_file_input(file_elem)
                if field:
                    fields.append(field)
                    
        except Exception as e:
            print(f"Failed to parse form fields: {e}")
        
        return fields

    async def _parse_text_input(self, elem: ElementHandle) -> Optional[FormField]:
        """Parse a text input field."""
        try:
            name = await elem.get_attribute("name") or ""
            input_id = await elem.get_attribute("id") or ""
            required = await elem.get_attribute("required") is not None
            current = await elem.input_value()
            
            # Find associated label
            label = await self._find_label(elem, input_id)
            
            return FormField(
                field_type="text",
                label=label,
                name=name,
                required=required,
                current_value=current,
            )
        except Exception:
            return None

    async def _parse_textarea(self, elem: ElementHandle) -> Optional[FormField]:
        """Parse a textarea field."""
        try:
            name = await elem.get_attribute("name") or ""
            input_id = await elem.get_attribute("id") or ""
            required = await elem.get_attribute("required") is not None
            current = await elem.input_value()
            
            label = await self._find_label(elem, input_id)
            
            return FormField(
                field_type="textarea",
                label=label,
                name=name,
                required=required,
                current_value=current,
            )
        except Exception:
            return None

    async def _parse_select(self, elem: ElementHandle) -> Optional[FormField]:
        """Parse a select dropdown."""
        try:
            name = await elem.get_attribute("name") or ""
            select_id = await elem.get_attribute("id") or ""
            required = await elem.get_attribute("required") is not None
            
            # Get options
            options: list[str] = []
            option_elems = await elem.query_selector_all("option")
            for opt in option_elems:
                opt_text = await opt.inner_text()
                if opt_text.strip():
                    options.append(opt_text.strip())
            
            label = await self._find_label(elem, select_id)
            
            return FormField(
                field_type="select",
                label=label,
                name=name,
                options=options,
                required=required,
            )
        except Exception:
            return None

    async def _find_radio_groups(self, container: ElementHandle) -> list[FormField]:
        """Find and parse radio button groups."""
        fields: list[FormField] = []
        
        try:
            radios = await container.query_selector_all(self.SELECTOR_RADIO)
            groups: dict[str, list[str]] = {}
            
            for radio in radios:
                name = await radio.get_attribute("name") or ""
                if not name:
                    continue
                    
                if name not in groups:
                    groups[name] = []
                
                # Get label text
                parent = await radio.evaluate_handle("el => el.closest('label')")
                if parent:
                    label_text = await parent.inner_text()
                    groups[name].append(label_text.strip())
            
            for name, options in groups.items():
                fields.append(FormField(
                    field_type="radio",
                    label=name,  # Will need label from fieldset/legend
                    name=name,
                    options=options,
                ))
                
        except Exception:
            pass
        
        return fields

    async def _parse_file_input(self, elem: ElementHandle) -> Optional[FormField]:
        """Parse a file input field."""
        try:
            name = await elem.get_attribute("name") or ""
            accept = await elem.get_attribute("accept") or ""
            
            return FormField(
                field_type="file",
                label=f"Upload ({accept})" if accept else "Upload",
                name=name,
            )
        except Exception:
            return None

    async def _find_label(self, elem: ElementHandle, for_id: str) -> str:
        """Find label text for a form element."""
        try:
            # Try label[for=id]
            if for_id:
                label_elem = await self.page.query_selector(f'label[for="{for_id}"]')
                if label_elem:
                    return (await label_elem.inner_text()).strip()
            
            # Try parent label
            parent_label = await elem.evaluate_handle("el => el.closest('label')")
            if parent_label:
                return (await parent_label.inner_text()).strip()
            
            # Try aria-label
            aria_label = await elem.get_attribute("aria-label")
            if aria_label:
                return aria_label
            
            # Try placeholder
            placeholder = await elem.get_attribute("placeholder")
            if placeholder:
                return placeholder
                
        except Exception:
            pass
        
        return "Unknown field"
