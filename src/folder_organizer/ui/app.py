"""QApplication setup, system tray icon, startup."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from .. import paths
from ..config import Settings
from ..explorer import open_folder
from ..storage import Storage
from .icon import make_app_icon
from .main_widget import MainWidget

log = logging.getLogger(__name__)


class Tray(QSystemTrayIcon):
    def __init__(self, icon: QIcon, widget: MainWidget, app: QApplication) -> None:
        super().__init__(icon, app)
        self.widget = widget
        self._hint_shown = False
        self.setToolTip("Folder Organizer")

        self._menu = QMenu()
        self._toggle_action = self._menu.addAction("Show", self.toggle_widget)
        self._menu.addSeparator()
        self._menu.addAction("Open config folder", lambda: open_folder(str(paths.CONFIG_DIR)))
        self._menu.addAction("Open data folder", lambda: open_folder(str(widget.storage.data_dir)))
        self._menu.addSeparator()
        self._menu.addAction("Quit", self.quit_app)
        self._menu.aboutToShow.connect(
            lambda: self._toggle_action.setText("Hide" if widget.isVisible() else "Show")
        )
        self.setContextMenu(self._menu)

        self.activated.connect(self._on_activated)
        widget.hiddenToTray.connect(self._on_hidden)

    def toggle_widget(self) -> None:
        if self.widget.isVisible():
            self.widget.hide()
        else:
            self.widget.show_and_raise()

    def quit_app(self) -> None:
        self.widget.save_state()
        self.hide()
        QApplication.quit()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_widget()

    def _on_hidden(self) -> None:
        if not self._hint_shown:
            self._hint_shown = True
            self.showMessage(
                "Folder Organizer", "Still running here. Click the icon to show it again.", self.icon(), 3000
            )


def run(settings: Settings, storage: Storage, warnings: list[str]) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Folder Organizer")
    icon = make_app_icon()
    app.setWindowIcon(icon)

    widget = MainWidget(settings, storage)
    widget.setWindowIcon(icon)

    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        app.setQuitOnLastWindowClosed(False)
        tray = Tray(icon, widget, app)
        tray.show()
    else:
        log.warning("System tray not available; closing the widget quits the app")

    if not settings.window.start_hidden or tray is None:
        widget.show()
    if warnings:
        QTimer.singleShot(
            0,
            lambda: QMessageBox.warning(
                widget if widget.isVisible() else None, "Folder Organizer – settings", "\n\n".join(warnings)
            ),
        )
    app.aboutToQuit.connect(widget.save_state)
    return app.exec()
