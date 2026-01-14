"""
Controls Panel Component - FE-05

Start/Stop bot controls with status display.
"""

import flet as ft
from typing import Callable, Optional

from ..styles import Theme


def create_controls_panel(
    on_start: Optional[Callable[[], None]] = None,
    on_stop: Optional[Callable[[], None]] = None,
    is_running: bool = False,
) -> tuple[ft.Container, dict]:
    """
    Create bot control panel.
    
    Features:
    - Start button (green)
    - Stop button (red, graceful shutdown)
    - Status indicator
    - Daily progress display
    
    Returns:
        Tuple of (container, controls_dict) for external updates
    """
    _is_running = is_running
    _applications_today = 0
    _daily_limit = 50
    
    async def _on_start_click(e) -> None:
        if on_start:
            await on_start()
    
    async def _on_stop_click(e) -> None:
        if on_stop:
            await on_stop()
    
    start_button = ft.ElevatedButton(
        "Iniciar BOT",
        icon="play_arrow",
        bgcolor=Theme.SUCCESS,
        color="white",
        on_click=_on_start_click,
        disabled=_is_running,
    )
    
    stop_button = ft.ElevatedButton(
        "Parar BOT",
        icon="stop",
        bgcolor=Theme.ERROR,
        color="white",
        on_click=_on_stop_click,
        disabled=not _is_running,
    )
    
    status_indicator = ft.Container(
        width=12,
        height=12,
        border_radius=6,
        bgcolor=Theme.SUCCESS if _is_running else Theme.DARK_TEXT_SECONDARY,
    )
    
    status_text = ft.Text(
        "Em execução" if _is_running else "Parado",
        weight="bold",
    )
    
    progress_bar = ft.ProgressBar(
        value=_applications_today / max(_daily_limit, 1),
        color=Theme.PRIMARY,
        bgcolor=Theme.DARK_CARD,
    )
    
    progress_text = ft.Text(
        f"{_applications_today} / {_daily_limit} candidaturas hoje",
    )
    
    container = ft.Container(
        content=ft.Column([
            ft.Text("🤖 Controles", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([start_button, stop_button], spacing=Theme.SPACING_MD),
            ft.Row([status_indicator, status_text]),
            ft.Divider(),
            ft.Text("Progresso Diário", size=14),
            progress_bar,
            progress_text,
        ], spacing=Theme.SPACING_MD),
        bgcolor=Theme.DARK_CARD,
        border_radius=Theme.RADIUS_LG,
        padding=Theme.SPACING_MD,
    )
    
    controls = {
        "start_button": start_button,
        "stop_button": stop_button,
        "status_indicator": status_indicator,
        "status_text": status_text,
        "progress_bar": progress_bar,
        "progress_text": progress_text,
    }
    
    return container, controls


class ControlsPanel:
    """Wrapper class for controls panel."""
    
    def __init__(
        self,
        on_start: Optional[Callable[[], None]] = None,
        on_stop: Optional[Callable[[], None]] = None,
        is_running: bool = False,
    ):
        self.container, self._controls = create_controls_panel(on_start, on_stop, is_running)
        self._is_running = is_running
    
    def set_running(self, is_running: bool) -> None:
        """Update running state."""
        self._is_running = is_running
        self._controls["start_button"].disabled = is_running
        self._controls["stop_button"].disabled = not is_running
        self._controls["status_indicator"].bgcolor = (
            Theme.SUCCESS if is_running else Theme.DARK_TEXT_SECONDARY
        )
        self._controls["status_text"].value = (
            "Em execução" if is_running else "Parado"
        )
        self.container.update()
    
    def set_progress(self, applications_today: int, daily_limit: int) -> None:
        """Update progress display."""
        self._controls["progress_bar"].value = applications_today / max(daily_limit, 1)
        self._controls["progress_text"].value = f"{applications_today} / {daily_limit} candidaturas hoje"
        self.container.update()
    
    def __getattr__(self, name):
        return getattr(self.container, name)
