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
    is_absorbed: bool = False
    absorbed_by_pattern_id: int | None = None


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
    """A higher-level recurring behavior or theme detected from memories."""

    summary: str
    importance: float
    weight: float
    evidence_count: int
    concepts: list[str]
    tone: str
    id: int | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    concept_key: str = ""
    evidence_memory_ids: list[int] = field(default_factory=list)

    @property
    def description(self) -> str:
        """Backward-compatible label used by existing pattern/opinion code."""
        return self.summary

    @description.setter
    def description(self, value: str) -> None:
        self.summary = value

    @property
    def strength(self) -> float:
        """Backward-compatible strength used by existing pattern/opinion code."""
        return self.weight

    @strength.setter
    def strength(self, value: float) -> None:
        self.weight = value


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
