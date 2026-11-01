from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.models import Base


def test_migration_upgrade_downgrade_and_model_parity(tmp_path: Path, monkeypatch) -> None:
    url = f"sqlite+pysqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    try:
        command.upgrade(config, "head")
        engine = create_engine(url)
        with engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        engine.dispose()
        command.downgrade(config, "base")
        engine = create_engine(url)
        assert inspect(engine).get_table_names() == ["alembic_version"]
        engine.dispose()
        command.upgrade(config, "head")
    finally:
        get_settings.cache_clear()
