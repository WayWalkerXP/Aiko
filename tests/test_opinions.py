from aiko_memory.database import get_session
from aiko_memory.opinions import generate_opinions
from aiko_memory.patterns import detect_patterns
from aiko_memory.repository import add_memory, list_opinions


def test_sock_pattern_creates_jack_laundry_opinion(tmp_path):
    with get_session(tmp_path / "test.db") as db:
        add_memory(db, "Jack left socks on the floor.", 20, 70, ["jack", "socks", "laundry", "home"])
        add_memory(db, "Jack left socks beside the bed.", 20, 70, ["jack", "socks", "laundry", "home"])
        add_memory(db, "Jack left socks near the couch.", 20, 70, ["jack", "socks", "laundry", "home"])

        detect_patterns(db)
        generated = generate_opinions(db)
        opinions = list_opinions(db)

        assert generated
        assert any(opinion.target == "Jack" and "laundry" in opinion.belief for opinion in opinions)
        assert max(opinion.confidence for opinion in opinions) >= 50
