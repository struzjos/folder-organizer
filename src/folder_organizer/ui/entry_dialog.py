"""Add / edit dialog for a button: custom name + folder path."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class EntryDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        path: str,
        suggest: Callable[[str], str],
        other_labels: Iterable[str] = (),
        label: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self._suggest = suggest
        self._other_labels = {name.strip().casefold() for name in other_labels}
        # When editing an existing button, never overwrite its name automatically.
        self._name_touched = label is not None

        self.name_edit = QLineEdit(label if label is not None else suggest(path))
        self.name_edit.setPlaceholderText("Name shown on the button")
        self.path_edit = QLineEdit(path)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse)

        self.warning = QLabel()
        self.warning.setWordWrap(True)
        self.warning.setStyleSheet("color: #c77700;")
        self.warning.hide()

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow("Name:", self.name_edit)
        form.addRow("Folder:", path_row)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.warning)
        layout.addWidget(self.buttons)

        self.name_edit.textEdited.connect(self._on_name_edited)
        self.name_edit.textChanged.connect(self._validate)
        self.path_edit.textChanged.connect(self._on_path_changed)
        self.name_edit.selectAll()
        self.name_edit.setFocus()
        self._validate()

    def values(self) -> tuple[str, str]:
        return self.name_edit.text().strip(), os.path.normpath(self.path_edit.text().strip())

    def _on_name_edited(self, _text: str) -> None:
        self._name_touched = True

    def _on_path_changed(self, text: str) -> None:
        if not self._name_touched and text.strip():
            self.name_edit.setText(self._suggest(os.path.normpath(text.strip())))
        self._validate()

    def _browse(self) -> None:
        start = self.path_edit.text().strip() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Choose folder", start)
        if folder:
            self.path_edit.setText(os.path.normpath(folder))

    def _validate(self) -> None:
        name = self.name_edit.text().strip()
        path = self.path_edit.text().strip()
        messages = []
        if name and name.casefold() in self._other_labels:
            messages.append("Another button in this list already has this name.")
        if path and not os.path.isdir(path):
            messages.append("This folder does not exist.")
        self.warning.setText("\n".join(messages))
        self.warning.setVisible(bool(messages))
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(name and path))
