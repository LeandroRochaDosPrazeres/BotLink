"""
BOTLink - Cognitive Automation for Job Applications

Entry point for the application.
"""

import logging
import sys

import flet as ft


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


def main(page: ft.Page) -> None:
    """Main entry point - Flet app target."""
    from src.presentation.gui.app import build_app
    build_app(page)


if __name__ == "__main__":
    setup_logging()
    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER,
        port=8553,
    )
