from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    """마이그레이션 도구 없음 — 앱 기동 시 테이블을 만든다 (구현계획 §7)."""
    from . import models  # noqa: F401  (모델 등록용 import)

    models.Base.metadata.create_all(bind=engine)
