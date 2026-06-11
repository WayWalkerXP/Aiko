"""Persistence operations for memories, associations, patterns, and opinions."""

from collections import defaultdict
import json

from aiko_memory.database import Session
from aiko_memory.models import (
    Association,
    Memory,
    Opinion,
    Pattern,
    datetime_from_db,
    datetime_to_db,
)

DEFAULT_ASSOCIATION_STRENGTH = 80.0


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """Clamp a numeric value into an inclusive range."""
    return max(minimum, min(maximum, value))


def normalize_concept(concept: str) -> str:
    """Normalize concept labels for stable matching."""
    return concept.strip().lower().replace(" ", "_")


def _memory_from_row(row) -> Memory:  # noqa: ANN001
    return Memory(
        id=row["id"],
        summary=row["summary"],
        importance=row["importance"],
        weight=row["weight"],
        created_at=datetime_from_db(row["created_at"]),
        last_activated_at=datetime_from_db(row["last_activated_at"]),
    )


def _association_from_row(row) -> Association:  # noqa: ANN001
    return Association(
        id=row["id"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        target_type=row["target_type"],
        target_id=row["target_id"],
        strength=row["strength"],
    )


def _pattern_from_row(row) -> Pattern:  # noqa: ANN001
    return Pattern(
        id=row["id"],
        description=row["description"],
        strength=row["strength"],
        evidence_memory_ids=json.loads(row["evidence_memory_ids"]),
        concept_key=row["concept_key"],
        created_at=datetime_from_db(row["created_at"]),
        updated_at=datetime_from_db(row["updated_at"]),
    )


def _opinion_from_row(row) -> Opinion:  # noqa: ANN001
    return Opinion(
        id=row["id"],
        target=row["target"],
        belief=row["belief"],
        confidence=row["confidence"],
        supporting_pattern_ids=json.loads(row["supporting_pattern_ids"]),
        opinion_key=row["opinion_key"],
        created_at=datetime_from_db(row["created_at"]),
        updated_at=datetime_from_db(row["updated_at"]),
    )


def save_memory(session: Session, memory: Memory) -> Memory:
    """Insert or update a memory."""
    if memory.id is None:
        cursor = session.execute(
            """
            INSERT INTO memory (summary, importance, weight, created_at, last_activated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                memory.summary,
                memory.importance,
                memory.weight,
                datetime_to_db(memory.created_at),
                datetime_to_db(memory.last_activated_at),
            ),
        )
        memory.id = cursor.lastrowid
    else:
        session.execute(
            """
            UPDATE memory
            SET summary = ?, importance = ?, weight = ?, created_at = ?, last_activated_at = ?
            WHERE id = ?
            """,
            (
                memory.summary,
                memory.importance,
                memory.weight,
                datetime_to_db(memory.created_at),
                datetime_to_db(memory.last_activated_at),
                memory.id,
            ),
        )
    session.commit()
    return memory


def save_pattern(session: Session, pattern: Pattern) -> Pattern:
    """Insert or update a pattern."""
    values = (
        pattern.description,
        pattern.strength,
        json.dumps(pattern.evidence_memory_ids),
        pattern.concept_key,
        datetime_to_db(pattern.created_at),
        datetime_to_db(pattern.updated_at),
    )
    if pattern.id is None:
        cursor = session.execute(
            """
            INSERT INTO pattern (description, strength, evidence_memory_ids, concept_key, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        pattern.id = cursor.lastrowid
    else:
        session.execute(
            """
            UPDATE pattern
            SET description = ?, strength = ?, evidence_memory_ids = ?, concept_key = ?, created_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (*values, pattern.id),
        )
    session.commit()
    return pattern


def save_opinion(session: Session, opinion: Opinion) -> Opinion:
    """Insert or update an opinion."""
    values = (
        opinion.target,
        opinion.belief,
        opinion.confidence,
        json.dumps(opinion.supporting_pattern_ids),
        opinion.opinion_key,
        datetime_to_db(opinion.created_at),
        datetime_to_db(opinion.updated_at),
    )
    if opinion.id is None:
        cursor = session.execute(
            """
            INSERT INTO opinion (target, belief, confidence, supporting_pattern_ids, opinion_key, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        opinion.id = cursor.lastrowid
    else:
        session.execute(
            """
            UPDATE opinion
            SET target = ?, belief = ?, confidence = ?, supporting_pattern_ids = ?, opinion_key = ?, created_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (*values, opinion.id),
        )
    session.commit()
    return opinion


def add_memory(
    session: Session,
    summary: str,
    importance: float,
    weight: float,
    tags: list[str],
    association_strength: float = DEFAULT_ASSOCIATION_STRENGTH,
) -> Memory:
    """Create a memory and concept associations for its tags."""
    memory = save_memory(session, Memory(summary=summary, importance=clamp(importance), weight=clamp(weight)))
    for tag in tags:
        concept = normalize_concept(tag)
        if concept:
            session.execute(
                """
                INSERT INTO association (source_type, source_id, target_type, target_id, strength)
                VALUES ('memory', ?, 'concept', ?, ?)
                """,
                (str(memory.id), concept, clamp(association_strength)),
            )
    session.commit()
    return memory


def list_memories(session: Session) -> list[Memory]:
    """Return memories sorted from most to least top-of-mind."""
    return [_memory_from_row(row) for row in session.execute("SELECT * FROM memory ORDER BY weight DESC, id ASC")]


def get_memory(session: Session, memory_id: int) -> Memory | None:
    """Fetch a memory by ID."""
    row = session.execute("SELECT * FROM memory WHERE id = ?", (memory_id,)).fetchone()
    return _memory_from_row(row) if row else None


def refresh_memory(session: Session, memory: Memory) -> None:
    """Refresh an in-memory object from SQLite."""
    if memory.id is None:
        return
    fresh = get_memory(session, memory.id)
    if fresh is None:
        return
    memory.summary = fresh.summary
    memory.importance = fresh.importance
    memory.weight = fresh.weight
    memory.created_at = fresh.created_at
    memory.last_activated_at = fresh.last_activated_at


def memory_concepts(session: Session, memory_id: int) -> set[str]:
    """Return all concepts associated with a memory."""
    rows = session.execute(
        """
        SELECT * FROM association
        WHERE source_type = 'memory' AND source_id = ? AND target_type = 'concept'
        """,
        (str(memory_id),),
    )
    return {row["target_id"] for row in rows}


def associations_for_concept(session: Session, concept: str) -> list[Association]:
    """Return memory associations targeting a concept."""
    rows = session.execute(
        """
        SELECT * FROM association
        WHERE source_type = 'memory' AND target_type = 'concept' AND target_id = ?
        """,
        (normalize_concept(concept),),
    )
    return [_association_from_row(row) for row in rows]


def concept_memory_map(session: Session) -> dict[str, set[int]]:
    """Map concepts to associated memory IDs."""
    mapping: dict[str, set[int]] = defaultdict(set)
    rows = session.execute("SELECT * FROM association WHERE source_type = 'memory' AND target_type = 'concept'")
    for row in rows:
        mapping[row["target_id"]].add(int(row["source_id"]))
    return dict(mapping)


def get_pattern_by_key(session: Session, concept_key: str) -> Pattern | None:
    """Fetch a pattern by concept key."""
    row = session.execute("SELECT * FROM pattern WHERE concept_key = ?", (concept_key,)).fetchone()
    return _pattern_from_row(row) if row else None


def list_patterns(session: Session) -> list[Pattern]:
    """Return patterns sorted by strength descending."""
    return [_pattern_from_row(row) for row in session.execute("SELECT * FROM pattern ORDER BY strength DESC, id ASC")]


def strong_patterns(session: Session, minimum_strength: float) -> list[Pattern]:
    """Return patterns at or above a strength threshold."""
    rows = session.execute("SELECT * FROM pattern WHERE strength >= ? ORDER BY strength DESC", (minimum_strength,))
    return [_pattern_from_row(row) for row in rows]


def get_opinion_by_key(session: Session, opinion_key: str) -> Opinion | None:
    """Fetch an opinion by key."""
    row = session.execute("SELECT * FROM opinion WHERE opinion_key = ?", (opinion_key,)).fetchone()
    return _opinion_from_row(row) if row else None


def list_opinions(session: Session) -> list[Opinion]:
    """Return opinions sorted by confidence descending."""
    return [_opinion_from_row(row) for row in session.execute("SELECT * FROM opinion ORDER BY confidence DESC, id ASC")]
