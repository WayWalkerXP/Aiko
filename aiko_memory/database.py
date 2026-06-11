"""SQLite database setup helpers."""

from pathlib import Path
import sqlite3
from types import TracebackType

DEFAULT_DB_PATH = Path("aiko_memory.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary TEXT NOT NULL,
    importance REAL NOT NULL,
    weight REAL NOT NULL,
    created_at TEXT NOT NULL,
    last_activated_at TEXT
);
CREATE TABLE IF NOT EXISTS association (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    strength REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS pattern (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    strength REAL NOT NULL,
    evidence_memory_ids TEXT NOT NULL,
    concept_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS opinion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    belief TEXT NOT NULL,
    confidence REAL NOT NULL,
    supporting_pattern_ids TEXT NOT NULL,
    opinion_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class Session:
    """Tiny sqlite3 session wrapper used by the MVP repositories."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.connection = sqlite3.connect(str(db_path))
        self.connection.row_factory = sqlite3.Row
        init_db(self)

    def execute(self, sql: str, parameters: tuple = ()):  # noqa: ANN001
        return self.connection.execute(sql, parameters)

    def commit(self) -> None:
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Session":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is None:
            self.commit()
        self.close()


def init_db(session: Session) -> None:
    """Create all database tables if they do not already exist."""
    session.connection.executescript(SCHEMA)
    session.commit()


def get_session(db_path: Path | str = DEFAULT_DB_PATH) -> Session:
    """Return an initialized SQLite session."""
    return Session(db_path)
