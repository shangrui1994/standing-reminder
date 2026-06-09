from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPixmap


def main() -> int:
    app = QGuiApplication(sys.argv)
    del app

    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    pixmap = QPixmap(256, 256)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#2eb67d"))
    painter.drawEllipse(18, 18, 220, 220)

    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(121, 62, 28, 125, 14, 14)
    painter.drawRoundedRect(82, 102, 106, 28, 14, 14)
    painter.drawEllipse(98, 42, 72, 72)

    painter.setBrush(QColor("#ffcf5a"))
    painter.drawEllipse(178, 38, 48, 48)
    painter.end()

    pixmap.save(str(assets_dir / "app_icon.ico"), "ICO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
