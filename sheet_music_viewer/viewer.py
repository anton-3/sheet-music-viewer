from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeyEvent, QResizeEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from sheet_music_viewer.markup import MarkupStore
from sheet_music_viewer.pdf_document import PdfDocument
from sheet_music_viewer.widgets.markup_toolbar import MarkupToolbar
from sheet_music_viewer.widgets.pdf_canvas import PdfCanvas


class ViewerWindow(QWidget):
    closed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sheet Music Viewer")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Window, True)

        self._document: PdfDocument | None = None
        self._markup_store = MarkupStore()

        self.canvas = PdfCanvas(self)
        self.canvas.navigate_requested.connect(self._navigate)
        self.canvas.close_requested.connect(self.close_pdf)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self._toolbar = MarkupToolbar(self)
        self._toolbar.hide()

        self.canvas.edit_mode_entered.connect(self._on_edit_mode_entered)
        self.canvas.edit_mode_exited.connect(self._on_edit_mode_exited)
        self.canvas.unsaved_changes_changed.connect(self._toolbar.set_save_enabled)

        self._toolbar.color_selected.connect(self.canvas.set_pen_color)
        self._toolbar.undo_requested.connect(self.canvas.undo_last)
        self._toolbar.erase_toggled.connect(self.canvas.set_erase_mode)
        self._toolbar.save_requested.connect(self.canvas.save_markup)
        self._toolbar.close_requested.connect(self.canvas.exit_edit_mode)

        self._build_actions()

    def open_pdf(self, pdf_path: Path) -> None:
        self._close_document()
        self._document = PdfDocument(pdf_path)
        self._markup_store.load(pdf_path)
        self.canvas.set_document(self._document)
        self.canvas.set_markup_store(self._markup_store)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.canvas.setFocus()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self.canvas.edit_mode_active():
                self.canvas.exit_edit_mode()
            else:
                self.close_pdf()
            event.accept()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._position_toolbar()

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
        self._toolbar.hide()
        self._markup_store.clear()
        if self._document is None:
            self.canvas.clear_document()
            return
        self._document.close()
        self._document = None
        self.canvas.clear_document()

    def _on_edit_mode_entered(self) -> None:
        self._toolbar.set_save_enabled(self._markup_store.has_unsaved_changes)
        self._toolbar.show()
        self._toolbar.raise_()
        self._position_toolbar()

    def _on_edit_mode_exited(self) -> None:
        self._toolbar.hide()

    def _position_toolbar(self) -> None:
        self._toolbar.adjustSize()
        tw = self._toolbar.sizeHint().width()
        th = self._toolbar.sizeHint().height()
        x = (self.width() - tw) // 2
        y = self.height() - th - 24
        self._toolbar.move(x, y)
        self._toolbar.resize(tw, th)

    def _build_actions(self) -> None:
        rotate_cw = QAction(self)
        rotate_cw.setShortcut("r")
        rotate_cw.triggered.connect(self.canvas.rotate_clockwise)
        self.addAction(rotate_cw)

        rotate_ccw = QAction(self)
        rotate_ccw.setShortcut("Shift+R")
        rotate_ccw.triggered.connect(self.canvas.rotate_counterclockwise)
        self.addAction(rotate_ccw)
