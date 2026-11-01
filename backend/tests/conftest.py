import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

os.environ["APP_ENV"] = "test"

from app.core.config import Settings  # noqa: E402
from app.core.database import build_engine  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, app_env="test", database_url="sqlite+pysqlite:///:memory:")


@pytest.fixture
def engine(settings: Settings) -> Iterator[Engine]:
    engine = build_engine(settings)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session
