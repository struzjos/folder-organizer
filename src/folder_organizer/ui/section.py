"""One column of the widget (Permanent or Daily): header, "+" button, list of folder buttons."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QCursor, QFont, QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from ..explorer import open_folder
from ..models import FolderEntry, path_key
from ..naming import suggest_label
from .entry_dialog import EntryDialog
from .folder_list import FolderList


class FolderSection(QFrame):
    changed = Signal(list, str)  # all entries after the change, action description
    moveRequested = Signal(object)  # FolderEntry to move to the other section

    def __init__(self, name: str, move_target: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.name = name
        self._move_target = move_target
        self._entries: list[FolderEntry] = []
        self._last_dir = str(Path.home())

        self.title_label = QLabel(name)
        font = QFont(self.title_label.font())
        font.setBold(True)
        self.title_label.setFont(font)
        self.add_button = QToolButton()
        self.add_button.setText("+")
        self.add_button.setToolTip(f"Add a folder to {name}…")
        self.add_button.setAutoRaise(True)
        self.add_button.setStyleSheet("QToolButton { font-size: 16px; font-weight: bold; padding: 0 4px; }")
        self.header = QHBoxLayout()
        self.header.setContentsMargins(0, 0, 0, 0)
        self.header.addWidget(self.title_label)
        self.header.addStretch(1)
        self.header.addWidget(self.add_button)

        self.notice_button = QPushButton()
        self.notice_button.hide()

        self.list = FolderList(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addLayout(self.header)
        layout.addWidget(self.notice_button)
        layout.addWidget(self.list, 1)

        self.add_button.clicked.connect(self.add_with_picker)
        self.list.entryActivated.connect(self._open)
        self.list.reordered.connect(self._on_reordered)
        self.list.foldersDropped.connect(self.add_folders)
        self.list.customContextMenuRequested.connect(self._show_context_menu)

    # Public API

    def add_header_widget(self, widget: QWidget) -> None:
        """Add a widget to the header, left of the "+" button."""
        self.header.insertWidget(self.header.count() - 1, widget)

    def add_toolbar(self, widget: QWidget) -> None:
        """Add a full-width row under the header."""
        self.layout().insertWidget(1, widget)

    def set_title(self, text: str) -> None:
        self.title_label.setText(text)

    def entries(self) -> list[FolderEntry]:
        return list(self._entries)

    def set_entries(self, entries: list[FolderEntry]) -> None:
        self._entries = list(entries)
        self.list.set_entries(self._entries)

    def contains_path(self, path: str, ignore_index: int | None = None) -> bool:
        key = path_key(path)
        return any(e.key() == key for i, e in enumerate(self._entries) if i != ignore_index)

    def accept_entry(self, entry: FolderEntry, action: str) -> bool:
        """Append an entry (e.g. moved from the other section). False if the folder is already here."""
        if self.contains_path(entry.path):
            return False
        self._apply(self._entries + [entry], action)
        return True

    def remove_entry(self, entry: FolderEntry, action: str) -> None:
        self._apply([e for e in self._entries if e is not entry], action)

    def add_with_picker(self) -> None:
        folder = QFileDialog.getExistingDirectory(self.window(), f"Add folder to {self.name}", self._last_dir)
        if folder:
            self.add_folders([os.path.normpath(folder)])

    def add_folders(self, paths: list[str]) -> None:
        new: dict[str, str] = {}
        for p in paths:
            if not self.contains_path(p):
                new.setdefault(path_key(p), p)
        skipped = len(paths) - len(new)
        if not new:
            self._notify(f"Already in {self.name}.")
            return
        new_paths = list(new.values())
        self._last_dir = str(Path(new_paths[0]).parent)

        labels = [e.label for e in self._entries]
        if len(new_paths) == 1:
            dialog = EntryDialog(
                self.window(),
                title=f"Add to {self.name}",
                path=new_paths[0],
                other_labels=labels,
                suggest=lambda p: suggest_label(p, labels),
            )
            if not dialog.exec():
                return
            label, path = dialog.values()
            if self.contains_path(path):
                self._notify(f"Already in {self.name}.")
                return
            added = [FolderEntry(label, path)]
        else:
            added = []
            for p in new_paths:
                label = suggest_label(p, labels)
                labels.append(label)
                added.append(FolderEntry(label, p))

        if len(added) == 1:
            action = f'added "{added[0].label}"'
        else:
            action = f"added {len(added)} folders: " + ", ".join(f'"{e.label}"' for e in added)
        self._apply(self._entries + added, action)
        if skipped:
            self._notify(f"{skipped} folder(s) already in {self.name} were skipped.")

    # Internals

    def _apply(self, entries: list[FolderEntry], action: str) -> None:
        self.set_entries(entries)
        self.changed.emit(self.entries(), action)

    def _notify(self, message: str) -> None:
        QToolTip.showText(QCursor.pos(), message, self.list)

    def _open(self, index: int) -> None:
        entry = self._entries[index]
        if not open_folder(entry.path):
            QMessageBox.warning(
                self.window(),
                "Folder not found",
                f"The folder for “{entry.label}” doesn't exist anymore:\n{entry.path}\n\n"
                "Right-click the button and choose Edit… to point it to the new location.",
            )
            self.list.set_entries(self._entries)  # refresh missing state

    def _edit(self, index: int) -> None:
        entry = self._entries[index]
        others = [e.label for i, e in enumerate(self._entries) if i != index]
        dialog = EntryDialog(
            self.window(),
            title="Edit button",
            path=entry.path,
            label=entry.label,
            other_labels=others,
            suggest=lambda p: suggest_label(p, others),
        )
        if not dialog.exec():
            return
        label, path = dialog.values()
        if (label, path) == (entry.label, entry.path):
            return
        if self.contains_path(path, ignore_index=index):
            self._notify(f"That folder is already in {self.name}.")
            return
        entries = list(self._entries)
        entries[index] = FolderEntry(label, path, entry.added_at)
        if path == entry.path:
            action = f'renamed "{entry.label}" → "{label}"'
        elif label == entry.label:
            action = f'changed folder of "{label}"'
        else:
            action = f'edited "{entry.label}" → "{label}"'
        self._apply(entries, action)

    def _remove(self, index: int) -> None:
        entry = self._entries[index]
        answer = QMessageBox.question(
            self.window(),
            "Remove button",
            f"Remove “{entry.label}” from {self.name}?\n\nThe folder itself is not touched.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.remove_entry(entry, f'removed "{entry.label}"')

    def _on_reordered(self, order: list[int]) -> None:
        self._apply([self._entries[i] for i in order], "reordered")

    def _show_context_menu(self, pos) -> None:
        index = self.list.entry_index_at(pos)
        menu = QMenu(self)
        if index is None:
            menu.addAction("Add folder…", self.add_with_picker)
        else:
            entry = self._entries[index]
            menu.addAction("Open", lambda: self._open(index))
            menu.addAction("Edit…", lambda: self._edit(index))
            menu.addAction("Copy path", lambda: QGuiApplication.clipboard().setText(entry.path))
            menu.addSeparator()
            menu.addAction(f"Move to {self._move_target}", lambda: self.moveRequested.emit(entry))
            menu.addSeparator()
            menu.addAction("Remove", lambda: self._remove(index))
        menu.exec(self.list.viewport().mapToGlobal(pos))
