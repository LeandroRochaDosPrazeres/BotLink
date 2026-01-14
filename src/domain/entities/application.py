"""
Application Entity - Represents a job application record.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ApplicationStatus(Enum):
    """Status of a job application."""
    
    SUCESSO = "SUCESSO"
    FALHA = "FALHA"
    PULADO = "PULADO"
    PENDING = "PENDING"


@dataclass
class Application:
    """
    Application entity representing a job application record.
    
    Corresponds to the `candidaturas` table in the database schema.
    
    Attributes:
        id: Database primary key (None for new applications)
        job_id: LinkedIn job ID (unique constraint)
        empresa: Company name
        titulo: Job title
        localizacao: Job location
        data_hora: Application timestamp
        status: Application status
        motivo_log: Log message (AI response, error details)
        tokens_ia: Token count for cost tracking
    """
    
    job_id: str
    empresa: str
    titulo: str
    localizacao: str
    status: ApplicationStatus
    id: Optional[int] = None
    data_hora: datetime = field(default_factory=datetime.now)
    motivo_log: str = ""
    tokens_ia: int = 0

    def __post_init__(self) -> None:
        """Validate and normalize application data."""
        if not self.job_id:
            raise ValueError("job_id is required")
        
        # Convert string status to enum if needed
        if isinstance(self.status, str):
            self.status = ApplicationStatus(self.status)

    @property
    def is_successful(self) -> bool:
        """Check if application was successful."""
        return self.status == ApplicationStatus.SUCESSO

    @property
    def is_failed(self) -> bool:
        """Check if application failed."""
        return self.status == ApplicationStatus.FALHA

    @property
    def display_status(self) -> str:
        """Human-readable status with emoji."""
        status_map = {
            ApplicationStatus.SUCESSO: "✅ Sucesso",
            ApplicationStatus.FALHA: "❌ Falha",
            ApplicationStatus.PULADO: "⏭️ Pulado",
            ApplicationStatus.PENDING: "⏳ Pendente",
        }
        return status_map.get(self.status, str(self.status.value))

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "job_id": self.job_id,
            "empresa": self.empresa,
            "titulo": self.titulo,
            "localizacao": self.localizacao,
            "data_hora": self.data_hora.isoformat(),
            "status": self.status.value,
            "motivo_log": self.motivo_log,
            "tokens_ia": self.tokens_ia,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Application":
        """Create Application from dictionary (database row)."""
        return cls(
            id=data.get("id"),
            job_id=data["job_id"],
            empresa=data["empresa"],
            titulo=data["titulo"],
            localizacao=data["localizacao"],
            data_hora=datetime.fromisoformat(data["data_hora"])
            if isinstance(data["data_hora"], str)
            else data["data_hora"],
            status=ApplicationStatus(data["status"]),
            motivo_log=data.get("motivo_log", ""),
            tokens_ia=data.get("tokens_ia", 0),
        )
