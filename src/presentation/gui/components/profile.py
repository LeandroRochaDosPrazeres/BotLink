"""
Profile Panel Component - FE-04

Extended profile with bio.
"""

import flet as ft
from typing import Callable, Optional

from ..styles import Theme


def create_profile_panel(
    page: ft.Page,
    on_bio_change: Optional[Callable[[str], None]] = None,
    initial_bio: str = "",
) -> ft.Container:
    """
    Create extended profile panel (web-compatible).
    
    Features:
    - Bio/cover letter textarea
    """
    
    def _on_bio_change_handler(e) -> None:
        """Handle bio text change."""
        if on_bio_change:
            on_bio_change(e.control.value or "")
    
    bio_input = ft.TextField(
        label="Bio / Carta de Apresentação",
        hint_text="Descreva seu perfil profissional, projetos relevantes, motivações...",
        multiline=True,
        min_lines=6,
        max_lines=12,
        value=initial_bio,
        border_radius=Theme.RADIUS_MD,
        on_change=_on_bio_change_handler,
    )
    
    return ft.Container(
        content=ft.Column([
            ft.Text("📝 Perfil Estendido", size=18, weight="bold"),
            ft.Text("Informações adicionais para personalizar suas candidaturas:", size=12, color=Theme.DARK_TEXT_SECONDARY),
            bio_input,
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
