from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeyEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from sheet_music_viewer.pdf_document import PdfDocument
from sheet_music_viewer.widgets.pdf_canvas import PdfCanvas


class ViewerWindow(QWidget):
    closed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sheet Music Viewer")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Window, True)

        self._document: PdfDocument | None = None
        self.canvas = PdfCanvas(self)
        self.canvas.navigate_requested.connect(self._navigate)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self._build_actions()

    def open_pdf(self, pdf_path: Path) -> None:
        self._close_document()
        self._document = PdfDocument(pdf_path)
        self.canvas.set_document(self._document)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.canvas.setFocus()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_pdf()
            event.accept()
            return
        super().keyPressEvent(event)

    def close_pdf(self) -> None:
        self.hide()
        self._close_document()
        self.closed.emit()

    def _navigate(self, delta: int) -> None:
        if not self._document:
            return
        target = self.canvas.page_index() + delta
        self.canvas.set_page_index(target)

    def _close_document(self) -> None:
        if self._document is None:
            self.canvas.clear_document()
            return
        self._document.close()
        self._document = None
        self.canvas.clear_document()

    def _build_actions(self) -> None:
        rotate_cw = QAction(self)
        rotate_cw.setShortcut("r")
        rotate_cw.triggered.connect(self.canvas.rotate_clockwise)
        self.addAction(rotate_cw)

        rotate_ccw = QAction(self)
        rotate_ccw.setShortcut("Shift+R")
        rotate_ccw.triggered.connect(self.canvas.rotate_counterclockwise)
        self.addAction(rotate_ccw)
