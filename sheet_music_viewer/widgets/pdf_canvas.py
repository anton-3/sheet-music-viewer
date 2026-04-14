from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget

from sheet_music_viewer.pdf_document import PdfDocument


PAGE_GAP = 24.0


@dataclass(frozen=True)
class PagePlacement:
    page_index: int
    rect: QRectF


class PdfCanvas(QWidget):
    navigate_requested = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._document: PdfDocument | None = None
        self._page_index = 0
        self._rotation = 0

    def set_document(self, document: PdfDocument) -> None:
        self._document = document
        self._page_index = 0
        self._rotation = 0
        self.update()

    def clear_document(self) -> None:
        self._document = None
        self._page_index = 0
        self._rotation = 0
        self.update()

    def set_page_index(self, page_index: int) -> None:
        if not self._document:
            return
        self._page_index = max(0, min(page_index, self._document.page_count - 1))
        self.update()

    def page_index(self) -> int:
        return self._page_index

    def spread_size(self) -> int:
        return 1 if self.height() > self.width() else 2

    def rotate_clockwise(self) -> None:
        self._rotation = (self._rotation + 90) % 360
        self.update()

    def rotate_counterclockwise(self) -> None:
        self._rotation = (self._rotation - 90) % 360
        self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_R and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.rotate_counterclockwise()
            event.accept()
            return
        if event.key() == Qt.Key.Key_R:
            self.rotate_clockwise()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        midpoint = self.width() / 2
        delta = self.spread_size() if event.position().x() >= midpoint else -self.spread_size()
        self.navigate_requested.emit(delta)
        event.accept()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#121212"))

        if not self._document:
            return

        logical_size = self._logical_viewport_size()
        if logical_size.width() <= 0 or logical_size.height() <= 0:
            return

        painter.translate(self.rect().center())
        painter.rotate(self._rotation)

        viewport = QRectF(
            -logical_size.width() / 2,
            -logical_size.height() / 2,
            logical_size.width(),
            logical_size.height(),
        )
        placements = self._page_placements(viewport)
        for placement in placements:
            target_size = placement.rect.size().toSize()
            image = self._document.render_page(placement.page_index, target_size)
            painter.drawImage(placement.rect, image)

        self._draw_page_borders(painter, placements)
        self.draw_overlays(painter, placements)

    def draw_overlays(self, painter: QPainter, placements: list[PagePlacement]) -> None:
        # Reserved extension point for pen or markup layers.
        del painter, placements

    def _logical_viewport_size(self) -> QSize:
        if self._rotation in (90, 270):
            return QSize(self.height(), self.width())
        return self.size()

    def _page_placements(self, viewport: QRectF) -> list[PagePlacement]:
        if not self._document:
            return []

        if self.spread_size() == 1:
            return [self._single_page_rect(viewport, self._page_index)]

        pages: list[PagePlacement] = [self._spread_page_rect(viewport, self._page_index, left=True)]
        right_index = self._page_index + 1
        if right_index < self._document.page_count:
            pages.append(self._spread_page_rect(viewport, right_index, left=False))
        return pages

    def _single_page_rect(self, viewport: QRectF, page_index: int) -> PagePlacement:
        assert self._document is not None
        page_rect = self._fit_rect(viewport, *self._document.page_size(page_index))
        centered = QRectF(
            viewport.center().x() - page_rect.width() / 2,
            viewport.center().y() - page_rect.height() / 2,
            page_rect.width(),
            page_rect.height(),
        )
        return PagePlacement(page_index=page_index, rect=centered)

    def _spread_page_rect(self, viewport: QRectF, page_index: int, *, left: bool) -> PagePlacement:
        assert self._document is not None
        half_width = (viewport.width() - PAGE_GAP) / 2
        slot = QRectF(
            viewport.left() if left else viewport.left() + half_width + PAGE_GAP,
            viewport.top(),
            half_width,
            viewport.height(),
        )
        fitted = self._fit_rect(slot, *self._document.page_size(page_index))
        centered = QRectF(
            slot.center().x() - fitted.width() / 2,
            slot.center().y() - fitted.height() / 2,
            fitted.width(),
            fitted.height(),
        )
        return PagePlacement(page_index=page_index, rect=centered)

    def _fit_rect(self, bounds: QRectF, source_width: float, source_height: float) -> QRectF:
        scale = min(bounds.width() / source_width, bounds.height() / source_height)
        width = source_width * scale
        height = source_height * scale
        return QRectF(QPointF(0, 0), QSize(int(width), int(height)))

    def _draw_page_borders(self, painter: QPainter, placements: list[PagePlacement]) -> None:
        painter.save()
        painter.setPen(QPen(QColor("#343434"), 1))
        for placement in placements:
            painter.drawRect(placement.rect)
        painter.restore()
