"""Concept activation and associative recall."""

from aiko_memory.database import Session
from aiko_memory.models import Memory, utc_now
from aiko_memory.repository import associations_for_concept, clamp, get_memory, save_memory

ASSOCIATION_WEIGHT_BOOST_FACTOR = 0.25


def activate_concept(session: Session, concept: str) -> list[Memory]:
    """Boost memories associated with a concept and mark them recently activated."""
    activated: list[Memory] = []
    now = utc_now()
    for association in associations_for_concept(session, concept):
        memory = get_memory(session, int(association.source_id))
        if memory is None:
            continue
        memory.weight = clamp(memory.weight + association.strength * ASSOCIATION_WEIGHT_BOOST_FACTOR)
        memory.last_activated_at = now
        save_memory(session, memory)
        activated.append(memory)
    return activated
