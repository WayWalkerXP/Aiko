from aiko_memory.database import get_session
from aiko_memory.patterns import detect_patterns
from aiko_memory.repository import add_memory, list_patterns


def test_three_memories_sharing_two_concepts_create_sock_pattern(tmp_path):
    with get_session(tmp_path / "test.db") as db:
        add_memory(db, "Jack left socks on the floor.", 20, 70, ["jack", "socks", "laundry", "home"])
        add_memory(db, "Jack left socks beside the bed.", 20, 70, ["jack", "socks", "laundry", "home"])
        add_memory(db, "Jack left socks near the couch.", 20, 70, ["jack", "socks", "laundry", "home"])

        detected = detect_patterns(db)
        patterns = list_patterns(db)

        assert detected
        assert any(pattern.description == "Jack often leaves socks around the home." for pattern in patterns)
        assert all(len(pattern.evidence_memory_ids) >= 3 for pattern in patterns)
