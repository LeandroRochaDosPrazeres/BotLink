"""
Theme Configuration for BOTLink GUI.

Implements FE-07: Dark and Light mode support.
"""

import flet as ft


class Theme:
    """Theme configuration for the application."""
    
    # Color palette
    PRIMARY = "#6366f1"  # Indigo
    PRIMARY_VARIANT = "#4f46e5"
    SECONDARY = "#10b981"  # Emerald
    SECONDARY_VARIANT = "#059669"
    
    ERROR = "#ef4444"  # Red
    WARNING = "#f59e0b"  # Amber
    SUCCESS = "#22c55e"  # Green
    INFO = "#3b82f6"  # Blue
    
    # Dark theme
    DARK_BG = "#0f172a"  # Slate 900
    DARK_SURFACE = "#1e293b"  # Slate 800
    DARK_CARD = "#334155"  # Slate 700
    DARK_TEXT = "#f8fafc"  # Slate 50
    DARK_TEXT_SECONDARY = "#94a3b8"  # Slate 400
    
    # Light theme
    LIGHT_BG = "#f8fafc"  # Slate 50
    LIGHT_SURFACE = "#ffffff"
    LIGHT_CARD = "#f1f5f9"  # Slate 100
    LIGHT_TEXT = "#0f172a"  # Slate 900
    LIGHT_TEXT_SECONDARY = "#64748b"  # Slate 500
    
    # Spacing
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 16
    SPACING_LG = 24
    SPACING_XL = 32
    
    # Border radius
    RADIUS_SM = 4
    RADIUS_MD = 8
    RADIUS_LG = 12
    RADIUS_XL = 16
    
    @classmethod
    def get_flet_theme(cls, dark: bool = True) -> ft.Theme:
        """Get Flet theme configuration."""
        return ft.Theme(
            color_scheme_seed=cls.PRIMARY,
            color_scheme=ft.ColorScheme(
                primary=cls.PRIMARY,
                secondary=cls.SECONDARY,
                error=cls.ERROR,
            ),
        )
    
    @classmethod
    def card_style(cls, dark: bool = True) -> dict:
        """Get card styling."""
        return {
            "bgcolor": cls.DARK_CARD if dark else cls.LIGHT_CARD,
            "border_radius": cls.RADIUS_LG,
            "padding": cls.SPACING_MD,
        }
    
    @classmethod
    def button_style(cls, variant: str = "primary") -> ft.ButtonStyle:
        """Get button styling."""
        colors = {
            "primary": cls.PRIMARY,
            "secondary": cls.SECONDARY,
            "error": cls.ERROR,
            "success": cls.SUCCESS,
        }
        return ft.ButtonStyle(
            color="white",
            bgcolor=colors.get(variant, cls.PRIMARY),
            shape=ft.RoundedRectangleBorder(radius=cls.RADIUS_MD),
            padding=ft.padding.symmetric(horizontal=cls.SPACING_LG, vertical=cls.SPACING_MD),
        )
