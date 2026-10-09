"""Browse saved versions of the Permanent list and restore one."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..models import PermanentSnapshot
from ..storage import Storage


class PermanentHistoryDialog(QDialog):
    def __init__(self, storage: Storage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Permanent history")
        self.resize(760, 440)
        self.storage = storage
        self.restored = False
        self._snapshots: list[PermanentSnapshot] = []
        self._current_row: int | None = None

        intro = QLabel(
            "Every change to the Permanent list is saved here. Select a version to preview it and "
            "click Restore to make it the current list. A restore is saved too, so it can be undone."
        )
        intro.setWordWrap(True)
        self.versions = QListWidget()
        self.preview = QListWidget()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.versions)
        splitter.addWidget(self.preview)
        splitter.setSizes([400, 360])

        self.restore_button = QPushButton("Restore this version")
        close_button = QPushButton("Close")
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.restore_button)
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(splitter, 1)
        layout.addLayout(buttons)

        self.versions.currentRowChanged.connect(self._show_preview)
        self.restore_button.clicked.connect(self._restore)
        close_button.clicked.connect(self.accept)
        self._reload()

    def _reload(self) -> None:
        self._snapshots = self.storage.list_permanent_snapshots()
        current = [(e.label, e.path) for e in self.storage.load_permanent()]
        newest = [(e.label, e.path) for e in self._snapshots[0].entries] if self._snapshots else None
        self._current_row = 0 if newest == current else None

        self.versions.blockSignals(True)
        self.versions.clear()
        for row, snapshot in enumerate(self._snapshots):
            text = f"{snapshot.timestamp:%Y-%m-%d %H:%M:%S}   {snapshot.action}"
            if row == self._current_row:
                text += "   (current)"
            self.versions.addItem(text)
        if not self._snapshots:
            item = QListWidgetItem("No changes recorded yet.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.versions.addItem(item)
        self.versions.blockSignals(False)

        if self._snapshots:
            self.versions.setCurrentRow(0)
        self._show_preview(self.versions.currentRow() if self._snapshots else -1)

    def _show_preview(self, row: int) -> None:
        self.preview.clear()
        if not 0 <= row < len(self._snapshots):
            self.restore_button.setEnabled(False)
            return
        entries = self._snapshots[row].entries
        for entry in entries:
            item = QListWidgetItem(f"{entry.label}\n    {entry.path}")
            item.setToolTip(entry.path)
            self.preview.addItem(item)
        if not entries:
            self.preview.addItem("(empty list)")
        self.restore_button.setEnabled(row != self._current_row)

    def _restore(self) -> None:
        row = self.versions.currentRow()
        if not 0 <= row < len(self._snapshots):
            return
        snapshot = self._snapshots[row]
        answer = QMessageBox.question(
            self,
            "Restore version",
            f"Replace the current Permanent list with the version from "
            f"{snapshot.timestamp:%Y-%m-%d %H:%M:%S}?\n\n"
            "The current list stays in the history, so you can switch back.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.restored = self.storage.restore_permanent(snapshot.snapshot_id) or self.restored
            self._reload()
