"""Offscreen smoke tests for the widget (no clicking, but real Qt objects)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import date, datetime  # noqa: E402

import pytest  # noqa: E402

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from folder_organizer import paths  # noqa: E402
from folder_organizer.config import load_settings  # noqa: E402
from folder_organizer.models import FolderEntry  # noqa: E402
from folder_organizer.storage import Storage  # noqa: E402
from folder_organizer.ui.main_widget import MainWidget  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def make_widget(tmp_path, qapp):
    widgets = []

    def make(clock, settings_text=None):
        settings_file = tmp_path / "settings.toml"
        if settings_text:
            settings_file.write_text(settings_text, encoding="utf-8")
        settings, _ = load_settings(settings_file, paths.DEFAULT_SETTINGS_FILE, tmp_path)
        storage = Storage(settings.data_dir, settings.max_snapshots)
        storage.ensure()
        widget = MainWidget(settings, storage, clock=clock)
        widgets.append(widget)
        return widget, storage

    yield make
    for w in widgets:
        w.close()
        w.deleteLater()


@pytest.fixture
def folder(tmp_path):
    f = tmp_path / "ProjectA" / "renders"
    f.mkdir(parents=True)
    return str(f)


def test_permanent_changes_are_saved_with_history(make_widget, folder):
    w, storage = make_widget(lambda: datetime(2026, 10, 9, 12, 0))
    assert w.permanent.accept_entry(FolderEntry("A renders", folder), 'added "A renders"')
    assert [e.label for e in storage.load_permanent()] == ["A renders"]
    assert storage.list_permanent_snapshots()[0].action == 'added "A renders"'
    assert not w.permanent.accept_entry(FolderEntry("dup", folder), "added")  # same path twice


def test_daily_changes_are_saved_for_today(make_widget, folder):
    w, storage = make_widget(lambda: datetime(2026, 10, 9, 12, 0))
    w.daily.accept_entry(FolderEntry("today", folder), "added")
    assert [e.label for e in storage.load_day(date(2026, 10, 9))] == ["today"]


def test_rollover_and_load_previous_day(make_widget, folder):
    now = [datetime(2026, 10, 9, 12, 0)]
    w, storage = make_widget(lambda: now[0])
    w.daily.accept_entry(FolderEntry("x", folder), "added")

    now[0] = datetime(2026, 10, 10, 3, 59)
    w.check_day()
    assert w.today == date(2026, 10, 9)

    now[0] = datetime(2026, 10, 10, 4, 0)
    w.check_day()
    assert w.today == w.viewed_day == date(2026, 10, 10)
    assert w.daily.entries() == []
    assert not w.daily.notice_button.isHidden()
    assert "2026-10-09" in w.daily.notice_button.text()

    w.daily.notice_button.click()
    assert [e.label for e in storage.load_day(date(2026, 10, 10))] == ["x"]
    assert w.daily.notice_button.isHidden()


def test_viewing_past_day_stays_after_rollover(make_widget, folder):
    now = [datetime(2026, 10, 9, 12, 0)]
    w, storage = make_widget(lambda: now[0])
    storage.save_day(date(2026, 10, 5), [FolderEntry("old", folder)])
    w.show_day(date(2026, 10, 5))
    assert [e.label for e in w.daily.entries()] == ["old"]
    assert w.daily.notice_button.text() == "Copy this day to today"

    now[0] = datetime(2026, 10, 10, 5, 0)
    w.check_day()
    assert w.viewed_day == date(2026, 10, 5)


def test_move_between_sections(make_widget, folder):
    w, storage = make_widget(lambda: datetime(2026, 10, 9, 12, 0))
    w.permanent.accept_entry(FolderEntry("A renders", folder), "added")
    entry = w.permanent.entries()[0]
    w._move(w.permanent._entries[0], w.permanent, w.daily)
    assert storage.load_permanent() == []
    assert [e.label for e in storage.load_day(date(2026, 10, 9))] == [entry.label]
    assert storage.list_permanent_snapshots()[0].action == 'moved "A renders" to Daily'


def test_layout_from_config(make_widget):
    w, _ = make_widget(lambda: datetime(2026, 10, 9, 12, 0))
    assert w.splitter.widget(0) is w.permanent and w.splitter.widget(1) is w.daily

    w2, _ = make_widget(lambda: datetime(2026, 10, 9, 12, 0), '[window]\npermanent_side = "right"\n')
    assert w2.splitter.widget(0) is w2.daily and w2.splitter.widget(1) is w2.permanent
