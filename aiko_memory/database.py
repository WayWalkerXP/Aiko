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
    last_activated_at TEXT,
    is_absorbed INTEGER NOT NULL DEFAULT 0,
    absorbed_by_pattern_id INTEGER REFERENCES pattern(id)
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
    summary TEXT NOT NULL,
    importance REAL NOT NULL,
    weight REAL NOT NULL,
    evidence_count INTEGER NOT NULL,
    concepts TEXT NOT NULL,
    tone TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    concept_key TEXT NOT NULL UNIQUE,
    evidence_memory_ids TEXT NOT NULL DEFAULT '[]'
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


def _columns(session: Session, table: str) -> set[str]:
    return {row["name"] for row in session.connection.execute(f"PRAGMA table_info({table})")}


def _add_column(session: Session, table: str, column: str, definition: str) -> None:
    if column not in _columns(session, table):
        session.connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _migrate_existing_schema(session: Session) -> None:
    """Add MVP consolidation columns to databases created by older versions."""
    _add_column(session, "memory", "is_absorbed", "INTEGER NOT NULL DEFAULT 0")
    _add_column(session, "memory", "absorbed_by_pattern_id", "INTEGER REFERENCES pattern(id)")

    pattern_columns = _columns(session, "pattern")
    if "description" in pattern_columns and "summary" not in pattern_columns:
        _add_column(session, "pattern", "summary", "TEXT NOT NULL DEFAULT ''")
        session.connection.execute("UPDATE pattern SET summary = description WHERE summary = ''")
    else:
        _add_column(session, "pattern", "summary", "TEXT NOT NULL DEFAULT ''")
    if "strength" in pattern_columns and "weight" not in _columns(session, "pattern"):
        _add_column(session, "pattern", "weight", "REAL NOT NULL DEFAULT 0")
        session.connection.execute("UPDATE pattern SET weight = strength WHERE weight = 0")
    else:
        _add_column(session, "pattern", "weight", "REAL NOT NULL DEFAULT 0")
    _add_column(session, "pattern", "importance", "REAL NOT NULL DEFAULT 25")
    _add_column(session, "pattern", "evidence_count", "INTEGER NOT NULL DEFAULT 0")
    _add_column(session, "pattern", "concepts", "TEXT NOT NULL DEFAULT '[]'")
    _add_column(session, "pattern", "tone", "TEXT NOT NULL DEFAULT ''")
    _add_column(session, "pattern", "concept_key", "TEXT NOT NULL DEFAULT ''")
    _add_column(session, "pattern", "evidence_memory_ids", "TEXT NOT NULL DEFAULT '[]'")


def init_db(session: Session) -> None:
    """Create all database tables if they do not already exist."""
    session.connection.executescript(SCHEMA)
    _migrate_existing_schema(session)
    session.commit()


def get_session(db_path: Path | str = DEFAULT_DB_PATH) -> Session:
    """Return an initialized SQLite session."""
    return Session(db_path)
