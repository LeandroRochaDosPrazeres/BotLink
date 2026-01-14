"""
Database Migrations - Schema setup and versioning.

Implements the schema defined in PRD Section 7.
"""

import sqlite3
from pathlib import Path
from typing import Optional


SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- Configuration key-value store
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Job applications log (candidaturas)
CREATE TABLE IF NOT EXISTS candidaturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE,
    empresa TEXT,
    titulo TEXT,
    localizacao TEXT,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK(status IN ('SUCESSO', 'FALHA', 'PULADO', 'PENDING')),
    motivo_log TEXT,
    tokens_ia INTEGER DEFAULT 0
);

-- Daily statistics
CREATE TABLE IF NOT EXISTS estatisticas_diarias (
    data DATE PRIMARY KEY,
    quantidade INTEGER DEFAULT 0
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_candidaturas_job_id ON candidaturas(job_id);
CREATE INDEX IF NOT EXISTS idx_candidaturas_status ON candidaturas(status);
CREATE INDEX IF NOT EXISTS idx_candidaturas_data_hora ON candidaturas(data_hora);
"""


def run_migrations(db_path: Path, conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Run database migrations to ensure schema is up to date.
    
    Args:
        db_path: Path to the SQLite database file.
        conn: Optional existing connection to use.
    """
    should_close = conn is None
    if conn is None:
        conn = sqlite3.connect(str(db_path))
    
    try:
        cursor = conn.cursor()
        
        # Check current version
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        version_table_exists = cursor.fetchone() is not None
        
        current_version = 0
        if version_table_exists:
            cursor.execute("SELECT MAX(version) FROM schema_version")
            row = cursor.fetchone()
            current_version = row[0] if row and row[0] else 0
        
        # Run migrations if needed
        if current_version < SCHEMA_VERSION:
            cursor.executescript(SCHEMA_SQL)
            
            # Record new version
            cursor.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,)
            )
            conn.commit()
            
    finally:
        if should_close:
            conn.close()


async def run_migrations_async(db_path: Path) -> None:
    """
    Async version of run_migrations for use with aiosqlite.
    
    Args:
        db_path: Path to the SQLite database file.
    """
    import aiosqlite
    
    async with aiosqlite.connect(str(db_path)) as db:
        # Check current version
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        version_table_exists = await cursor.fetchone() is not None
        
        current_version = 0
        if version_table_exists:
            cursor = await db.execute("SELECT MAX(version) FROM schema_version")
            row = await cursor.fetchone()
            current_version = row[0] if row and row[0] else 0
        
        # Run migrations if needed
        if current_version < SCHEMA_VERSION:
            await db.executescript(SCHEMA_SQL)
            
            # Record new version
            await db.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,)
            )
            await db.commit()
