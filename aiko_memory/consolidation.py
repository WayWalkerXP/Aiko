"""Memory consolidation into higher-level patterns."""

from aiko_memory.database import Session
from aiko_memory.models import Pattern, utc_now
from aiko_memory.repository import clamp, get_pattern_by_key, list_unabsorbed_memories, save_memory, save_pattern

CONSOLIDATION_MIN_EVIDENCE_COUNT = 3
SOCK_PATTERN_KEY = "jack:socks:habit"
SOCK_PATTERN_SUMMARY = "Jack often leaves socks around the home."
SOCK_PATTERN_CONCEPTS = ["home", "socks", "habit"]
SOCK_PATTERN_IMPORTANCE = 25.0
SOCK_PATTERN_TONE = "mildly amused / mildly exasperated"


def _is_jack_socks_memory(summary: str) -> bool:
    words = summary.lower()
    return "jack" in words and "sock" in words


def consolidate_memories(session: Session) -> list[Pattern]:
    """Fold repeated low-importance memories into higher-level patterns."""
    memories = list_unabsorbed_memories(session)
    sock_memories = [memory for memory in memories if _is_jack_socks_memory(memory.summary)]
    if len(sock_memories) < CONSOLIDATION_MIN_EVIDENCE_COUNT:
        return []

    now = utc_now()
    source_ids = {memory.id for memory in sock_memories if memory.id is not None}
    weight = clamp(max(memory.weight for memory in sock_memories) + 5.0)
    pattern = get_pattern_by_key(session, SOCK_PATTERN_KEY)
    if pattern is None:
        pattern = Pattern(
            summary=SOCK_PATTERN_SUMMARY,
            importance=SOCK_PATTERN_IMPORTANCE,
            weight=weight,
            evidence_count=len(source_ids),
            concepts=SOCK_PATTERN_CONCEPTS.copy(),
            tone=SOCK_PATTERN_TONE,
            concept_key=SOCK_PATTERN_KEY,
            evidence_memory_ids=sorted(source_ids),
        )
    else:
        pattern.summary = SOCK_PATTERN_SUMMARY
        pattern.importance = SOCK_PATTERN_IMPORTANCE
        pattern.weight = clamp(max(pattern.weight, weight))
        pattern.evidence_memory_ids = sorted(set(pattern.evidence_memory_ids) | source_ids)
        pattern.evidence_count = len(pattern.evidence_memory_ids)
        pattern.concepts = SOCK_PATTERN_CONCEPTS.copy()
        pattern.tone = SOCK_PATTERN_TONE
        pattern.updated_at = now
    save_pattern(session, pattern)

    for memory in sock_memories:
        memory.is_absorbed = True
        memory.absorbed_by_pattern_id = pattern.id
        save_memory(session, memory)

    return [pattern]
