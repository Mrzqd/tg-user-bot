from __future__ import annotations

from pathlib import Path

from loguru import logger
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

_db_path = settings.database_url.split("///")[-1]
Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _col_default_sql(col) -> str:
    """Build a DEFAULT clause for a column (SQLite compatible)."""
    if col.default is not None and col.default.is_scalar:
        val = col.default.arg
        if isinstance(val, bool):
            return f" DEFAULT {1 if val else 0}"
        if isinstance(val, (int, float)):
            return f" DEFAULT {val}"
        if isinstance(val, str):
            return f" DEFAULT '{val}'"
    return " DEFAULT 0" if "INT" in str(col.type).upper() else " DEFAULT ''"


def _col_type_sql(col) -> str:
    """Map SQLAlchemy column type to SQLite type affinity."""
    t = str(col.type).upper()
    if "INT" in t or "BOOL" in t:
        return "INTEGER"
    if "CHAR" in t or "TEXT" in t or "CLOB" in t:
        return "TEXT"
    if "FLOAT" in t or "REAL" in t or "DOUBLE" in t or "NUMERIC" in t:
        return "REAL"
    if "DATETIME" in t or "TIMESTAMP" in t:
        return "DATETIME"
    return "TEXT"


def _sync_migrate(connection) -> None:
    """Compare ORM model columns against live DB tables and ALTER TABLE ADD any missing ones."""
    from database.models import Base

    Base.metadata.create_all(connection)

    insp = inspect(connection)
    for table_name, table in Base.metadata.tables.items():
        if not insp.has_table(table_name):
            continue
        existing = {c["name"] for c in insp.get_columns(table_name)}
        for col in table.columns:
            if col.name in existing:
                continue
            col_type = _col_type_sql(col)
            default = _col_default_sql(col)
            ddl = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{default}"
            connection.execute(text(ddl))
            logger.info("[Migrate] {}: added column '{}' ({}{}) ", table_name, col.name, col_type, default)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(_sync_migrate)
