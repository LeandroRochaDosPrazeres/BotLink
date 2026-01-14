"""
Resume Upload Component - FE-03

PDF/DOCX resume upload with text extraction preview.
"""

import flet as ft
from pathlib import Path
from typing import Callable, Optional

from src.domain.entities import Candidate
from src.infrastructure.parsers import ResumeParser
from ..styles import Theme


def create_resume_upload(
    page: ft.Page,
    on_resume_loaded: Optional[Callable[[Candidate], None]] = None,
) -> ft.Container:
    """
    Create resume upload component.
    
    Features:
    - File picker for PDF/DOCX
    - Text extraction preview
    - Skill detection display
    """
    _candidate: Optional[Candidate] = None
    
    file_name = ft.Text("Nenhum arquivo selecionado")
    
    preview_text = ft.TextField(
        label="Texto extraído",
        multiline=True,
        min_lines=5,
        max_lines=10,
        read_only=True,
        border_radius=Theme.RADIUS_MD,
    )
    
    skills_row = ft.Row(controls=[], wrap=True, spacing=Theme.SPACING_XS)
    
    def _on_file_picked(e) -> None:
        """Handle file selection."""
        nonlocal _candidate
        
        if not e.files:
            return
        
        file = e.files[0]
        file_name.value = file.name
        
        try:
            path = Path(file.path)
            text = ResumeParser.extract_text(path)
            contact = ResumeParser.extract_contact_info(text)
            skills = ResumeParser.extract_skills(text)
            
            # Update preview
            preview_text.value = text[:2000] + ("..." if len(text) > 2000 else "")
            
            # Update skills chips
            skills_row.controls = [
                ft.Chip(label=ft.Text(skill), selected=True)
                for skill in skills[:10]
            ]
            
            # Create candidate
            _candidate = Candidate(
                name=contact.get("name") or "",
                email=contact.get("email") or "",
                phone=contact.get("phone") or "",
                resume_text=text,
                resume_path=path,
                skills=skills,
            )
            
            if on_resume_loaded:
                on_resume_loaded(_candidate)
            
        except Exception as ex:
            preview_text.value = f"Erro ao processar arquivo: {ex}"
        
        file_name.update()
        preview_text.update()
        skills_row.update()
    
    file_picker = ft.FilePicker()
    file_picker.on_result = _on_file_picked
    page.overlay.append(file_picker)
    
    return ft.Container(
        content=ft.Column([
            ft.Text("📄 Upload de Currículo", size=18, weight="bold"),
            ft.Row([
                ft.ElevatedButton(
                    "Selecionar Arquivo",
                    icon="upload_file",
                    on_click=lambda _: file_picker.pick_files(
                        allowed_extensions=["pdf", "docx", "doc"],
                        dialog_title="Selecione seu currículo",
                    ),
                ),
                file_name,
            ], spacing=Theme.SPACING_MD),
            preview_text,
            ft.Text("Habilidades detectadas:", size=14),
            skills_row,
        ], spacing=Theme.SPACING_MD),
        bgcolor=Theme.DARK_CARD,
        border_radius=Theme.RADIUS_LG,
        padding=Theme.SPACING_MD,
    )


class ResumeUpload:
    """Wrapper class for resume upload."""
    
    def __init__(
        self,
        on_resume_loaded: Optional[Callable[[Candidate], None]] = None,
    ):
        self.on_resume_loaded = on_resume_loaded
        self.container: Optional[ft.Container] = None
    
    def build(self, page: ft.Page) -> ft.Container:
        """Build the component with page reference."""
        self.container = create_resume_upload(page, self.on_resume_loaded)
        return self.container
    
    def __getattr__(self, name):
        if self.container:
            return getattr(self.container, name)
        raise AttributeError(f"ResumeUpload has no attribute '{name}'")
