from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)

if settings.database_url.startswith("sqlite"):
    # Unlike Postgres (used in production), SQLite does not enforce foreign
    # key constraints by default -- without this, "restrict delete" routes
    # (e.g. deleting a Trinn that still has classes) would silently succeed
    # and leave orphaned rows instead of raising the IntegrityError those
    # routes rely on.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):  # noqa: ANN001, ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
