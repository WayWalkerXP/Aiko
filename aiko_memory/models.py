"""Data models for the Aiko memory engine."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def datetime_to_db(value: datetime | None) -> str | None:
    """Serialize datetimes for SQLite."""
    return value.isoformat() if value else None


def datetime_from_db(value: str | None) -> datetime | None:
    """Deserialize datetimes from SQLite."""
    return datetime.fromisoformat(value) if value else None


@dataclass
class Memory:
    """A specific remembered experience."""

    summary: str
    importance: float
    weight: float
    id: int | None = None
    created_at: datetime = field(default_factory=utc_now)
    last_activated_at: datetime | None = None


@dataclass
class Association:
    """A directed link from a memory/concept/pattern/opinion to another node."""

    source_type: str
    source_id: str
    target_type: str
    target_id: str
    strength: float
    id: int | None = None


@dataclass
class Pattern:
    """A recurring behavior or theme detected from memories."""

    description: str
    strength: float
    evidence_memory_ids: list[int]
    concept_key: str
    id: int | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class Opinion:
    """A subjective belief formed from one or more patterns."""

    target: str
    belief: str
    confidence: float
    supporting_pattern_ids: list[int]
    opinion_key: str
    id: int | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
