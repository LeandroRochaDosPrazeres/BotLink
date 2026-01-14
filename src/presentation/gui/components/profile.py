"""
Profile Panel Component - FE-04

Extended profile with bio and attachments.
"""

import flet as ft
from pathlib import Path
from typing import Callable, Optional

from ..styles import Theme


def create_profile_panel(
    page: ft.Page,
    on_bio_change: Optional[Callable[[str], None]] = None,
    initial_bio: str = "",
) -> ft.Container:
    """
    Create extended profile panel.
    
    Features:
    - Bio/cover letter textarea
    - Additional attachments list
    """
    _attachments: list[Path] = []
    
    attachments_list = ft.Column(controls=[], spacing=Theme.SPACING_XS)
    
    def _on_bio_change_handler(e) -> None:
        """Handle bio text change."""
        if on_bio_change:
            on_bio_change(e.control.value or "")
    
    def _on_attachment_picked(e) -> None:
        """Handle attachment file selection."""
        if not e.files:
            return
        
        for file in e.files:
            path = Path(file.path)
            if path not in _attachments:
                _attachments.append(path)
                attachments_list.controls.append(
                    ft.Row([
                        ft.Icon("insert_drive_file", size=16),
                        ft.Text(file.name, expand=True),
                    ])
                )
        
        attachments_list.update()
    
    bio_input = ft.TextField(
        label="Bio / Carta de Apresentação",
        hint_text="Descreva seu perfil profissional, projetos relevantes...",
        multiline=True,
        min_lines=6,
        max_lines=12,
        value=initial_bio,
        border_radius=Theme.RADIUS_MD,
        on_change=_on_bio_change_handler,
    )
    
    file_picker = ft.FilePicker()
    file_picker.on_result = _on_attachment_picked
    page.overlay.append(file_picker)
    
    return ft.Container(
        content=ft.Column([
            ft.Text("📝 Perfil Estendido", size=18, weight="bold"),
            bio_input,
            ft.Text("Anexos Extras (Portfólio, Certificados):", size=14),
            ft.OutlinedButton(
                "Adicionar Anexo",
                icon="attach_file",
                on_click=lambda _: file_picker.pick_files(
                    dialog_title="Selecione arquivo adicional",
                ),
            ),
            attachments_list,
        ], spacing=Theme.SPACING_MD),
        bgcolor=Theme.DARK_CARD,
        border_radius=Theme.RADIUS_LG,
        padding=Theme.SPACING_MD,
    )


class ProfilePanel:
    """Wrapper class for profile panel."""
    
    def __init__(
        self,
        on_bio_change: Optional[Callable[[str], None]] = None,
        initial_bio: str = "",
    ):
        self.on_bio_change = on_bio_change
        self.initial_bio = initial_bio
        self.container: Optional[ft.Container] = None
    
    def build(self, page: ft.Page) -> ft.Container:
        """Build the component with page reference."""
        self.container = create_profile_panel(page, self.on_bio_change, self.initial_bio)
        return self.container
    
    def __getattr__(self, name):
        if self.container:
            return getattr(self.container, name)
        raise AttributeError(f"ProfilePanel has no attribute '{name}'")
