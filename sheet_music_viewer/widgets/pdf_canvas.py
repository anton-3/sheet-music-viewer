from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from time import monotonic

from PyQt6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen, QTouchEvent
from PyQt6.QtWidgets import QWidget

from sheet_music_viewer.pdf_document import PdfDocument


PAGE_GAP = 24.0
TAP_SLOP = 24.0
SWIPE_CLOSE_DISTANCE = 90.0
SWIPE_NAVIGATE_DISTANCE = 90.0
PINCH_SCALE_SLOP = 0.03
TWO_FINGER_TAP_MAX_DURATION = 0.35
MIN_ZOOM_FACTOR = 0.3
MAX_ZOOM_FACTOR = 6.0


@dataclass(frozen=True)
class PagePlacement:
    page_index: int
    rect: QRectF


class PdfCanvas(QWidget):
    navigate_requested = pyqtSignal(int)
    close_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._document: PdfDocument | None = None
        self._page_index = 0
        self._rotation = 0
        self._zoom_factor = 1.0
        self._pan_offset = QPointF()
        self._pointer_press_pos: QPointF | None = None
        self._single_touch_press_pos: QPointF | None = None
        self._single_touch_last_pos: QPointF | None = None
        self._touch_session_active = False
        self._pinch_start_distance: float | None = None
        self._pinch_start_zoom = 1.0
        self._pinch_start_center = QPointF()
        self._pinch_start_pan = QPointF()
        self._two_finger_tap_candidate = False
        self._two_finger_tap_started_at = 0.0
        self._two_finger_start_positions: dict[int, QPointF] = {}
        self._ignore_mouse_until = 0.0

    def set_document(self, document: PdfDocument) -> None:
        self._document = document
        self._page_index = 0
        self._rotation = 0
        self._zoom_factor = 1.0
        self._pan_offset = QPointF()
        self.update()

    def clear_document(self) -> None:
        self._document = None
        self._page_index = 0
        self._rotation = 0
        self._zoom_factor = 1.0
        self._pan_offset = QPointF()
        self.update()

    def set_page_index(self, page_index: int) -> None:
        if not self._document:
            return
        self._page_index = max(0, min(page_index, self._max_page_index()))
        self._pan_offset = QPointF()
        self.update()

    def page_index(self) -> int:
        return self._page_index

    def _max_page_index(self) -> int:
        assert self._document is not None
        if self.spread_size() == 2 and self._document.page_count % 2 == 0:
            return max(0, self._document.page_count - 2)
        return self._document.page_count - 1

    def spread_size(self) -> int:
        return 1 if self.height() > self.width() else 2

    def rotate_clockwise(self) -> None:
        self._rotation = (self._rotation + 90) % 360
        self._pan_offset = QPointF()
        self.update()

    def rotate_counterclockwise(self) -> None:
        self._rotation = (self._rotation - 90) % 360
        self._pan_offset = QPointF()
        self.update()

    def reset_zoom(self) -> None:
        if self._zoom_factor == 1.0 and self._pan_offset.isNull():
            return
        self._zoom_factor = 1.0
        self._pan_offset = QPointF()
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

    def event(self, event: QEvent) -> bool:
        if event.type() in (
            QEvent.Type.TouchBegin,
            QEvent.Type.TouchUpdate,
            QEvent.Type.TouchEnd,
            QEvent.Type.TouchCancel,
        ):
            self._ignore_mouse_until = monotonic() + 0.5
            self._handle_touch_event(event)
            return True
        return super().event(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._should_ignore_mouse():
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._pointer_press_pos = event.position()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._should_ignore_mouse():
            event.accept()
            return
        if event.button() != Qt.MouseButton.LeftButton or self._pointer_press_pos is None:
            super().mouseReleaseEvent(event)
            return

        start = self._pointer_press_pos
        end = event.position()
        self._pointer_press_pos = None
        self._handle_pointer_gesture(start, end)
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

        base_pages = self._base_page_placements(viewport)
        return [self._transform_placement(placement) for placement in base_pages]

    def _base_page_placements(self, viewport: QRectF) -> list[PagePlacement]:
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
        return QRectF(0.0, 0.0, width, height)

    def _transform_placement(self, placement: PagePlacement) -> PagePlacement:
        rect = placement.rect
        transformed = QRectF(
            rect.left() * self._zoom_factor + self._pan_offset.x(),
            rect.top() * self._zoom_factor + self._pan_offset.y(),
            rect.width() * self._zoom_factor,
            rect.height() * self._zoom_factor,
        )
        return PagePlacement(page_index=placement.page_index, rect=transformed)

    def _draw_page_borders(self, painter: QPainter, placements: list[PagePlacement]) -> None:
        painter.save()
        painter.setPen(QPen(QColor("#343434"), 1))
        for placement in placements:
            painter.drawRect(placement.rect)
        painter.restore()

    def _handle_pointer_gesture(self, start: QPointF, end: QPointF) -> None:
        delta_x = end.x() - start.x()
        delta_y = end.y() - start.y()
        horizontal_third = self.width() / 3

        if delta_y >= SWIPE_CLOSE_DISTANCE and abs(delta_y) > abs(delta_x):
            self.close_requested.emit()
            return

        if abs(delta_x) >= SWIPE_NAVIGATE_DISTANCE and abs(delta_x) > abs(delta_y):
            if delta_x > 0:
                self.navigate_requested.emit(-self.spread_size())
            else:
                self.navigate_requested.emit(self.spread_size())
            return

        if abs(delta_x) <= TAP_SLOP and abs(delta_y) <= TAP_SLOP:
            if end.x() < horizontal_third:
                self.navigate_requested.emit(-self.spread_size())
            elif end.x() >= horizontal_third * 2:
                self.navigate_requested.emit(self.spread_size())

    def _handle_touch_event(self, event: QEvent) -> None:
        touch_event = event
        assert isinstance(touch_event, QTouchEvent)

        if touch_event.type() == QEvent.Type.TouchCancel:
            self._reset_touch_state()
            touch_event.accept()
            return

        points = touch_event.points()
        point_count = len(points)

        if touch_event.type() == QEvent.Type.TouchBegin:
            self._touch_session_active = True
            if point_count == 1:
                self._single_touch_press_pos = points[0].position()
                self._single_touch_last_pos = points[0].position()
            else:
                self._single_touch_press_pos = None
                self._single_touch_last_pos = None
            if point_count >= 2:
                self._begin_multi_touch(points)
            touch_event.accept()
            return

        if touch_event.type() == QEvent.Type.TouchUpdate:
            if point_count == 1:
                self._single_touch_last_pos = points[0].position()
            if point_count >= 2:
                if self._pinch_start_distance is None:
                    self._begin_multi_touch(points)
                self._update_pinch(points)
            touch_event.accept()
            return

        if touch_event.type() == QEvent.Type.TouchEnd:
            if self._two_finger_tap_candidate and self._two_finger_tap_within_threshold():
                self.reset_zoom()
            elif self._single_touch_press_pos is not None and self._single_touch_last_pos is not None:
                self._handle_pointer_gesture(self._single_touch_press_pos, self._single_touch_last_pos)
            self._reset_touch_state()
            touch_event.accept()

    def _begin_multi_touch(self, points: list[QTouchEvent.TouchPoint]) -> None:
        self._single_touch_press_pos = None
        self._single_touch_last_pos = None
        self._pinch_start_distance = self._touch_distance(points)
        self._pinch_start_zoom = self._zoom_factor
        self._pinch_start_center = self._touch_center(points)
        self._pinch_start_pan = QPointF(self._pan_offset)
        self._two_finger_tap_candidate = len(points) == 2
        self._two_finger_tap_started_at = monotonic()
        self._two_finger_start_positions = {point.id(): point.position() for point in points[:2]}

    def _update_pinch(self, points: list[QTouchEvent.TouchPoint]) -> None:
        if len(points) < 2:
            return

        current_distance = self._touch_distance(points)
        if self._pinch_start_distance is None or self._pinch_start_distance <= 0:
            self._pinch_start_distance = max(current_distance, 1.0)
            self._pinch_start_zoom = self._zoom_factor
            return

        scale_delta = current_distance / self._pinch_start_distance
        next_zoom = max(
            MIN_ZOOM_FACTOR,
            min(self._pinch_start_zoom * scale_delta, MAX_ZOOM_FACTOR),
        )
        current_center = self._touch_center(points)
        content_focus = QPointF(
            (self._pinch_start_center.x() - self._pinch_start_pan.x()) / self._pinch_start_zoom,
            (self._pinch_start_center.y() - self._pinch_start_pan.y()) / self._pinch_start_zoom,
        )
        next_pan = QPointF(
            current_center.x() - content_focus.x() * next_zoom,
            current_center.y() - content_focus.y() * next_zoom,
        )
        if (
            abs(next_zoom - self._zoom_factor) > 0.001
            or abs(next_pan.x() - self._pan_offset.x()) > 0.5
            or abs(next_pan.y() - self._pan_offset.y()) > 0.5
        ):
            self._zoom_factor = next_zoom
            self._pan_offset = next_pan
            self.update()

        if abs(scale_delta - 1.0) > PINCH_SCALE_SLOP:
            self._two_finger_tap_candidate = False
            return

        for point in points[:2]:
            start_position = self._two_finger_start_positions.get(point.id())
            if start_position is None:
                self._two_finger_tap_candidate = False
                return
            movement = point.position() - start_position
            if hypot(movement.x(), movement.y()) > TAP_SLOP:
                self._two_finger_tap_candidate = False
                return

    def _touch_distance(self, points: list[QTouchEvent.TouchPoint]) -> float:
        first = self._to_logical_point(points[0].position())
        second = self._to_logical_point(points[1].position())
        return hypot(second.x() - first.x(), second.y() - first.y())

    def _touch_center(self, points: list[QTouchEvent.TouchPoint]) -> QPointF:
        first = self._to_logical_point(points[0].position())
        second = self._to_logical_point(points[1].position())
        return QPointF((first.x() + second.x()) / 2, (first.y() + second.y()) / 2)

    def _two_finger_tap_within_threshold(self) -> bool:
        return monotonic() - self._two_finger_tap_started_at <= TWO_FINGER_TAP_MAX_DURATION

    def _reset_touch_state(self) -> None:
        self._touch_session_active = False
        self._single_touch_press_pos = None
        self._single_touch_last_pos = None
        self._pinch_start_distance = None
        self._pinch_start_zoom = self._zoom_factor
        self._pinch_start_center = QPointF()
        self._pinch_start_pan = QPointF(self._pan_offset)
        self._two_finger_tap_candidate = False
        self._two_finger_tap_started_at = 0.0
        self._two_finger_start_positions = {}

    def _should_ignore_mouse(self) -> bool:
        return self._touch_session_active or monotonic() < self._ignore_mouse_until

    def _to_logical_point(self, point: QPointF) -> QPointF:
        centered = QPointF(point.x() - self.width() / 2, point.y() - self.height() / 2)
        if self._rotation == 90:
            return QPointF(centered.y(), -centered.x())
        if self._rotation == 180:
            return QPointF(-centered.x(), -centered.y())
        if self._rotation == 270:
            return QPointF(-centered.y(), centered.x())
        return centered
