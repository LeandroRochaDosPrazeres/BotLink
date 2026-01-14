"""
Job Panel Component - FE-01

Job search configuration with tags, location, and filters.
"""

import flet as ft
from typing import Callable, Optional

from src.domain.value_objects import JobFilter
from ..styles import Theme


def create_job_panel(
    on_filter_change: Optional[Callable[[JobFilter], None]] = None,
    initial_filter: Optional[JobFilter] = None,
) -> ft.Container:
    """
    Create job search configuration panel.
    
    Features:
    - Multiple keyword tags input
    - Location input
    - Remote only checkbox
    """
    _filter = initial_filter or JobFilter()
    _keywords: list[str] = list(_filter.keywords)
    _location = _filter.location
    _remote_only = _filter.remote_only
    
    keywords_row = ft.Row(controls=[], wrap=True, spacing=Theme.SPACING_SM)
    
    def _build_keyword_chips() -> list[ft.Chip]:
        """Build keyword chip controls."""
        return [
            ft.Chip(
                label=ft.Text(kw),
                on_delete=lambda e, k=kw: _remove_keyword(k),
            )
            for kw in _keywords
        ]
    
    def _emit_change() -> None:
        """Emit filter change event."""
        if on_filter_change:
            job_filter = JobFilter(
                keywords=tuple(_keywords),
                location=_location,
                remote_only=_remote_only,
            )
            on_filter_change(job_filter)
    
    def _add_keyword(e) -> None:
        """Add a keyword tag."""
        nonlocal _keywords
        keyword = keyword_input.value.strip() if keyword_input.value else ""
        if keyword and keyword not in _keywords:
            _keywords.append(keyword)
            keyword_input.value = ""
            keywords_row.controls = _build_keyword_chips()
            _emit_change()
            keyword_input.update()
            keywords_row.update()
    
    def _remove_keyword(keyword: str) -> None:
        """Remove a keyword tag."""
        nonlocal _keywords
        if keyword in _keywords:
            _keywords.remove(keyword)
            keywords_row.controls = _build_keyword_chips()
            _emit_change()
            keywords_row.update()
    
    def _on_location_change(e) -> None:
        """Handle location change."""
        nonlocal _location
        _location = e.control.value or ""
        _emit_change()
    
    def _on_remote_change(e) -> None:
        """Handle remote checkbox change."""
        nonlocal _remote_only
        _remote_only = e.control.value
        _emit_change()
    
    keyword_input = ft.TextField(
        label="Adicionar cargo/palavra-chave",
        hint_text="Ex: Backend Python, DevOps",
        border_radius=Theme.RADIUS_MD,
        on_submit=_add_keyword,
        suffix=ft.IconButton(
            icon="add",
            on_click=_add_keyword,
        ),
    )
    
    keywords_row.controls = _build_keyword_chips()
    
    location_input = ft.TextField(
        label="Localização",
        hint_text="Ex: São Paulo, SP, Brasil",
        value=_location,
        border_radius=Theme.RADIUS_MD,
        on_change=_on_location_change,
    )
    
    remote_checkbox = ft.Checkbox(
        label="Apenas vagas remotas",
        value=_remote_only,
        on_change=_on_remote_change,
    )
    
    return ft.Container(
        content=ft.Column([
            ft.Text("🎯 Configuração de Vagas", size=18, weight="bold"),
            keyword_input,
            keywords_row,
            location_input,
            remote_checkbox,
        ], spacing=Theme.SPACING_MD),
        bgcolor=Theme.DARK_CARD,
        border_radius=Theme.RADIUS_LG,
        padding=Theme.SPACING_MD,
    )


# For backward compatibility
class JobPanel:
    """Wrapper class for job panel."""
    
    def __init__(
        self,
        on_filter_change: Optional[Callable[[JobFilter], None]] = None,
        initial_filter: Optional[JobFilter] = None,
    ):
        self.container = create_job_panel(on_filter_change, initial_filter)
    
    def __getattr__(self, name):
        return getattr(self.container, name)
