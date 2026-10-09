"""◀ [day combo] ▶ [Today]: switch between saved days of the Daily list."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QSizePolicy, QToolButton, QWidget

from ..day import format_day


class DayNavigator(QWidget):
    dayChanged = Signal(object)  # date

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._days: list[date] = []  # newest first
        self._today: date | None = None

        self.older_button = QToolButton()
        self.older_button.setArrowType(Qt.ArrowType.LeftArrow)
        self.older_button.setToolTip("Previous saved day")
        self.older_button.setAutoRaise(True)
        self.combo = QComboBox()
        self.combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo.setToolTip("Saved days")
        self.newer_button = QToolButton()
        self.newer_button.setArrowType(Qt.ArrowType.RightArrow)
        self.newer_button.setToolTip("Next saved day")
        self.newer_button.setAutoRaise(True)
        self.today_button = QToolButton()
        self.today_button.setText("Today")
        self.today_button.setAutoRaise(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.older_button)
        layout.addWidget(self.combo, 1)
        layout.addWidget(self.newer_button)
        layout.addWidget(self.today_button)

        self.older_button.clicked.connect(lambda: self._step(+1))
        self.newer_button.clicked.connect(lambda: self._step(-1))
        self.today_button.clicked.connect(lambda: self._today and self.dayChanged.emit(self._today))
        self.combo.activated.connect(lambda i: self.dayChanged.emit(self._days[i]))

    def set_days(self, days: list[date], today: date, current: date) -> None:
        self._today = today
        self._days = sorted(set(days) | {today, current}, reverse=True)
        self.combo.blockSignals(True)
        self.combo.clear()
        for d in self._days:
            self.combo.addItem(format_day(d))
        self.combo.setCurrentIndex(self._days.index(current))
        self.combo.blockSignals(False)
        i = self.combo.currentIndex()
        self.older_button.setEnabled(i < len(self._days) - 1)
        self.newer_button.setEnabled(i > 0)
        self.today_button.setEnabled(current != today)

    def _step(self, delta: int) -> None:
        i = self.combo.currentIndex() + delta
        if 0 <= i < len(self._days):
            self.dayChanged.emit(self._days[i])
