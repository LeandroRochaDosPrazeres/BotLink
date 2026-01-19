"""
AI Form Filler - Intelligent form field detection and filling.

Uses GPT-4o to analyze form fields and generate contextual responses
based on candidate profile, resume, and job requirements.
"""

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from playwright.async_api import Page, ElementHandle

if TYPE_CHECKING:
    from src.infrastructure.ai.openai_adapter import OpenAIAdapter
    from src.infrastructure.ai.prompt_builder import PromptBuilder
    from src.domain.entities.candidate import Candidate


@dataclass
class FormField:
    """Represents a detected form field."""
    
    element: ElementHandle
    field_type: str  # text, textarea, select, radio, checkbox
    label: str
    name: str
    placeholder: str
    current_value: str
    options: List[str] = field(default_factory=list)  # For select/radio
    required: bool = False
    selector: str = ""


@dataclass
class FormFillerResult:
    """Result of form filling operation."""
    
    success: bool
    fields_detected: int = 0
    fields_filled: int = 0
    fields_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    details: List[Dict[str, Any]] = field(default_factory=list)


class AIFormFiller:
    """
    AI-powered form filler for LinkedIn Easy Apply and similar forms.
    
    Detects form fields, analyzes their purpose, and fills them
    intelligently using the candidate's profile and GPT-4o.
    """
    
    def __init__(
        self,
        page: Page,
        openai_adapter: "OpenAIAdapter",
        prompt_builder: "PromptBuilder",
        candidate: "Candidate",
        log_callback: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """
        Initialize the AI Form Filler.
        
        Args:
            page: Playwright page instance.
            openai_adapter: OpenAI adapter for AI completions.
            prompt_builder: Prompt builder for context construction.
            candidate: Candidate entity with profile info.
            log_callback: Optional logging function (message, level).
        """
        self.page = page
        self.openai = openai_adapter
        self.prompt_builder = prompt_builder
        self.candidate = candidate
        self.log_callback = log_callback
        
        # Job context (set per application)
        self.job_title: str = ""
        self.job_company: str = ""
        self.job_description: str = ""
    
    def _log(self, message: str, level: str = "info") -> None:
        """Log a message if callback is available."""
        if self.log_callback:
            self.log_callback(message, level)
    
    def set_job_context(
        self,
        title: str = "",
        company: str = "",
        description: str = "",
    ) -> None:
        """
        Set the current job context for better AI responses.
        
        Args:
            title: Job title.
            company: Company name.
            description: Job description text.
        """
        self.job_title = title
        self.job_company = company
        self.job_description = description
    
    async def detect_form_fields(self) -> List[FormField]:
        """
        Detect all fillable form fields on the current page/modal.
        
        Returns:
            List of FormField objects representing detected fields.
        """
        fields: List[FormField] = []
        
        try:
            # Find the application modal or form container
            modal = await self.page.query_selector('.artdeco-modal__content')
            container = modal if modal else self.page
            
            # Detect text inputs
            text_inputs = await container.query_selector_all(
                'input[type="text"]:not([hidden]), '
                'input[type="email"]:not([hidden]), '
                'input[type="tel"]:not([hidden]), '
                'input[type="number"]:not([hidden]), '
                'input:not([type]):not([hidden])'
            )
            
            for inp in text_inputs:
                try:
                    # Skip if already filled and not required
                    value = await inp.get_attribute('value') or ""
                    if value.strip():
                        continue  # Already has value
                    
                    field = await self._create_form_field(inp, "text")
                    if field and field.label:  # Only add if we found a label
                        fields.append(field)
                except Exception:
                    continue
            
            # Detect textareas
            textareas = await container.query_selector_all('textarea:not([hidden])')
            for ta in textareas:
                try:
                    value = await ta.input_value() if hasattr(ta, 'input_value') else ""
                    if value and value.strip():
                        continue  # Already has value
                    
                    field = await self._create_form_field(ta, "textarea")
                    if field and field.label:
                        fields.append(field)
                except Exception:
                    continue
            
            # Detect select dropdowns
            selects = await container.query_selector_all('select:not([hidden])')
            for sel in selects:
                try:
                    field = await self._create_form_field(sel, "select")
                    if field and field.label:
                        # Get options
                        options_els = await sel.query_selector_all('option')
                        options = []
                        for opt in options_els:
                            text = await opt.inner_text()
                            if text and text.strip() and text.strip() != "Selecione uma opção":
                                options.append(text.strip())
                        field.options = options
                        fields.append(field)
                except Exception:
                    continue
            
            # Detect LinkedIn-style custom dropdowns
            custom_dropdowns = await container.query_selector_all(
                '[data-test-text-entity-list-form-component], '
                '.artdeco-dropdown, '
                '[class*="dropdown"]'
            )
            for dd in custom_dropdowns:
                try:
                    field = await self._create_form_field(dd, "dropdown")
                    if field and field.label:
                        fields.append(field)
                except Exception:
                    continue
            
            # Detect radio button groups
            radio_groups = await container.query_selector_all('fieldset, [role="radiogroup"]')
            for rg in radio_groups:
                try:
                    field = await self._create_radio_field(rg)
                    if field and field.label:
                        fields.append(field)
                except Exception:
                    continue
            
        except Exception as e:
            self._log(f"Error detecting form fields: {e}", "error")
        
        return fields
    
    async def _create_form_field(
        self,
        element: ElementHandle,
        field_type: str,
    ) -> Optional[FormField]:
        """
        Create a FormField object from an element.
        
        Args:
            element: The form element.
            field_type: Type of field (text, textarea, select, etc).
            
        Returns:
            FormField object or None if unable to process.
        """
        try:
            # Get field attributes
            name = await element.get_attribute('name') or ""
            placeholder = await element.get_attribute('placeholder') or ""
            required = await element.get_attribute('required') is not None
            aria_required = await element.get_attribute('aria-required')
            if aria_required == "true":
                required = True
            
            # Try to get label
            label = ""
            
            # Method 1: aria-label
            aria_label = await element.get_attribute('aria-label')
            if aria_label:
                label = aria_label
            
            # Method 2: id -> for label
            if not label:
                el_id = await element.get_attribute('id')
                if el_id:
                    label_el = await self.page.query_selector(f'label[for="{el_id}"]')
                    if label_el:
                        label = await label_el.inner_text()
            
            # Method 3: Parent label
            if not label:
                parent = await element.evaluate_handle('el => el.closest("label")')
                if parent:
                    try:
                        label = await parent.inner_text()
                    except:
                        pass
            
            # Method 4: Preceding label/text
            if not label:
                prev_label = await element.evaluate_handle('''
                    el => {
                        let prev = el.previousElementSibling;
                        while (prev) {
                            if (prev.tagName === 'LABEL' || prev.tagName === 'SPAN') {
                                return prev;
                            }
                            prev = prev.previousElementSibling;
                        }
                        return null;
                    }
                ''')
                if prev_label:
                    try:
                        label = await prev_label.inner_text()
                    except:
                        pass
            
            # Method 5: Use placeholder as label
            if not label and placeholder:
                label = placeholder
            
            # Method 6: Use name as label
            if not label and name:
                label = name.replace('_', ' ').replace('-', ' ').title()
            
            # Get current value
            current_value = ""
            if field_type == "text":
                current_value = await element.get_attribute('value') or ""
            elif field_type == "textarea":
                current_value = await element.input_value() if hasattr(element, 'input_value') else ""
            
            return FormField(
                element=element,
                field_type=field_type,
                label=label.strip() if label else "",
                name=name,
                placeholder=placeholder,
                current_value=current_value,
                required=required,
            )
            
        except Exception as e:
            self._log(f"Error creating form field: {e}", "warning")
            return None
    
    async def _create_radio_field(self, fieldset: ElementHandle) -> Optional[FormField]:
        """
        Create a FormField for a radio button group.
        
        Args:
            fieldset: The fieldset or container element.
            
        Returns:
            FormField object or None.
        """
        try:
            # Get legend/label
            label = ""
            legend = await fieldset.query_selector('legend')
            if legend:
                label = await legend.inner_text()
            
            if not label:
                aria_label = await fieldset.get_attribute('aria-label')
                if aria_label:
                    label = aria_label
            
            # Get radio options
            radios = await fieldset.query_selector_all('input[type="radio"]')
            options = []
            
            for radio in radios:
                radio_id = await radio.get_attribute('id')
                if radio_id:
                    label_el = await self.page.query_selector(f'label[for="{radio_id}"]')
                    if label_el:
                        opt_text = await label_el.inner_text()
                        if opt_text:
                            options.append(opt_text.strip())
            
            if not options:
                return None
            
            return FormField(
                element=fieldset,
                field_type="radio",
                label=label.strip() if label else "",
                name="",
                placeholder="",
                current_value="",
                options=options,
                required=False,
            )
            
        except Exception:
            return None
    
    async def fill_field(self, field: FormField) -> bool:
        """
        Fill a single form field using AI.
        
        Args:
            field: The FormField to fill.
            
        Returns:
            True if successfully filled, False otherwise.
        """
        try:
            # Build context for AI
            context = self._build_context_for_field(field)
            
            if field.field_type in ("text", "textarea"):
                return await self._fill_text_field(field, context)
            elif field.field_type == "select":
                return await self._fill_select_field(field, context)
            elif field.field_type == "dropdown":
                return await self._fill_dropdown_field(field, context)
            elif field.field_type == "radio":
                return await self._fill_radio_field(field, context)
            else:
                return False
                
        except Exception as e:
            self._log(f"Error filling field '{field.label}': {e}", "error")
            return False
    
    def _build_context_for_field(self, field: FormField) -> str:
        """
        Build context string for AI to understand and answer the field.
        
        Args:
            field: The form field.
            
        Returns:
            Context string for AI prompt.
        """
        parts = [
            "You are helping to fill out a job application form.",
            f"\nJob: {self.job_title} at {self.job_company}" if self.job_title else "",
        ]
        
        if self.candidate:
            parts.append(f"\n\n=== CANDIDATE PROFILE ===\n{self.candidate.context_for_ai}")
        
        parts.append(f"\n\n=== FORM FIELD ===")
        parts.append(f"Label: {field.label}")
        
        if field.placeholder:
            parts.append(f"Placeholder/Hint: {field.placeholder}")
        
        if field.options:
            parts.append(f"Available Options: {', '.join(field.options)}")
        
        if field.required:
            parts.append("This field is REQUIRED.")
        
        return "\n".join(parts)
    
    async def _fill_text_field(self, field: FormField, context: str) -> bool:
        """Fill a text input or textarea field."""
        try:
            # First try to get a smart answer from AI
            prompt = f"""{context}

Based on the candidate's profile and the job context, provide the BEST answer for this field.

IMPORTANT RULES:
1. Be concise and direct
2. For phone numbers, use the format from the resume
3. For email, use the exact email from the profile
4. For name, use the full name from the profile
5. For experience/years questions, extract from resume
6. For salary expectations, use the extra info if provided, otherwise say "Negotiable" or "A combinar"
7. For availability/start date, use extra info if provided, otherwise say "Immediately" or "Imediato"
8. For links (LinkedIn, GitHub, etc), only provide if in the resume/profile
9. Keep answers natural and professional
10. Answer in Portuguese (Brazil) if the field label is in Portuguese

Respond with ONLY the answer text, nothing else. No explanations."""

            response = await self.openai.complete(prompt, max_tokens=100)
            
            if response:
                answer = response.strip().strip('"').strip("'")
                
                # Apply smart defaults for common fields
                answer = self._apply_smart_defaults(field, answer)
                
                # Clear and fill the field
                await field.element.click()
                await asyncio.sleep(0.2)
                await field.element.fill("")  # Clear first
                await asyncio.sleep(0.1)
                await field.element.fill(answer)
                await asyncio.sleep(0.2)
                
                self._log(f"    📝 {field.label}: {answer[:50]}...", "info")
                return True
            
            return False
            
        except Exception as e:
            self._log(f"Error in text field: {e}", "warning")
            return False
    
    def _apply_smart_defaults(self, field: FormField, ai_answer: str) -> str:
        """
        Apply smart defaults for common field types.
        
        Args:
            field: The form field.
            ai_answer: The AI-generated answer.
            
        Returns:
            Potentially modified answer.
        """
        label_lower = field.label.lower()
        
        # Name fields
        if any(kw in label_lower for kw in ['nome', 'name', 'full name']):
            if self.candidate and self.candidate.name:
                return self.candidate.name
        
        # Email fields
        if any(kw in label_lower for kw in ['email', 'e-mail', 'correo']):
            if self.candidate and self.candidate.email:
                return self.candidate.email
        
        # Phone fields
        if any(kw in label_lower for kw in ['phone', 'telefone', 'celular', 'mobile']):
            if self.candidate and self.candidate.phone:
                return self.candidate.phone
        
        # If AI returned something weird for salary
        if any(kw in label_lower for kw in ['salário', 'salary', 'pretensão']):
            if len(ai_answer) < 3 or ai_answer.lower() in ['n/a', 'na', 'none']:
                return "A combinar"
        
        return ai_answer
    
    async def _fill_select_field(self, field: FormField, context: str) -> bool:
        """Fill a select dropdown field."""
        try:
            if not field.options:
                return False
            
            prompt = f"""{context}

Choose the BEST option from the available choices that matches the candidate's profile.

Available options:
{chr(10).join(f"- {opt}" for opt in field.options)}

Respond with ONLY the exact text of the chosen option. No explanations."""

            response = await self.openai.complete(prompt, max_tokens=50)
            
            if response:
                chosen = response.strip().strip('"').strip("'")
                
                # Find best matching option
                best_match = None
                for opt in field.options:
                    if opt.lower() == chosen.lower():
                        best_match = opt
                        break
                    if chosen.lower() in opt.lower() or opt.lower() in chosen.lower():
                        best_match = opt
                
                if best_match:
                    await field.element.select_option(label=best_match)
                    self._log(f"    📋 {field.label}: {best_match}", "info")
                    return True
                elif field.options:
                    # Default to first non-empty option
                    await field.element.select_option(label=field.options[0])
                    self._log(f"    📋 {field.label}: {field.options[0]} (default)", "info")
                    return True
            
            return False
            
        except Exception as e:
            self._log(f"Error in select field: {e}", "warning")
            return False
    
    async def _fill_dropdown_field(self, field: FormField, context: str) -> bool:
        """Fill a LinkedIn-style custom dropdown."""
        try:
            # Click to open dropdown
            await field.element.click()
            await asyncio.sleep(0.5)
            
            # Find dropdown options
            options_container = await self.page.query_selector(
                '.artdeco-dropdown__content-inner, '
                '[role="listbox"], '
                '.dropdown-options'
            )
            
            if not options_container:
                return False
            
            option_els = await options_container.query_selector_all(
                '[role="option"], li, .artdeco-dropdown__option'
            )
            
            options = []
            for opt_el in option_els:
                text = await opt_el.inner_text()
                if text and text.strip():
                    options.append((opt_el, text.strip()))
            
            if not options:
                # Close dropdown
                await self.page.keyboard.press("Escape")
                return False
            
            field.options = [opt[1] for opt in options]
            
            prompt = f"""{context}

Choose the BEST option:
{chr(10).join(f"- {opt[1]}" for opt in options)}

Respond with ONLY the exact text of the chosen option."""

            response = await self.openai.complete(prompt, max_tokens=50)
            
            if response:
                chosen = response.strip().strip('"').strip("'")
                
                # Find and click the option
                for opt_el, opt_text in options:
                    if opt_text.lower() == chosen.lower() or chosen.lower() in opt_text.lower():
                        await opt_el.click()
                        self._log(f"    📋 {field.label}: {opt_text}", "info")
                        return True
                
                # Default to first option
                if options:
                    await options[0][0].click()
                    self._log(f"    📋 {field.label}: {options[0][1]} (default)", "info")
                    return True
            
            # Close dropdown
            await self.page.keyboard.press("Escape")
            return False
            
        except Exception as e:
            self._log(f"Error in dropdown field: {e}", "warning")
            try:
                await self.page.keyboard.press("Escape")
            except:
                pass
            return False
    
    async def _fill_radio_field(self, field: FormField, context: str) -> bool:
        """Fill a radio button group."""
        try:
            if not field.options:
                return False
            
            prompt = f"""{context}

Choose the BEST option:
{chr(10).join(f"- {opt}" for opt in field.options)}

Respond with ONLY the exact text of the chosen option."""

            response = await self.openai.complete(prompt, max_tokens=50)
            
            if response:
                chosen = response.strip().strip('"').strip("'")
                
                # Find and click the radio
                radios = await field.element.query_selector_all('input[type="radio"]')
                
                for radio in radios:
                    radio_id = await radio.get_attribute('id')
                    if radio_id:
                        label_el = await self.page.query_selector(f'label[for="{radio_id}"]')
                        if label_el:
                            label_text = await label_el.inner_text()
                            if label_text and (
                                label_text.strip().lower() == chosen.lower() or
                                chosen.lower() in label_text.strip().lower()
                            ):
                                await radio.click()
                                self._log(f"    ⭕ {field.label}: {label_text.strip()}", "info")
                                return True
                
                # Default to first option
                if radios:
                    await radios[0].click()
                    return True
            
            return False
            
        except Exception as e:
            self._log(f"Error in radio field: {e}", "warning")
            return False
    
    async def fill_all_fields(self) -> FormFillerResult:
        """
        Detect and fill all form fields on the current page/modal.
        
        Returns:
            FormFillerResult with statistics and details.
        """
        result = FormFillerResult(success=False)
        
        try:
            # Detect fields
            fields = await self.detect_form_fields()
            result.fields_detected = len(fields)
            
            if not fields:
                result.success = True  # No fields to fill is still success
                return result
            
            # Fill each field
            for field in fields:
                try:
                    filled = await self.fill_field(field)
                    
                    if filled:
                        result.fields_filled += 1
                        result.details.append({
                            "label": field.label,
                            "type": field.field_type,
                            "status": "filled",
                        })
                    else:
                        result.fields_skipped += 1
                        result.details.append({
                            "label": field.label,
                            "type": field.field_type,
                            "status": "skipped",
                        })
                        
                except Exception as e:
                    result.errors.append(f"Field '{field.label}': {str(e)}")
                    result.details.append({
                        "label": field.label,
                        "type": field.field_type,
                        "status": "error",
                        "error": str(e),
                    })
            
            result.success = len(result.errors) == 0
            
        except Exception as e:
            result.errors.append(f"General error: {str(e)}")
        
        return result
