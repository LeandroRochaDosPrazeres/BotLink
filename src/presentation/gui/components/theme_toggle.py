"""
Theme Toggle Component - FE-07

Dark/Light mode toggle switch.
"""

import flet as ft
from typing import Callable, Optional

from ..styles import Theme


def create_theme_toggle(
    on_theme_change: Optional[Callable[[bool], None]] = None,
    initial_dark: bool = True,
) -> ft.Row:
    """
    Create theme toggle switch.
    
    Features:
    - Toggle between dark and light modes
    """
    _is_dark = initial_dark
    
    def _on_toggle(e) -> None:
        nonlocal _is_dark
        _is_dark = e.control.value
        
        if on_theme_change:
            on_theme_change(_is_dark)
    
    return ft.Row([
        ft.Icon("wb_sunny", color=Theme.WARNING),
        ft.Switch(
            value=_is_dark,
            on_change=_on_toggle,
        ),
        ft.Icon("nightlight_round", color=Theme.PRIMARY),
    ])


class ThemeToggle:
    """Wrapper class for theme toggle."""
    
    def __init__(
        self,
        on_theme_change: Optional[Callable[[bool], None]] = None,
        initial_dark: bool = True,
    ):
        self.row = create_theme_toggle(on_theme_change, initial_dark)
        self._is_dark = initial_dark
    
    @property
    def is_dark(self) -> bool:
        return self._is_dark
    
    def __getattr__(self, name):
        return getattr(self.row, name)
