from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from models import Base, FileRecord


def _make_engine():
    db_path = Path(settings.DB_PATH)
    # Le dossier parent est un volume Docker déjà monté ; on ne crée que si absent
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


_engine = None
_SessionLocal = None


def _get_session_factory():
    global _engine, _SessionLocal
    if _SessionLocal is None:
        _engine = _make_engine()
        Base.metadata.create_all(_engine)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _SessionLocal


@contextmanager
def get_session() -> Session:
    factory = _get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def find_by_sha256(sha256: str) -> Optional[FileRecord]:
    with get_session() as session:
        return session.query(FileRecord).filter_by(sha256=sha256).first()


def find_by_slack_id(slack_file_id: str) -> Optional[FileRecord]:
    with get_session() as session:
        return session.query(FileRecord).filter_by(slack_file_id=slack_file_id).first()


def create_record(
    slack_file_id: str,
    original_name: str,
    stored_path: str,
    sha256: str,
    mime_type: str,
    file_size: int,
    uploaded_by: str,
) -> FileRecord:
    record = FileRecord(
        slack_file_id=slack_file_id,
        original_name=original_name,
        stored_path=stored_path,
        sha256=sha256,
        mime_type=mime_type,
        file_size=file_size,
        uploaded_by=uploaded_by,
    )
    with get_session() as session:
        session.add(record)
        session.flush()
        session.expunge(record)
    return record


def init_db() -> None:
    _get_session_factory()
