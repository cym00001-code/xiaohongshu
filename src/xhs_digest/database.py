"""Database engine and session helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from xhs_digest.models import Base


def make_engine(database_url: str, *, echo: bool = False, pool_pre_ping: bool = True) -> Engine:
    """Create a SQLAlchemy engine for the configured database URL."""

    return create_engine(database_url, echo=echo, pool_pre_ping=pool_pre_ping, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a SQLAlchemy 2.x session factory."""

    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def create_all(engine: Engine) -> None:
    """Create all digest storage tables."""

    Base.metadata.create_all(engine)


def create_tables(engine: Engine) -> None:
    """Compatibility wrapper used by CLI and scheduled jobs."""

    create_all(engine)


def create_engine_and_session(database_url: str, *, echo: bool = False) -> tuple[Engine, sessionmaker[Session]]:
    """Create an engine and session factory in one step."""

    engine = make_engine(database_url, echo=echo)
    return engine, make_session_factory(engine)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional session scope."""

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def open_session(database_url: str, *, echo: bool = False, create_schema: bool = False) -> Iterator[Session]:
    """Open a one-off session for scripts and jobs."""

    engine = make_engine(database_url, echo=echo)
    if create_schema:
        create_all(engine)
    session_factory = make_session_factory(engine)
    return session_scope(session_factory)
