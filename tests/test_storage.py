from datetime import date

import pytest

from folder_organizer.models import FolderEntry
from folder_organizer.storage import Storage


@pytest.fixture
def storage(tmp_path):
    s = Storage(tmp_path / "data", max_snapshots=1000)
    s.ensure()
    return s


def entry(label, path=None):
    return FolderEntry(label, path or rf"D:\Projects\{label}")


def labels(entries):
    return [e.label for e in entries]


def test_ensure_creates_layout_and_never_overwrites(storage):
    assert storage.daily_dir.is_dir()
    assert storage.snapshot_dir.is_dir()
    assert storage.permanent_file.is_file()
    assert storage.state_file.is_file()
    storage.save_permanent([entry("a")], "added")
    storage.ensure()
    assert labels(storage.load_permanent()) == ["a"]


def test_day_round_trip(storage):
    d = date(2026, 10, 9)
    storage.save_day(d, [entry("a"), entry("b")])
    loaded = storage.load_day(d)
    assert [(e.label, e.path) for e in loaded] == [("a", r"D:\Projects\a"), ("b", r"D:\Projects\b")]


def test_missing_day_is_empty(storage):
    assert storage.load_day(date(2020, 1, 1)) == []


def test_list_days_ignores_empty_days(storage):
    d1, d2 = date(2026, 10, 7), date(2026, 10, 8)
    storage.save_day(d1, [entry("a")])
    storage.save_day(d2, [entry("b")])
    storage.save_day(d2, [])
    (storage.daily_dir / "notes.json").write_text("{}", encoding="utf-8")
    assert storage.list_days() == [d1]


def test_last_nonempty_day_before(storage):
    storage.save_day(date(2026, 10, 5), [entry("a")])
    storage.save_day(date(2026, 10, 7), [entry("b")])
    assert storage.last_nonempty_day_before(date(2026, 10, 9)) == date(2026, 10, 7)
    assert storage.last_nonempty_day_before(date(2026, 10, 7)) == date(2026, 10, 5)
    assert storage.last_nonempty_day_before(date(2026, 10, 5)) is None


def test_permanent_change_writes_one_snapshot(storage):
    assert storage.save_permanent([entry("a")], 'added "a"')
    snapshots = storage.list_permanent_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0].action == 'added "a"'
    assert labels(snapshots[0].entries) == ["a"]


def test_noop_save_writes_no_snapshot(storage):
    storage.save_permanent([entry("a")], "added")
    assert not storage.save_permanent([entry("a")], "nothing")
    assert len(storage.list_permanent_snapshots()) == 1


def test_rename_is_a_change(storage):
    storage.save_permanent([entry("a", r"D:\x")], "added")
    assert storage.save_permanent([entry("b", r"D:\x")], "renamed")
    assert len(storage.list_permanent_snapshots()) == 2


def test_snapshots_newest_first(storage):
    storage.save_permanent([entry("a")], "first")
    storage.save_permanent([entry("a"), entry("b")], "second")
    storage.save_permanent([entry("b")], "third")
    assert [s.action for s in storage.list_permanent_snapshots()] == ["third", "second", "first"]


def test_pruning_keeps_newest(tmp_path):
    storage = Storage(tmp_path / "data", max_snapshots=3)
    storage.ensure()
    for i in range(5):
        storage.save_permanent([entry(f"e{i}")], f"change {i}")
    assert [s.action for s in storage.list_permanent_snapshots()] == ["change 4", "change 3", "change 2"]


def test_max_snapshots_zero_keeps_all(tmp_path):
    storage = Storage(tmp_path / "data", max_snapshots=0)
    storage.ensure()
    for i in range(5):
        storage.save_permanent([entry(f"e{i}")], f"change {i}")
    assert len(storage.list_permanent_snapshots()) == 5


def test_restore_and_undo_restore(storage):
    storage.save_permanent([entry("a")], "v1")
    storage.save_permanent([entry("a"), entry("b")], "v2")
    v1, v2 = storage.list_permanent_snapshots()[1], storage.list_permanent_snapshots()[0]

    assert storage.restore_permanent(v1.snapshot_id)
    assert labels(storage.load_permanent()) == ["a"]
    snapshots = storage.list_permanent_snapshots()
    assert len(snapshots) == 3
    assert snapshots[0].action.startswith("restored version from")

    assert storage.restore_permanent(v2.snapshot_id)
    assert labels(storage.load_permanent()) == ["a", "b"]


def test_restore_unknown_snapshot(storage):
    assert not storage.restore_permanent("2000-01-01_00-00-00-000000")


def test_corrupt_permanent_falls_back_to_latest_snapshot(storage):
    storage.save_permanent([entry("a")], "added")
    storage.permanent_file.write_text("{not json", encoding="utf-8")
    assert labels(storage.load_permanent()) == ["a"]
    assert list(storage.data_dir.glob("permanent.json.corrupt-*"))


def test_invalid_entries_are_skipped(storage):
    storage.permanent_file.write_text(
        '{"entries": [{"label": "ok", "path": "D:\\\\x"}, {"label": 5}, "junk"]}', encoding="utf-8"
    )
    assert labels(storage.load_permanent()) == ["ok"]


def test_state_round_trip(storage):
    storage.save_state({"geometry": [1, 2, 3, 4], "always_on_top": True})
    assert storage.load_state() == {"geometry": [1, 2, 3, 4], "always_on_top": True}
