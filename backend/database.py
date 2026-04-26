from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import PROJECT_ROOT, ensure_project_directories, get_settings


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///./"):
        relative = settings.database_url.replace("sqlite:///./", "", 1)
        return f"sqlite:///{(PROJECT_ROOT / relative).as_posix()}"
    return settings.database_url


ensure_project_directories()
engine = create_engine(
    _database_url(),
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def init_db() -> None:
    from backend.models import business_models, forecast_models, weather_models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
