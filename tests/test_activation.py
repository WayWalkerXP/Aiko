from aiko_memory.activation import activate_concept
from aiko_memory.database import get_session
from aiko_memory.repository import add_memory, refresh_memory


def test_activate_concept_boosts_associated_memories_only(tmp_path):
    with get_session(tmp_path / "test.db") as db:
        park = add_memory(db, "Jack broke his leg in the park.", 90, 40, ["jack", "park", "injury"])
        squirrel = add_memory(db, "Aiko saw a squirrel gathering nuts.", 10, 40, ["aiko", "squirrel"])

        activated = activate_concept(db, "park")
        refresh_memory(db, park)
        refresh_memory(db, squirrel)

        assert [memory.id for memory in activated] == [park.id]
        assert park.weight == 60
        assert park.last_activated_at is not None
        assert squirrel.weight == 40
