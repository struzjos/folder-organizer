"""The frameless desktop panel: header + Permanent and Daily columns."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QGuiApplication, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSizeGrip,
    QSplitter,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..config import Settings
from ..day import format_day, logical_date
from ..models import FolderEntry
from ..storage import Storage
from .day_navigator import DayNavigator
from .permanent_history_dialog import PermanentHistoryDialog
from .section import FolderSection

log = logging.getLogger(__name__)

PANEL_STYLE = """
QFrame#panel {
    background: palette(window);
    border: 1px solid palette(mid);
    border-radius: 8px;
}
"""

DAY_CHECK_INTERVAL_MS = 30_000


class HeaderBar(QWidget):
    """Title row; dragging it moves the frameless window."""

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None and handle.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)


class MainWidget(QWidget):
    hiddenToTray = Signal()

    def __init__(
        self,
        settings: Settings,
        storage: Storage,
        clock: Callable[[], datetime] = datetime.now,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.storage = storage
        self._clock = clock
        self._state = storage.load_state()
        self.today = logical_date(clock(), settings.reset_time)
        self.viewed_day = self.today
        self._notice_source_day: date | None = None

        self.setWindowTitle("Folder Organizer")
        on_top = bool(self._state.get("always_on_top", settings.window.always_on_top))
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(settings.window.opacity)
        self.setMinimumSize(280, 220)

        # Panel with rounded border
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setStyleSheet(PANEL_STYLE)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 4, 6, 2)
        layout.setSpacing(2)

        # Header
        header = HeaderBar()
        header.setCursor(Qt.CursorShape.SizeAllCursor)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 2, 0, 2)
        title = QLabel("Folder Organizer")
        font = QFont(title.font())
        font.setBold(True)
        title.setFont(font)
        self.pin_button = QToolButton()
        self.pin_button.setText("📌")
        self.pin_button.setToolTip("Keep on top of other windows")
        self.pin_button.setCheckable(True)
        self.pin_button.setChecked(on_top)
        self.pin_button.setAutoRaise(True)
        self.pin_button.setCursor(Qt.CursorShape.ArrowCursor)
        hide_button = QToolButton()
        hide_button.setText("—")
        hide_button.setToolTip("Hide to tray (click the tray icon to show again)")
        hide_button.setAutoRaise(True)
        hide_button.setCursor(Qt.CursorShape.ArrowCursor)
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        header_layout.addWidget(self.pin_button)
        header_layout.addWidget(hide_button)

        # Sections
        self.permanent = FolderSection("Permanent", move_target="Daily")
        self.daily = FolderSection("Daily", move_target="Permanent")
        history_button = QToolButton()
        history_button.setText("🕘")
        history_button.setToolTip("Permanent history: view and restore earlier versions")
        history_button.setAutoRaise(True)
        self.permanent.add_header_widget(history_button)
        self.navigator = DayNavigator()
        self.daily.add_toolbar(self.navigator)

        orientation = (
            Qt.Orientation.Horizontal if settings.window.layout == "horizontal" else Qt.Orientation.Vertical
        )
        self.splitter = QSplitter(orientation)
        self.splitter.setChildrenCollapsible(False)
        first, second = (
            (self.permanent, self.daily) if settings.window.permanent_first else (self.daily, self.permanent)
        )
        self.splitter.addWidget(first)
        self.splitter.addWidget(second)

        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.addStretch(1)
        grip_row.addWidget(QSizeGrip(self))

        layout.addWidget(header)
        layout.addWidget(self.splitter, 1)
        layout.addLayout(grip_row)

        # Wiring
        self.pin_button.toggled.connect(self.set_always_on_top)
        hide_button.clicked.connect(self.hide_to_tray)
        history_button.clicked.connect(self.show_permanent_history)
        self.permanent.changed.connect(self._on_permanent_changed)
        self.daily.changed.connect(self._on_daily_changed)
        self.permanent.moveRequested.connect(lambda e: self._move(e, self.permanent, self.daily))
        self.daily.moveRequested.connect(lambda e: self._move(e, self.daily, self.permanent))
        self.navigator.dayChanged.connect(self.show_day)
        self.daily.notice_button.clicked.connect(self._copy_notice_day_to_today)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self.save_state)
        self.splitter.splitterMoved.connect(lambda *_: self._save_timer.start())

        self._day_timer = QTimer(self)
        self._day_timer.setInterval(DAY_CHECK_INTERVAL_MS)
        self._day_timer.timeout.connect(self.check_day)
        self._day_timer.start()

        self.permanent.set_entries(storage.load_permanent())
        self.refresh_daily()
        self._restore_geometry()

    # Daily

    def show_day(self, day: date) -> None:
        self.viewed_day = day
        self.refresh_daily()

    def refresh_daily(self) -> None:
        self.daily.set_entries(self.storage.load_day(self.viewed_day))
        self._refresh_daily_chrome()

    def check_day(self) -> None:
        """Called periodically: switch to the new day after the reset time."""
        new_today = logical_date(self._clock(), self.settings.reset_time)
        if new_today == self.today:
            return
        log.info("New day: %s", new_today)
        was_viewing_today = self.viewed_day == self.today
        self.today = new_today
        if was_viewing_today:
            self.viewed_day = new_today
        self.refresh_daily()

    def _refresh_daily_chrome(self) -> None:
        is_today = self.viewed_day == self.today
        self.daily.set_title("Daily · Today" if is_today else f"Daily · {format_day(self.viewed_day)}")
        self.daily.list.placeholder_text = (
            "Drop folders here\nor click +" if is_today else "Nothing saved for this day"
        )
        self.navigator.set_days(self.storage.list_days(), self.today, self.viewed_day)

        self._notice_source_day = None
        if is_today and not self.daily.entries():
            previous = self.storage.last_nonempty_day_before(self.today)
            if previous is not None:
                self._notice_source_day = previous
                self.daily.notice_button.setText(f"Load previous day ({format_day(previous)})")
        elif not is_today and self.daily.entries():
            self._notice_source_day = self.viewed_day
            self.daily.notice_button.setText("Copy this day to today")
        self.daily.notice_button.setVisible(self._notice_source_day is not None)

    def _copy_notice_day_to_today(self) -> None:
        if self._notice_source_day is None:
            return
        today_entries = self.storage.load_day(self.today)
        present = {e.key() for e in today_entries}
        copied = [
            FolderEntry(e.label, e.path)
            for e in self.storage.load_day(self._notice_source_day)
            if e.key() not in present
        ]
        self.storage.save_day(self.today, today_entries + copied)
        log.info("Copied %d entries from %s to today", len(copied), self._notice_source_day)
        self.show_day(self.today)

    def _on_daily_changed(self, entries: list[FolderEntry], action: str) -> None:
        self.storage.save_day(self.viewed_day, entries)
        log.info("Daily %s: %s", self.viewed_day, action)
        self._refresh_daily_chrome()

    # Permanent

    def _on_permanent_changed(self, entries: list[FolderEntry], action: str) -> None:
        self.storage.save_permanent(entries, action)

    def show_permanent_history(self) -> None:
        dialog = PermanentHistoryDialog(self.storage, self)
        dialog.exec()
        if dialog.restored:
            self.permanent.set_entries(self.storage.load_permanent())

    def _move(self, entry: FolderEntry, source: FolderSection, target: FolderSection) -> None:
        if not target.accept_entry(entry, f'moved "{entry.label}" from {source.name}'):
            QMessageBox.information(self, "Already there", f"“{entry.label}” is already in {target.name}.")
            return
        source.remove_entry(entry, f'moved "{entry.label}" to {target.name}')

    # Window

    def set_always_on_top(self, on: bool) -> None:
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on)
        if visible:
            self.show()  # changing window flags hides the window
        self._state["always_on_top"] = on
        self.save_state()

    def hide_to_tray(self) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            self.hiddenToTray.emit()
        else:
            self.close()

    def show_and_raise(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def save_state(self) -> None:
        g = self.geometry()
        self._state["geometry"] = [g.x(), g.y(), g.width(), g.height()]
        self._state["splitter"] = self.splitter.sizes()
        self.storage.save_state(self._state)

    def _restore_geometry(self) -> None:
        rect = None
        geometry = self._state.get("geometry")
        if isinstance(geometry, list) and len(geometry) == 4 and all(isinstance(v, int) for v in geometry):
            rect = QRect(*geometry)
        if rect is None or QGuiApplication.screenAt(rect.center()) is None:
            screen = QGuiApplication.primaryScreen().availableGeometry()
            rect = QRect(0, 0, self.settings.window.width, 400)
            rect.moveTopRight(screen.topRight() + QPoint(-24, 24))
        self.setGeometry(rect)
        sizes = self._state.get("splitter")
        if isinstance(sizes, list) and len(sizes) == 2 and all(isinstance(v, int) and v > 0 for v in sizes):
            self.splitter.setSizes(sizes)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Re-check which folders still exist.
        self.permanent.set_entries(self.permanent.entries())
        self.daily.set_entries(self.daily.entries())

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self._save_timer.start()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._save_timer.start()

    def closeEvent(self, event) -> None:
        self.save_state()
        super().closeEvent(event)
