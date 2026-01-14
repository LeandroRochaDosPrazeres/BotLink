"""
BOTLink Main Application - Flet GUI

Main application window orchestrating all components.
"""

import asyncio
import flet as ft
from typing import Optional

from src.config.settings import get_settings
from src.domain.entities import Candidate
from src.domain.value_objects import Credentials, JobFilter
from src.application.use_cases import BotOrchestrator, BotState

from .components import (
    JobPanel,
    CredentialsPanel,
    ResumeUpload,
    ProfilePanel,
    ControlsPanel,
    LogDashboard,
    ThemeToggle,
)
from .styles import Theme


class BotLinkApp:
    """
    Main BOTLink application.
    
    Orchestrates all GUI components and connects to the bot orchestrator.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.orchestrator: Optional[BotOrchestrator] = None
        
        # Components
        self.job_panel: Optional[JobPanel] = None
        self.credentials_panel: Optional[CredentialsPanel] = None
        self.resume_upload: Optional[ResumeUpload] = None
        self.profile_panel: Optional[ProfilePanel] = None
        self.controls_panel: Optional[ControlsPanel] = None
        self.log_dashboard: Optional[LogDashboard] = None
        self.theme_toggle: Optional[ThemeToggle] = None
        
        # State
        self._candidate: Optional[Candidate] = None
        self._job_filter: Optional[JobFilter] = None

    async def main(self, page: ft.Page) -> None:
        """Main entry point for Flet app."""
        self.page = page
        
        # Configure page
        page.title = "BOTLink - Automação Cognitiva de Candidaturas"
        page.theme_mode = "dark"
        page.theme = Theme.get_flet_theme(dark=True)
        page.padding = Theme.SPACING_LG
        
        # Initialize orchestrator
        self.orchestrator = BotOrchestrator(self.settings)
        self.orchestrator.add_event_listener(self._on_bot_event)
        
        # Build UI
        await self._build_ui()

    async def _build_ui(self) -> None:
        """Build the main UI layout."""
        # Theme toggle
        self.theme_toggle = ThemeToggle(on_theme_change=self._on_theme_change)
        
        # Header
        header = ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Icon("smart_toy", size=32, color=Theme.PRIMARY),
                    ft.Text("BOTLink", size=28, weight="bold"),
                ]),
                self.theme_toggle.row,
            ], alignment="spaceBetween"),
            padding=Theme.SPACING_MD,
        )
        
        # Initialize components
        self.job_panel = JobPanel(on_filter_change=self._on_filter_change)
        self.credentials_panel = CredentialsPanel(
            on_credentials_save=self._on_credentials_save,
            on_verify_session=self._on_verify_session,
        )
        self.resume_upload = ResumeUpload(on_resume_loaded=self._on_resume_loaded)
        self.profile_panel = ProfilePanel(on_bio_change=self._on_bio_change)
        self.controls_panel = ControlsPanel(
            on_start=self._on_start,
            on_stop=self._on_stop,
        )
        self.log_dashboard = LogDashboard()
        
        # Build components that need page reference
        resume_container = self.resume_upload.build(self.page)
        profile_container = self.profile_panel.build(self.page)
        
        # Layout - Two columns
        left_column = ft.Column([
            self.job_panel.container,
            self.credentials_panel.container,
            self.controls_panel.container,
        ], spacing=Theme.SPACING_MD, expand=True, scroll="auto")
        
        right_column = ft.Column([
            resume_container,
            profile_container,
            self.log_dashboard.container,
        ], spacing=Theme.SPACING_MD, expand=True, scroll="auto")
        
        main_content = ft.Row([
            ft.Container(content=left_column, expand=1),
            ft.Container(content=right_column, expand=1),
        ], spacing=Theme.SPACING_LG, expand=True)

        # Add to page
        self.page.add(
            header,
            ft.Divider(),
            main_content,
        )
        
        # Log welcome message
        self.log_dashboard.add_log("👋 BOTLink iniciado. Configure suas preferências e clique em Iniciar.", "info")

    def _on_theme_change(self, is_dark: bool) -> None:
        """Handle theme change."""
        self.page.theme_mode = "dark" if is_dark else "light"
        self.page.update()

    async def _on_filter_change(self, job_filter: JobFilter) -> None:
        """Handle job filter change."""
        self._job_filter = job_filter
        if self.log_dashboard:
            keywords = ", ".join(job_filter.keywords) if job_filter.keywords else "Nenhum"
            self.log_dashboard.add_log(f"🎯 Filtros atualizados: {keywords}")

    async def _on_credentials_save(self, credentials: Credentials) -> None:
        """Handle credentials save."""
        if self.orchestrator:
            await self.orchestrator.save_credentials(credentials)
        if self.log_dashboard:
            self.log_dashboard.add_log("🔐 Credenciais salvas", "success")

    async def _on_verify_session(self) -> None:
        """Handle session verification request."""
        if self.log_dashboard:
            self.log_dashboard.add_log("🔍 Verificando sessão...")
            
        if self.orchestrator:
            try:
                # Attempt verification
                is_valid = await self.orchestrator.verify_session()
                
                # Update UI
                if self.credentials_panel:
                    self.credentials_panel.set_status(is_valid)
                
                if self.log_dashboard:
                    if is_valid:
                        self.log_dashboard.add_log("✅ Sessão verificada com sucesso!", "success")
                    else:
                        self.log_dashboard.add_log("❌ Falha na verificação da sessão", "error")
            except Exception as e:
                if self.log_dashboard:
                    self.log_dashboard.add_log(f"Erro na verificação: {e}", "error")

    def _on_resume_loaded(self, candidate: Candidate) -> None:
        """Handle resume loaded."""
        self._candidate = candidate
        if self.log_dashboard:
            self.log_dashboard.add_log(f"📄 Currículo carregado: {candidate.name}", "success")

    def _on_bio_change(self, bio: str) -> None:
        """Handle bio text change."""
        if self._candidate:
            self._candidate.bio = bio

    async def _on_start(self) -> None:
        """Handle start button click."""
        if not self._candidate:
            if self.log_dashboard:
                self.log_dashboard.add_log("⚠️ Carregue um currículo primeiro", "warning")
            return
        
        if not self._job_filter or not self._job_filter.is_configured:
            if self.log_dashboard:
                self.log_dashboard.add_log("⚠️ Configure os filtros de vagas", "warning")
            return
        
        if self.orchestrator:
            asyncio.create_task(self.orchestrator.start(
                job_filter=self._job_filter,
                candidate=self._candidate,
            ))

    async def _on_stop(self) -> None:
        """Handle stop button click."""
        if self.orchestrator:
            await self.orchestrator.stop()

    def _on_bot_event(self, event: str, data: dict) -> None:
        """Handle bot events."""
        if event == "log":
            if self.log_dashboard:
                self.log_dashboard.add_log(data.get("message", ""))
        elif event == "error":
            if self.log_dashboard:
                self.log_dashboard.add_log(data.get("message", "Erro"), "error")
        elif event == "state_change":
            state = data.get("state", "")
            is_running = state == BotState.RUNNING.value
            if self.controls_panel:
                self.controls_panel.set_running(is_running)

def run_app() -> None:
    """Run the BOTLink application."""
    app = BotLinkApp()
    ft.app(target=app.main, view=ft.AppView.WEB_BROWSER, port=8553)
