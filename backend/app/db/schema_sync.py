"""Add new *nullable* columns to existing tables at startup.

``Base.metadata.create_all`` creates missing tables but never alters existing ones, so a new
column on an existing model would break older databases. This adds such columns (nullable,
no server default) with ``ALTER TABLE ... ADD COLUMN``. It never drops, renames or changes
columns - anything beyond additive changes still needs an Alembic migration.
"""

from loguru import logger
from sqlalchemy import Engine, inspect, text

from app.db.base import Base


def add_missing_columns(engine: Engine) -> list[str]:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    added: list[str] = []
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # create_all handles new tables
            present = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in present:
                    continue
                if not column.nullable or column.primary_key:
                    logger.warning("Column {}.{} is NOT NULL - needs an Alembic migration", table.name, column.name)
                    continue
                ddl_type = column.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {ddl_type}'))
                added.append(f"{table.name}.{column.name}")
    if added:
        logger.info("Schema sync added columns: {}", ", ".join(added))
    return added
