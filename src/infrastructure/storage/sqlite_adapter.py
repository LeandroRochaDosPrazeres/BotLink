"""
SQLite Adapter - Database operations for BOTLink.

Implements BE-07: SQLite with job_id uniqueness.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from src.domain.entities import Application, ApplicationStatus
from src.domain.value_objects import Credentials, JobFilter
from .migrations import run_migrations


class SQLiteAdapter:
    """
    SQLite database adapter for BOTLink.
    
    Provides async CRUD operations for applications, config, and statistics.
    """
    
    def __init__(self, db_path: Path) -> None:
        """
        Initialize the adapter.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialize database and run migrations."""
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Run migrations synchronously first
        run_migrations(self.db_path)
        
        # Open async connection
        self._connection = await aiosqlite.connect(str(self.db_path))
        self._connection.row_factory = aiosqlite.Row

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    @property
    def conn(self) -> aiosqlite.Connection:
        """Get the active connection or raise error."""
        if not self._connection:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._connection

    # ==================== Config Operations ====================
    
    async def get_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a config value by key."""
        cursor = await self.conn.execute(
            "SELECT value FROM config WHERE key = ?",
            (key,)
        )
        row = await cursor.fetchone()
        return row["value"] if row else default

    async def set_config(self, key: str, value: str) -> None:
        """Set a config value."""
        await self.conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value)
        )
        await self.conn.commit()

    async def get_config_json(self, key: str, default: Any = None) -> Any:
        """Get a config value as parsed JSON."""
        value = await self.get_config(key)
        if value is None:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

    async def set_config_json(self, key: str, value: Any) -> None:
        """Set a config value as JSON string."""
        await self.set_config(key, json.dumps(value))

    # ==================== Credentials Operations ====================

    async def save_credentials(self, credentials: Credentials) -> None:
        """Save encrypted credentials to config."""
        await self.set_config("linkedin_username", credentials.username)
        await self.set_config("linkedin_password", credentials.password)

    async def get_credentials(self) -> Optional[Credentials]:
        """Get stored credentials."""
        username = await self.get_config("linkedin_username")
        password = await self.get_config("linkedin_password")
        if username and password:
            return Credentials(
                username=username,
                password=password,
                is_encrypted=True,
            )
        return None

    # ==================== Job Filter Operations ====================

    async def save_job_filter(self, job_filter: JobFilter) -> None:
        """Save job filter configuration."""
        await self.set_config_json("job_filter", job_filter.to_dict())

    async def get_job_filter(self) -> Optional[JobFilter]:
        """Get stored job filter."""
        data = await self.get_config_json("job_filter")
        if data:
            return JobFilter.from_dict(data)
        return None

    # ==================== Application Operations ====================

    async def save_application(self, application: Application) -> int:
        """
        Save an application record.
        
        Returns:
            The ID of the inserted/updated record.
        """
        cursor = await self.conn.execute(
            """
            INSERT OR REPLACE INTO candidaturas 
            (job_id, empresa, titulo, localizacao, data_hora, status, motivo_log, tokens_ia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application.job_id,
                application.empresa,
                application.titulo,
                application.localizacao,
                application.data_hora.isoformat(),
                application.status.value,
                application.motivo_log,
                application.tokens_ia,
            )
        )
        await self.conn.commit()
        return cursor.lastrowid or 0

    async def get_application(self, job_id: str) -> Optional[Application]:
        """Get an application by job_id."""
        cursor = await self.conn.execute(
            "SELECT * FROM candidaturas WHERE job_id = ?",
            (job_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Application.from_dict(dict(row))
        return None

    async def job_already_applied(self, job_id: str) -> bool:
        """Check if we've already applied to a job."""
        cursor = await self.conn.execute(
            "SELECT 1 FROM candidaturas WHERE job_id = ?",
            (job_id,)
        )
        return await cursor.fetchone() is not None

    async def get_applications(
        self,
        limit: int = 100,
        status: Optional[ApplicationStatus] = None,
        since: Optional[datetime] = None,
    ) -> list[Application]:
        """Get application records with optional filters."""
        query = "SELECT * FROM candidaturas WHERE 1=1"
        params: list[Any] = []
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
            
        if since:
            query += " AND data_hora >= ?"
            params.append(since.isoformat())
            
        query += " ORDER BY data_hora DESC LIMIT ?"
        params.append(limit)
        
        cursor = await self.conn.execute(query, params)
        rows = await cursor.fetchall()
        return [Application.from_dict(dict(row)) for row in rows]

    async def get_today_count(self) -> int:
        """Get count of applications made today."""
        today = date.today().isoformat()
        cursor = await self.conn.execute(
            "SELECT COUNT(*) FROM candidaturas WHERE DATE(data_hora) = ?",
            (today,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    # ==================== Statistics Operations ====================

    async def increment_daily_stats(self, dt: Optional[date] = None) -> None:
        """Increment the daily application counter."""
        target_date = (dt or date.today()).isoformat()
        await self.conn.execute(
            """
            INSERT INTO estatisticas_diarias (data, quantidade)
            VALUES (?, 1)
            ON CONFLICT(data) DO UPDATE SET quantidade = quantidade + 1
            """,
            (target_date,)
        )
        await self.conn.commit()

    async def get_daily_stats(self, dt: Optional[date] = None) -> int:
        """Get application count for a specific day."""
        target_date = (dt or date.today()).isoformat()
        cursor = await self.conn.execute(
            "SELECT quantidade FROM estatisticas_diarias WHERE data = ?",
            (target_date,)
        )
        row = await cursor.fetchone()
        return row["quantidade"] if row else 0

    async def get_stats_range(
        self,
        start: date,
        end: date,
    ) -> list[dict]:
        """Get statistics for a date range."""
        cursor = await self.conn.execute(
            """
            SELECT data, quantidade 
            FROM estatisticas_diarias 
            WHERE data BETWEEN ? AND ?
            ORDER BY data
            """,
            (start.isoformat(), end.isoformat())
        )
        rows = await cursor.fetchall()
        return [{"date": row["data"], "count": row["quantidade"]} for row in rows]
