"""
BOTLink - Cognitive Automation for Job Applications

Entry point for the application.
"""

import logging
import sys

from src.presentation.gui import BotLinkApp
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


def main() -> None:
    """Main entry point."""
    setup_logging()
    
    app = BotLinkApp()
    # Run in web browser mode for localhost testing
    ft.app(target=app.main, view=ft.AppView.WEB_BROWSER, port=8553)


if __name__ == "__main__":
    main()
