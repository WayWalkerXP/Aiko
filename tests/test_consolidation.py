from aiko_memory.consolidation import consolidate_memories
from aiko_memory.database import get_session
from aiko_memory.repository import add_memory, list_memories, list_patterns, refresh_memory
from aiko_memory.thoughts import current_thoughts


def test_three_sock_memories_consolidate_into_one_pattern(tmp_path):
    with get_session(tmp_path / "test.db") as db:
        add_memory(db, "Jack left socks on the floor.", 20, 70, ["jack", "socks", "laundry", "home"])
        add_memory(db, "Jack left socks beside the bed.", 20, 75, ["jack", "socks", "laundry", "home"])
        add_memory(db, "Jack left socks near the couch.", 20, 90, ["jack", "socks", "laundry", "home"])

        consolidated = consolidate_memories(db)
        patterns = list_patterns(db)

        assert len(consolidated) == 1
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.summary == "Jack often leaves socks around the home."
        assert pattern.importance == 25
        assert pattern.weight == 95
        assert pattern.evidence_count == 3
        assert pattern.concepts == ["home", "socks", "habit"]
        assert pattern.tone == "mildly amused / mildly exasperated"


def test_source_memories_are_marked_absorbed(tmp_path):
    with get_session(tmp_path / "test.db") as db:
        memories = [
            add_memory(db, "Jack left socks on the floor.", 20, 70, ["jack", "socks"]),
            add_memory(db, "Jack left socks beside the bed.", 20, 70, ["jack", "socks"]),
            add_memory(db, "Jack left socks near the couch.", 20, 70, ["jack", "socks"]),
        ]

        pattern = consolidate_memories(db)[0]
        for memory in memories:
            refresh_memory(db, memory)
            assert memory.is_absorbed is True
            assert memory.absorbed_by_pattern_id == pattern.id


def test_absorbed_memories_are_excluded_from_normal_thoughts_but_pattern_appears(tmp_path):
    with get_session(tmp_path / "test.db") as db:
        add_memory(db, "Jack left socks on the floor.", 20, 70, ["jack", "socks"])
        add_memory(db, "Jack left socks beside the bed.", 20, 70, ["jack", "socks"])
        add_memory(db, "Jack left socks near the couch.", 20, 70, ["jack", "socks"])

        consolidate_memories(db)
        thoughts = current_thoughts(db)
        all_memories = list_memories(db, include_absorbed=True)

        assert thoughts.memories == []
        assert len(all_memories) == 3
        assert all(memory.is_absorbed for memory in all_memories)
        assert any(pattern.summary == "Jack often leaves socks around the home." for pattern in thoughts.patterns)


def test_high_importance_one_off_memory_does_not_get_absorbed(tmp_path):
    with get_session(tmp_path / "test.db") as db:
        injury = add_memory(db, "Jack broke his leg.", 95, 100, ["jack", "injury"])
        add_memory(db, "Jack left socks on the floor.", 20, 70, ["jack", "socks"])
        add_memory(db, "Jack left socks beside the bed.", 20, 70, ["jack", "socks"])
        add_memory(db, "Jack left socks near the couch.", 20, 70, ["jack", "socks"])

        consolidate_memories(db)
        refresh_memory(db, injury)
        thoughts = current_thoughts(db)

        assert injury.is_absorbed is False
        assert injury in thoughts.memories
