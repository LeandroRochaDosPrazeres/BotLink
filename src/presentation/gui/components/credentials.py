"""
Credentials Panel Component - FE-02

LinkedIn login credentials with encryption.
"""

import flet as ft
from typing import Callable, Optional

from src.domain.value_objects import Credentials
from ..styles import Theme


def create_credentials_panel(
    on_credentials_save: Optional[Callable[[Credentials], None]] = None,
    on_verify_session: Optional[Callable[[], None]] = None,
    session_valid: bool = False,
) -> ft.Container:
    """
    Create credentials panel for LinkedIn login.
    
    Features:
    - Username/email input
    - Password input (hidden)
    - Session verification button
    - Save credentials locally (encrypted)
    """
    _session_valid = session_valid
    
    username_input = ft.TextField(
        label="Email ou Usuário LinkedIn",
        hint_text="seu.email@exemplo.com",
        border_radius=Theme.RADIUS_MD,
        prefix_icon="person",
    )
    
    password_input = ft.TextField(
        label="Senha",
        password=True,
        can_reveal_password=True,
        border_radius=Theme.RADIUS_MD,
        prefix_icon="lock",
    )
    
    status_icon = ft.Icon(
        "check_circle" if _session_valid else "warning",
        color=Theme.SUCCESS if _session_valid else Theme.WARNING,
    )
    
    status_text = ft.Text(
        "Sessão ativa" if _session_valid else "Sessão não verificada",
    )
    
    session_status = ft.Row([status_icon, status_text])
    
    async def _on_save(e) -> None:
        """Save credentials."""
        username = username_input.value
        password = password_input.value
        
        if not username or not password:
            return
        
        credentials = Credentials(username=username, password=password)
        
        if on_credentials_save:
            await on_credentials_save(credentials)
        
        # Clear password from UI
        password_input.value = ""
        password_input.update()
    
    async def _on_verify(e) -> None:
        """Verify session."""
        if on_verify_session:
            await on_verify_session()
    
    save_button = ft.ElevatedButton(
        "Salvar Credenciais",
        icon="save",
        on_click=_on_save,
    )
    
    verify_button = ft.OutlinedButton(
        "Verificar Sessão",
        icon="refresh",
        on_click=_on_verify,
    )
    
    container = ft.Container(
        content=ft.Column([
            ft.Text("🔐 Credenciais LinkedIn", size=18, weight="bold"),
            username_input,
            password_input,
            ft.Row([save_button, verify_button], spacing=Theme.SPACING_MD),
            session_status,
        ], spacing=Theme.SPACING_MD),
        bgcolor=Theme.DARK_CARD,
        border_radius=Theme.RADIUS_LG,
        padding=Theme.SPACING_MD,
    )
    
    controls = {
        "status_icon": status_icon,
        "status_text": status_text,
    }
    
    return container, controls


class CredentialsPanel:
    """Wrapper class for credentials panel."""
    
    def __init__(
        self,
        on_credentials_save: Optional[Callable[[Credentials], None]] = None,
        on_verify_session: Optional[Callable[[], None]] = None,
        session_valid: bool = False,
    ):
        self.container, self._controls = create_credentials_panel(
            on_credentials_save, on_verify_session, session_valid
        )
    
    def set_status(self, valid: bool) -> None:
        """Update session status."""
        self._controls["status_icon"].name = "check_circle" if valid else "warning"
        self._controls["status_icon"].color = Theme.SUCCESS if valid else Theme.WARNING
        self._controls["status_text"].value = "Sessão ativa" if valid else "Sessão não verificada"
        self.container.update()
    
    def __getattr__(self, name):
        return getattr(self.container, name)
