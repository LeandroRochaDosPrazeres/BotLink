"""
Log Dashboard Component - FE-06

Application log display with filtering.
"""

import flet as ft
from datetime import datetime
from typing import Optional

from src.domain.entities import Application, ApplicationStatus
from ..styles import Theme


def create_log_dashboard() -> tuple[ft.Container, dict]:
    """
    Create log dashboard for application history.
    
    Features:
    - DataTable with application records
    - Console log output
    - Refresh button
    
    Returns:
        Tuple of (container, controls_dict) for external updates
    """
    _applications: list[Application] = []
    
    log_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Data/Hora")),
            ft.DataColumn(ft.Text("Empresa")),
            ft.DataColumn(ft.Text("Vaga")),
            ft.DataColumn(ft.Text("Status")),
        ],
        rows=[],
        border=ft.border.all(1, Theme.DARK_CARD),
        border_radius=Theme.RADIUS_MD,
    )
    
    logs_column = ft.Column(
        controls=[],
        scroll="auto",
        height=200,
        spacing=Theme.SPACING_XS,
    )
    
    def _on_refresh(e) -> None:
        """Refresh log data."""
        pass  # Would rebuild table
    
    container = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("📊 Log de Candidaturas", size=18, weight="bold"),
                ft.IconButton(
                    icon="refresh",
                    on_click=_on_refresh,
                    tooltip="Atualizar",
                ),
            ], alignment="spaceBetween"),
            ft.Container(
                content=log_table,
                height=150,
                border=ft.border.all(1, Theme.DARK_CARD),
                border_radius=Theme.RADIUS_MD,
            ),
            ft.Divider(),
            ft.Text("Console", size=14),
            ft.Container(
                content=logs_column,
                bgcolor=Theme.DARK_BG,
                border_radius=Theme.RADIUS_MD,
                padding=Theme.SPACING_SM,
            ),
        ], spacing=Theme.SPACING_MD),
        bgcolor=Theme.DARK_CARD,
        border_radius=Theme.RADIUS_LG,
        padding=Theme.SPACING_MD,
    )
    
    controls = {
        "log_table": log_table,
        "logs_column": logs_column,
    }
    
    return container, controls


class LogDashboard:
    """Wrapper class for log dashboard."""
    
    def __init__(self):
        self.container, self._controls = create_log_dashboard()
        self._applications: list[Application] = []
    
    def add_log(self, message: str, level: str = "info") -> None:
        """Add a log message to the console."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        colors = {
            "info": Theme.DARK_TEXT,
            "success": Theme.SUCCESS,
            "warning": Theme.WARNING,
            "error": Theme.ERROR,
        }
        
        self._controls["logs_column"].controls.append(
            ft.Text(
                f"[{timestamp}] {message}",
                size=12,
                color=colors.get(level, Theme.DARK_TEXT),
            )
        )
        
        # Keep only last 100 logs
        if len(self._controls["logs_column"].controls) > 100:
            self._controls["logs_column"].controls = self._controls["logs_column"].controls[-100:]
        
        try:
            self._controls["logs_column"].update()
        except Exception:
            pass  # May fail if not attached to page yet
    
    def set_applications(self, applications: list[Application]) -> None:
        """Update displayed applications."""
        self._applications = applications
        # Would rebuild table here
    
    def clear_logs(self) -> None:
        """Clear the console logs."""
        self._controls["logs_column"].controls = []
        try:
            self._controls["logs_column"].update()
        except Exception:
            pass
    
    def __getattr__(self, name):
        return getattr(self.container, name)
