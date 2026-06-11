from types import SimpleNamespace

import pytest

from aiko_memory import cli
from aiko_memory.activation import activate_concept
from aiko_memory.database import get_session
from aiko_memory.patterns import detect_patterns
from aiko_memory.repository import list_patterns


@pytest.mark.parametrize(
    "tag_args",
    [
        ["--tags", "jack", "socks", "laundry", "home"],
        ["--tags", "jack", "--tags", "socks", "--tags", "laundry", "--tags", "home"],
    ],
)
def test_main_flattens_supported_tag_forms_before_adding_memory(tmp_path, monkeypatch, capsys, tag_args):
    captured_tags = None

    def fake_add_memory(session, summary, importance, weight, tags):  # noqa: ANN001
        nonlocal captured_tags
        captured_tags = tags
        return SimpleNamespace(id=1, summary=summary)

    monkeypatch.setattr(cli, "add_memory", fake_add_memory)

    cli.main(["--db", str(tmp_path / "test.db"), "add", "Jack left socks on the floor.", *tag_args])

    assert captured_tags == ["jack", "socks", "laundry", "home"]
    assert "Added memory #1" in capsys.readouterr().out


def test_main_preserves_empty_tags_default(tmp_path, monkeypatch):
    captured_tags = None

    def fake_add_memory(session, summary, importance, weight, tags):  # noqa: ANN001
        nonlocal captured_tags
        captured_tags = tags
        return SimpleNamespace(id=1, summary=summary)

    monkeypatch.setattr(cli, "add_memory", fake_add_memory)

    cli.main(["--db", str(tmp_path / "test.db"), "add", "A tagless memory."])

    assert captured_tags == []


def test_repeated_tags_readme_commands_activate_and_detect_patterns(tmp_path, capsys):
    db_path = tmp_path / "test.db"
    base_args = ["--db", str(db_path), "add"]
    repeated_tags = ["--tags", "jack", "--tags", "socks", "--tags", "laundry", "--tags", "home"]

    cli.main([*base_args, "Jack left socks on the floor.", "--importance", "20", "--weight", "70", *repeated_tags])
    cli.main([*base_args, "Jack left socks beside the bed.", "--importance", "20", "--weight", "70", *repeated_tags])
    cli.main([*base_args, "Jack left socks near the couch.", "--importance", "20", "--weight", "70", *repeated_tags])
    capsys.readouterr()

    with get_session(db_path) as db:
        activated = activate_concept(db, "socks")
        detected = detect_patterns(db)
        patterns = list_patterns(db)

    assert len(activated) == 3
    assert detected
    assert any(pattern.summary == "Jack often leaves socks around the home." for pattern in patterns)
