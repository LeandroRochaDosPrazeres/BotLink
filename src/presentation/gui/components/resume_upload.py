"""
Resume Upload Component - FE-03

Resume profile input for web mode.
"""

import flet as ft
from typing import Callable, Optional

from src.domain.entities import Candidate
from ..styles import Theme


def create_resume_upload(
    page: ft.Page,
    on_resume_loaded: Optional[Callable[[Candidate], None]] = None,
) -> ft.Container:
    """
    Create resume upload component (web-compatible).
    
    Features:
    - Text area for pasting resume content
    - Manual info input
    - Skill input
    """
    _candidate: Optional[Candidate] = None
    
    name_input = ft.TextField(
        label="Nome Completo",
        hint_text="Seu nome completo",
        border_radius=Theme.RADIUS_MD,
    )
    
    email_input = ft.TextField(
        label="Email",
        hint_text="seu.email@exemplo.com",
        border_radius=Theme.RADIUS_MD,
        expand=True,
    )
    
    phone_input = ft.TextField(
        label="Telefone",
        hint_text="(11) 99999-9999",
        border_radius=Theme.RADIUS_MD,
        expand=True,
    )
    
    resume_text_input = ft.TextField(
        label="Cole o texto do seu currículo aqui",
        hint_text="Cole aqui o conteúdo do seu currículo (experiências, formação, habilidades...)",
        multiline=True,
        min_lines=8,
        max_lines=15,
        border_radius=Theme.RADIUS_MD,
    )
    
    skills_input = ft.TextField(
        label="Habilidades (separadas por vírgula)",
        hint_text="Python, JavaScript, SQL, React...",
        border_radius=Theme.RADIUS_MD,
    )
    
    status_text = ft.Text("", color=Theme.SUCCESS)
    
    def _on_save_profile(e) -> None:
        """Save the profile information."""
        nonlocal _candidate
        
        name = name_input.value or ""
        email = email_input.value or ""
        phone = phone_input.value or ""
        resume_text = resume_text_input.value or ""
        skills_str = skills_input.value or ""
        
        # Parse skills
        skills = [s.strip() for s in skills_str.split(",") if s.strip()]
        
        if not name or not resume_text:
            status_text.value = "⚠️ Preencha pelo menos o nome e o texto do currículo"
            status_text.color = Theme.WARNING
            status_text.update()
            return
        
        # Create candidate
        _candidate = Candidate(
            name=name,
            email=email,
            phone=phone,
            resume_text=resume_text,
            resume_path=None,
            skills=skills,
        )
        
        status_text.value = f"✅ Perfil salvo: {name}"
        status_text.color = Theme.SUCCESS
        status_text.update()
        
        if on_resume_loaded:
            on_resume_loaded(_candidate)
    
    save_button = ft.ElevatedButton(
        "Salvar Perfil",
        icon="save",
        bgcolor=Theme.SUCCESS,
        color="white",
        on_click=_on_save_profile,
    )
    
    return ft.Container(
        content=ft.Column([
            ft.Text("📄 Perfil do Candidato", size=18, weight="bold"),
            ft.Text("Preencha suas informações para a candidatura automática:", size=12, color=Theme.DARK_TEXT_SECONDARY),
            name_input,
            ft.Row([email_input, phone_input], spacing=Theme.SPACING_MD),
            resume_text_input,
            skills_input,
            ft.Row([save_button, status_text], spacing=Theme.SPACING_MD),
        ], spacing=Theme.SPACING_MD, scroll="auto"),
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
