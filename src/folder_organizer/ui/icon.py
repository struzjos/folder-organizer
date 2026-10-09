"""App / tray icon, drawn in code so no image files are needed."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap


def make_app_icon() -> QIcon:
    """A folder with two "button" bars. Requires a QGuiApplication."""
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        s = size / 64

        def rect(x: float, y: float, w: float, h: float, r: float) -> None:
            p.drawRoundedRect(QRectF(x * s, y * s, w * s, h * s), r * s, r * s)

        p.setBrush(QColor("#D89A1E"))  # back + tab
        rect(4, 8, 26, 14, 4)
        rect(4, 14, 56, 44, 6)
        p.setBrush(QColor("#F5C342"))  # front
        rect(4, 20, 56, 38, 6)
        p.setBrush(QColor(255, 255, 255, 230))  # buttons
        rect(13, 29, 38, 8, 3)
        rect(13, 42, 26, 8, 3)
        p.end()
        icon.addPixmap(pixmap)
    return icon
