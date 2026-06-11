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


def test_single_behavior_type_keeps_concrete_trash_summary(tmp_path):
    with get_session(tmp_path / "test.db") as db:
        add_memory(db, "Jack forgot the kitchen trash.", 20, 70, ["jack", "trash", "kitchen"])
        add_memory(db, "Jack left the bathroom trash full.", 20, 70, ["jack", "trash", "bathroom"])
        add_memory(db, "Jack forgot the garage trash again.", 20, 70, ["jack", "trash", "garage"])

        detect_patterns(db)
        patterns = list_patterns(db)

        assert any(pattern.description == "Jack sometimes leaves trash unattended." for pattern in patterns)
        assert all("household chores" not in pattern.description for pattern in patterns)


def test_broader_household_summary_requires_different_behavior_types(tmp_path):
    with get_session(tmp_path / "test.db") as db:
        add_memory(db, "Jack left socks on the floor.", 20, 70, ["jack", "household", "socks"])
        add_memory(db, "Jack left dishes in the sink.", 20, 70, ["jack", "household", "dishes"])
        add_memory(db, "Jack forgot the trash by the door.", 20, 70, ["jack", "household", "trash"])

        detect_patterns(db)
        patterns = list_patterns(db)

        assert any(
            pattern.description == "Jack repeatedly leaves household tasks unfinished, including socks, dishes, and trash."
            for pattern in patterns
        )
