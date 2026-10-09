"""List of folder "buttons": click opens, drag to reorder, drop folders from Explorer to add."""

from __future__ import annotations

import os

from PySide6.QtCore import QMimeData, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QKeyEvent, QPainter, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileIconProvider,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QWidget,
)

from ..models import FolderEntry

ENTRY_INDEX_ROLE = Qt.ItemDataRole.UserRole

STYLE = """
QListWidget#folderList { background: transparent; border: none; outline: none; }
QListWidget#folderList::item {
    border: 1px solid palette(mid);
    border-radius: 6px;
    padding: 2px 6px;
    margin: 1px 1px;
    background: palette(button);
}
QListWidget#folderList::item:hover { border-color: palette(highlight); }
QListWidget#folderList::item:selected {
    border-color: palette(highlight);
    background: palette(button);
    color: palette(button-text);
}
"""


class FolderList(QListWidget):
    entryActivated = Signal(int)  # entry index
    reordered = Signal(list)  # new order as a list of old entry indexes
    foldersDropped = Signal(list)  # local folder paths dropped from outside

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("folderList")
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setStyleSheet(STYLE)
        self.placeholder_text = "Drop folders here\nor click +"
        self._folder_icon = QFileIconProvider().icon(QFileIconProvider.IconType.Folder)
        self._missing_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
        self.itemClicked.connect(self._on_item_clicked)

    def set_entries(self, entries: list[FolderEntry]) -> None:
        self.clear()
        missing_color = self.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text)
        for index, entry in enumerate(entries):
            exists = os.path.isdir(entry.path)
            item = QListWidgetItem(self._folder_icon if exists else self._missing_icon, entry.label)
            item.setData(ENTRY_INDEX_ROLE, index)
            item.setToolTip(entry.path if exists else f"{entry.path}\n(folder not found)")
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled
            )
            if not exists:
                item.setForeground(missing_color)
            self.addItem(item)

    def entry_index_at(self, pos: QPoint) -> int | None:
        item = self.itemAt(pos)
        return None if item is None else item.data(ENTRY_INDEX_ROLE)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.clearSelection()
        self.entryActivated.emit(item.data(ENTRY_INDEX_ROLE))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.currentItem() is not None:
            self.entryActivated.emit(self.currentItem().data(ENTRY_INDEX_ROLE))
            return
        super().keyPressEvent(event)

    # Drag & drop: internal = reorder, external (Explorer) = add folders

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.source() is not self and dropped_folders(event.mimeData()):
            _accept_as_link(event)
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.source() is not self and dropped_folders(event.mimeData()):
            _accept_as_link(event)
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        if event.source() is not self:
            folders = dropped_folders(event.mimeData())
            if folders:
                _accept_as_link(event)
                self.foldersDropped.emit(folders)
            return
        super().dropEvent(event)
        order = [self.item(row).data(ENTRY_INDEX_ROLE) for row in range(self.count())]
        if order != sorted(order):
            # Emit after Qt finishes the drag, so the re-render doesn't race with it.
            QTimer.singleShot(0, lambda: self.reordered.emit(order))

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.count() == 0 and self.placeholder_text:
            painter = QPainter(self.viewport())
            painter.setPen(self.palette().color(QPalette.ColorRole.PlaceholderText))
            painter.drawText(
                self.viewport().rect(),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                self.placeholder_text,
            )
            painter.end()


def _accept_as_link(event: QDropEvent | QDragMoveEvent | QDragEnterEvent) -> None:
    # Never report Move to Explorer, or it may delete the source folder.
    if event.possibleActions() & Qt.DropAction.LinkAction:
        event.setDropAction(Qt.DropAction.LinkAction)
    else:
        event.setDropAction(Qt.DropAction.CopyAction)
    event.accept()


def dropped_folders(mime: QMimeData) -> list[str]:
    """Local folders from a drop; for dropped files, their parent folder."""
    folders: dict[str, None] = {}
    if not mime.hasUrls():
        return []
    for url in mime.urls():
        if not url.isLocalFile():
            continue
        path = os.path.normpath(url.toLocalFile())
        if os.path.isfile(path):
            path = os.path.dirname(path)
        if os.path.isdir(path):
            folders.setdefault(path)
    return list(folders)
