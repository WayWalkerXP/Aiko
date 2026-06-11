"""Time decay for memory importance and active weight."""

from aiko_memory.database import Session
from aiko_memory.models import Memory
from aiko_memory.repository import clamp, list_memories, save_memory

LOW_IMPORTANCE_DECAY_DIVISOR = 25.0
IMPORTANCE_DECAY_PER_DAY = 0.05
BASE_WEIGHT_DECAY_PER_DAY = 1.0


def decay_memory(memory: Memory, days: float) -> Memory:
    """Apply MVP decay rules to one memory."""
    weight_decay = days * (BASE_WEIGHT_DECAY_PER_DAY + ((100.0 - memory.importance) / LOW_IMPORTANCE_DECAY_DIVISOR))
    importance_decay = days * IMPORTANCE_DECAY_PER_DAY
    memory.weight = clamp(memory.weight - weight_decay)
    memory.importance = clamp(memory.importance - importance_decay)
    return memory


def apply_decay(session: Session, days: float) -> list[Memory]:
    """Apply decay to all memories in storage."""
    memories = list_memories(session)
    for memory in memories:
        save_memory(session, decay_memory(memory, days))
    return memories
