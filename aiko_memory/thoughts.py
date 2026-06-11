"""Current active thought selection."""

from dataclasses import dataclass

from aiko_memory.database import Session
from aiko_memory.models import Memory, Opinion, Pattern
from aiko_memory.repository import list_memories, list_opinions, list_patterns


@dataclass(frozen=True)
class CurrentThoughts:
    """Top items currently on Aiko's mind."""

    memories: list[Memory]
    patterns: list[Pattern]
    opinions: list[Opinion]


def current_thoughts(session: Session, limit: int = 3, include_absorbed: bool = False) -> CurrentThoughts:
    """Return top memories, patterns, and opinions for display."""
    return CurrentThoughts(
        memories=list_memories(session, include_absorbed=include_absorbed)[:limit],
        patterns=list_patterns(session)[:limit],
        opinions=list_opinions(session)[:limit],
    )
