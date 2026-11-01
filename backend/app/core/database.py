"""Session ownership and portable test engine construction."""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    url = settings.database_url.get_secret_value()
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection: object, _: object) -> None:
            # DBAPI connection type differs by driver.
            connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

        return engine
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=10,
        connect_args={
            "connect_timeout": max(1, int(settings.health_timeout_seconds)),
            "options": "-c statement_timeout=10000",
        },
        hide_parameters=True,
    )


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """A request owns its transaction; uncommitted writes are rolled back on exit."""
    with factory() as session:
        yield session
