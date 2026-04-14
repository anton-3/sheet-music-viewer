from __future__ import annotations

import sys

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

from sheet_music_viewer.home import HomeWindow
from sheet_music_viewer.settings import AppSettings
from sheet_music_viewer.viewer import ViewerWindow


def main() -> int:
    QGuiApplication.setApplicationDisplayName("Sheet Music Viewer")
    QApplication.setOrganizationName("sheet-music-viewer")
    QApplication.setApplicationName("sheet-music-viewer")

    app = QApplication(sys.argv)

    settings = AppSettings()
    home = HomeWindow(settings)
    viewer = ViewerWindow()

    home.pdf_requested.connect(lambda path: _open_pdf(home, viewer, path))
    viewer.closed.connect(home.show_home)

    home.show()
    return app.exec()


def _open_pdf(home: HomeWindow, viewer: ViewerWindow, path) -> None:
    home.hide()
    viewer.open_pdf(path)
