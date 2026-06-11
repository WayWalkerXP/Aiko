from aiko_memory.database import get_session
from aiko_memory.decay import apply_decay
from aiko_memory.repository import add_memory, refresh_memory


def test_low_importance_memories_decay_faster_than_high_importance_memories(tmp_path):
    with get_session(tmp_path / "test.db") as db:
        low = add_memory(db, "Aiko saw a squirrel gathering nuts.", 10, 70, ["aiko", "squirrel"])
        high = add_memory(db, "Jack broke his leg in the park.", 90, 70, ["jack", "park", "injury"])

        apply_decay(db, days=5)
        refresh_memory(db, low)
        refresh_memory(db, high)

        assert high.weight > low.weight
        assert high.importance == 89.75
        assert low.importance == 9.75
