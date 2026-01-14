"""
Bot Orchestrator - Main workflow orchestration.

Manages the start/stop lifecycle and coordinates between components.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from src.config.settings import Settings
from src.domain.entities import Candidate
from src.domain.services import OpSecService
from src.domain.value_objects import Credentials, JobFilter
from src.infrastructure.browser import CamoufoxAdapter, CookieManager
from src.infrastructure.storage import SQLiteAdapter
from src.infrastructure.ai import OpenAIAdapter
from src.infrastructure.security import CryptoService
from src.infrastructure.parsers import ResumeParser

from .apply_to_job import ApplyToJobUseCase, ApplicationResult


logger = logging.getLogger(__name__)


class BotState(Enum):
    """Bot operational states."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class BotStatus:
    """Current bot status for display."""
    state: BotState
    applications_today: int = 0
    daily_limit: int = 50
    consecutive_errors: int = 0
    last_activity: Optional[datetime] = None
    current_job: str = ""
    message: str = ""


EventCallback = Callable[[str, dict], None]


class BotOrchestrator:
    """
    Main bot orchestrator that coordinates all components.
    
    Manages:
    - Browser lifecycle
    - AI initialization
    - Job search and application loop
    - OpSec compliance
    - Error handling and recovery
    """
    
    def __init__(self, settings: Settings) -> None:
        """
        Initialize the orchestrator.
        
        Args:
            settings: Application settings.
        """
        self.settings = settings
        
        # State
        self._state = BotState.IDLE
        self._stop_requested = False
        self._event_callbacks: list[EventCallback] = []
        
        # Candidate context
        self.candidate: Optional[Candidate] = None
        self.job_filter: Optional[JobFilter] = None
        
        # Components (lazy initialized)
        self._storage: Optional[SQLiteAdapter] = None
        self._browser: Optional[CamoufoxAdapter] = None
        self._ai: Optional[OpenAIAdapter] = None
        self._crypto: Optional[CryptoService] = None
        self._opsec: Optional[OpSecService] = None
        self._apply_use_case: Optional[ApplyToJobUseCase] = None

    @property
    def status(self) -> BotStatus:
        """Get current bot status."""
        opsec_status = self._opsec.get_status() if self._opsec else {}
        return BotStatus(
            state=self._state,
            applications_today=opsec_status.get("applications_today", 0),
            daily_limit=opsec_status.get("daily_limit", self.settings.daily_limit),
            consecutive_errors=opsec_status.get("consecutive_errors", 0),
            last_activity=datetime.now() if self._state == BotState.RUNNING else None,
        )

    def add_event_listener(self, callback: EventCallback) -> None:
        """Add an event listener for bot events."""
        self._event_callbacks.append(callback)

    def _emit_event(self, event: str, data: dict) -> None:
        """Emit an event to all listeners."""
        for callback in self._event_callbacks:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

    async def initialize(self) -> None:
        """Initialize all components."""
        self._state = BotState.STARTING
        self._emit_event("state_change", {"state": self._state.value})
        
        try:
            # Initialize storage
            self._storage = SQLiteAdapter(self.settings.database_path)
            await self._storage.initialize()
            self._emit_event("log", {"message": "Base de dados inicializada"})
            
            # Initialize crypto
            self._crypto = CryptoService(self.settings.encryption_key_path)
            self._crypto.initialize()
            self._emit_event("log", {"message": "Criptografia configurada"})
            
            # Initialize OpSec
            self._opsec = OpSecService(self.settings)
            
            # Load today's count from database
            today_count = await self._storage.get_today_count()
            self._opsec.state.applications_today = today_count
            
            # Initialize browser
            cookie_manager = CookieManager(self.settings.auth_file_path)
            self._browser = CamoufoxAdapter(self.settings, cookie_manager)
            await self._browser.start()
            self._emit_event("log", {"message": "Navegador iniciado"})
            
            # Initialize AI
            if self.settings.openai_api_key:
                self._ai = OpenAIAdapter(self.settings)
                self._ai.initialize()
                self._emit_event("log", {"message": "IA configurada"})
            else:
                self._emit_event("log", {"message": "⚠️ API Key não configurada"})
            
            # Load stored job filter
            self.job_filter = await self._storage.get_job_filter()
            
        except Exception as e:
            self._emit_event("error", {"message": str(e)})
            raise

    async def verify_session(self, credentials: Optional[Credentials] = None) -> bool:
        """Video session verification."""
        if self._state == BotState.IDLE:
            await self.initialize()
            
        return await self._ensure_logged_in(credentials)


    async def start(
        self,
        credentials: Optional[Credentials] = None,
        job_filter: Optional[JobFilter] = None,
        candidate: Optional[Candidate] = None,
    ) -> None:
        """
        Start the bot automation loop.
        
        Args:
            credentials: LinkedIn credentials (uses stored if None).
            job_filter: Job search filters.
            candidate: Candidate profile for AI context.
        """
        if self._state == BotState.RUNNING:
            return
        
        self._stop_requested = False
        
        # Initialize if needed
        if self._state == BotState.IDLE:
            await self.initialize()
        
        # Update candidate
        if candidate:
            self.candidate = candidate
        
        # Update job filter
        if job_filter:
            self.job_filter = job_filter
            if self._storage:
                await self._storage.save_job_filter(job_filter)
        
        # Handle login
        if not await self._ensure_logged_in(credentials):
            self._state = BotState.ERROR
            self._emit_event("error", {"message": "Falha no login"})
            return
        
        self._state = BotState.RUNNING
        self._emit_event("state_change", {"state": self._state.value})
        
        # Initialize apply use case
        if self._browser and self._ai and self.candidate:
            self._apply_use_case = ApplyToJobUseCase(
                browser=self._browser,
                ai=self._ai,
                candidate=self.candidate,
            )
        
        # Start main loop
        await self._run_loop()

    async def _ensure_logged_in(self, credentials: Optional[Credentials]) -> bool:
        """Ensure we're logged into LinkedIn."""
        if not self._browser:
            return False
        
        # Check if already logged in
        if await self._browser.is_logged_in():
            self._emit_event("log", {"message": "✅ Sessão ativa encontrada"})
            return True
        
        # Try to get credentials
        if not credentials and self._storage:
            credentials = await self._storage.get_credentials()
            if credentials and self._crypto:
                credentials = self._crypto.try_decrypt_credentials(credentials)
        
        if not credentials:
            self._emit_event("log", {"message": "❌ Credenciais não configuradas"})
            return False
        
        # Attempt login
        self._emit_event("log", {"message": "🔐 Fazendo login..."})
        success = await self._browser.login(credentials.username, credentials.password)
        
        if success:
            self._emit_event("log", {"message": "✅ Login bem-sucedido"})
        else:
            self._emit_event("log", {"message": "❌ Falha no login"})
        
        return success

    async def _run_loop(self) -> None:
        """Main automation loop."""
        if not self._browser or not self._opsec or not self.job_filter:
            return
        
        self._emit_event("log", {"message": "🚀 Iniciando busca de vagas..."})
        
        # Navigate to job search
        await self._browser.search_jobs(
            keywords=list(self.job_filter.keywords),
            location=self.job_filter.location,
            remote_only=self.job_filter.remote_only,
        )
        
        await asyncio.sleep(3)
        
        while not self._stop_requested:
            # Check OpSec limits
            can_apply, reason = self._opsec.can_apply()
            if not can_apply:
                self._emit_event("log", {"message": f"⏸️ {reason}"})
                
                if "Limite diário" in reason:
                    self._state = BotState.IDLE
                    self._emit_event("state_change", {"state": self._state.value})
                    break
                elif "Pausa" in reason:
                    self._state = BotState.PAUSED
                    self._emit_event("state_change", {"state": self._state.value})
                    # Wait for pause to end
                    await asyncio.sleep(60)
                    self._state = BotState.RUNNING
                    continue
                else:
                    break
            
            # Wait between applications
            await self._opsec.wait_before_application()
            
            # Here we would find and process jobs
            # For now, emit a placeholder message
            self._emit_event("log", {"message": "🔍 Buscando próxima vaga..."})
            
            await asyncio.sleep(5)  # Placeholder - would be actual job processing
            
            if self._stop_requested:
                break
        
        self._state = BotState.IDLE
        self._emit_event("state_change", {"state": self._state.value})
        self._emit_event("log", {"message": "⏹️ Bot parado"})

    async def stop(self) -> None:
        """Request graceful stop of the bot."""
        self._stop_requested = True
        self._state = BotState.STOPPING
        self._emit_event("state_change", {"state": self._state.value})
        self._emit_event("log", {"message": "⏳ Parando bot graciosamente..."})

    async def shutdown(self) -> None:
        """Shutdown all components."""
        await self.stop()
        
        if self._browser:
            await self._browser.stop()
            
        if self._storage:
            await self._storage.close()
        
        self._state = BotState.IDLE
        self._emit_event("log", {"message": "👋 Bot encerrado"})

    async def save_credentials(self, credentials: Credentials) -> None:
        """Save encrypted credentials."""
        if self._crypto and self._storage:
            encrypted = self._crypto.encrypt_credentials(credentials)
            await self._storage.save_credentials(encrypted)
            self._emit_event("log", {"message": "🔐 Credenciais salvas"})

    def load_resume(self, file_path: str) -> Optional[Candidate]:
        """Load and parse a resume file."""
        from pathlib import Path
        
        path = Path(file_path)
        if not path.exists():
            return None
        
        try:
            text = ResumeParser.extract_text(path)
            contact = ResumeParser.extract_contact_info(text)
            skills = ResumeParser.extract_skills(text)
            
            self.candidate = Candidate(
                name=contact.get("name") or "",
                email=contact.get("email") or "",
                phone=contact.get("phone") or "",
                resume_text=text,
                resume_path=path,
                skills=skills,
            )
            
            self._emit_event("log", {"message": f"📄 Currículo carregado: {path.name}"})
            return self.candidate
            
        except Exception as e:
            self._emit_event("error", {"message": f"Erro ao carregar currículo: {e}"})
            return None
