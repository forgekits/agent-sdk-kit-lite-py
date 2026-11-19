from pathlib import Path

import pytest

from agent_kit_lite.tools.notes import MAX_BODY_CHARS, NotesStore


def test_empty_store(tmp_path: Path) -> None:
    store = NotesStore(tmp_path)
    assert store.all() == []
    assert store.search("anything") == []


def test_save_and_search(tmp_path: Path) -> None:
    store = NotesStore(tmp_path)
    note = store.save("Dentist", "Appointment Tuesday 14:00", ["Health"])
    assert len(note.id) == 36
    assert note.tags == ("health",)
    assert [n.id for n in store.search("dentist")] == [note.id]
    assert [n.id for n in store.search("tuesday")] == [note.id]
    assert [n.id for n in store.search("health")] == [note.id]
    assert store.search("plumber") == []


def test_newest_first_and_limit(tmp_path: Path) -> None:
    store = NotesStore(tmp_path)
    for i in range(1, 6):
        store.save(f"n{i}", "x")
    assert [n.title for n in store.search("", 3)] == ["n5", "n4", "n3"]


def test_persists_across_instances(tmp_path: Path) -> None:
    NotesStore(tmp_path).save("a", "b")
    assert len(NotesStore(tmp_path).all()) == 1


def test_skips_damaged_lines(tmp_path: Path) -> None:
    store = NotesStore(tmp_path)
    store.save("ok", "fine")
    with store.file.open("a", encoding="utf-8") as fh:
        fh.write("{not json\n")
    store.save("also ok", "fine")
    assert [n.title for n in store.all()] == ["ok", "also ok"]


def test_rejects_long_body(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="exceeds"):
        NotesStore(tmp_path).save("big", "x" * (MAX_BODY_CHARS + 1))
