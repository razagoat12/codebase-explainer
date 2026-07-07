from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


def _run_lightweight_migrations(sync_conn) -> None:
    """Additive, idempotent column migrations for dev databases created before
    a column existed. `create_all` only creates missing *tables*, never alters
    existing ones, so a long-lived SQLite file would otherwise be missing new
    columns. Production (Postgres) should use a real migration tool; this keeps
    local dev zero-friction. `ALTER TABLE ADD COLUMN` is valid on both backends.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(sync_conn)
    existing = {table: {c["name"] for c in inspector.get_columns(table)} for table in inspector.get_table_names()}

    additive_columns = {
        "analyses": {"progress": "INTEGER NOT NULL DEFAULT 0"},
    }
    for table, columns in additive_columns.items():
        for name, ddl in columns.items():
            if table in existing and name not in existing[table]:
                sync_conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_run_lightweight_migrations)
