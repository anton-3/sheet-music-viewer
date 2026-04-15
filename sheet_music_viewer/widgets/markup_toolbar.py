from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget


PEN_COLORS = [
    "#000000",
    "#dc3545",
    "#e67e22",
    "#f4d03f",
    "#2b7cff",
    "#9b59b6",
    "#ffffff",
]

_CIRCLE_SIZE = 36
_BUTTON_SIZE = 40
_TOOLBAR_PADDING = 10
_TOOLBAR_SPACING = 6
_SELECTION_RING_WIDTH = 3


class ColorCircleButton(QPushButton):
    def __init__(self, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self._selected = False
        self.setFixedSize(_CIRCLE_SIZE, _CIRCLE_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_selected(self, selected: bool) -> None:
        if self._selected != selected:
            self._selected = selected
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        center = QPointF(self.rect().center())
        radius = min(self.width(), self.height()) / 2 - 2

        if self._selected:
            ring_color = QColor("#ffffff") if self._color != "#ffffff" else QColor("#888888")
            painter.setPen(QPen(ring_color, _SELECTION_RING_WIDTH))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, radius, radius)
            radius -= _SELECTION_RING_WIDTH + 1

        painter.setPen(QPen(QColor("#555555"), 1))
        painter.setBrush(QColor(self._color))
        painter.drawEllipse(center, radius, radius)


class IconButton(QPushButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(_BUTTON_SIZE, _BUTTON_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._active = False

    def set_active(self, active: bool) -> None:
        if self._active != active:
            self._active = active
            self.update()

    def _icon_color(self) -> QColor:
        if not self.isEnabled():
            return QColor("#555555")
        if self._active:
            return QColor("#4fc3f7")
        return QColor("#e0e0e0")

    def _draw_background(self, painter: QPainter) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        bg = QColor("#4fc3f7") if self._active else QColor(50, 50, 50, 180)
        painter.setBrush(bg)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)

    def _icon_color_for_active(self) -> QColor:
        if self._active:
            return QColor("#1a1a1a")
        return self._icon_color()


class UndoButton(IconButton):
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._draw_background(painter)

        color = self._icon_color_for_active()
        painter.setPen(QPen(color, 2.2, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cx, cy = self.width() / 2, self.height() / 2
        r = 9.0
        path = QPainterPath()
        path.arcMoveTo(QRectF(cx - r, cy - r, r * 2, r * 2), 150)
        path.arcTo(QRectF(cx - r, cy - r, r * 2, r * 2), 150, -200)
        painter.drawPath(path)

        end = path.currentPosition()
        painter.setBrush(color)
        arrow = QPainterPath()
        arrow.moveTo(end.x() - 4, end.y() - 1)
        arrow.lineTo(end.x() + 2, end.y() - 5)
        arrow.lineTo(end.x() + 2, end.y() + 3)
        arrow.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(arrow)


class EraseButton(IconButton):
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._draw_background(painter)

        color = self._icon_color_for_active()
        painter.setPen(QPen(color, 2.0, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin))

        cx, cy = self.width() / 2, self.height() / 2
        w, h = 16.0, 10.0
        painter.translate(cx, cy)
        painter.rotate(-25)
        rect = QRectF(-w / 2, -h / 2, w, h)
        painter.drawRoundedRect(rect, 2, 2)
        painter.drawLine(int(-w / 2 + 5), int(-h / 2), int(-w / 2 + 5), int(h / 2))


class SaveButton(IconButton):
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._draw_background(painter)

        color = self._icon_color_for_active()
        painter.setPen(QPen(color, 2.0, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cx, cy = self.width() / 2, self.height() / 2
        s = 8.0
        body = QRectF(cx - s, cy - s, s * 2, s * 2)
        painter.drawRoundedRect(body, 2, 2)

        painter.drawLine(int(cx - 4), int(cy - s), int(cx - 4), int(cy - s + 5))
        painter.drawLine(int(cx + 4), int(cy - s), int(cx + 4), int(cy - s + 5))

        inner = QRectF(cx - 4, cy + 1, 8, 5)
        painter.drawRect(inner)


class CloseButton(IconButton):
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._draw_background(painter)

        color = self._icon_color_for_active()
        painter.setPen(QPen(color, 2.5, cap=Qt.PenCapStyle.RoundCap))

        cx, cy = self.width() / 2, self.height() / 2
        d = 7.0
        painter.drawLine(int(cx - d), int(cy - d), int(cx + d), int(cy + d))
        painter.drawLine(int(cx + d), int(cy - d), int(cx - d), int(cy + d))


class MarkupToolbar(QWidget):
    color_selected = pyqtSignal(str)
    undo_requested = pyqtSignal()
    erase_toggled = pyqtSignal(bool)
    save_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._color_buttons: list[ColorCircleButton] = []
        self._active_color = PEN_COLORS[0]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(_TOOLBAR_PADDING, _TOOLBAR_PADDING, _TOOLBAR_PADDING, _TOOLBAR_PADDING)
        layout.setSpacing(_TOOLBAR_SPACING)

        for color in PEN_COLORS:
            btn = ColorCircleButton(color, self)
            btn.clicked.connect(lambda checked, c=color: self._on_color_clicked(c))
            self._color_buttons.append(btn)
            layout.addWidget(btn)

        layout.addSpacing(12)

        self._undo_btn = UndoButton(self)
        self._undo_btn.clicked.connect(self.undo_requested.emit)
        layout.addWidget(self._undo_btn)

        self._erase_btn = EraseButton(self)
        self._erase_btn.clicked.connect(self._on_erase_clicked)
        layout.addWidget(self._erase_btn)

        self._save_btn = SaveButton(self)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self.save_requested.emit)
        layout.addWidget(self._save_btn)

        self._close_btn = CloseButton(self)
        self._close_btn.clicked.connect(self.close_requested.emit)
        layout.addWidget(self._close_btn)

        self._update_color_selection()
        self.adjustSize()
        self.hide()

    def set_save_enabled(self, enabled: bool) -> None:
        self._save_btn.setEnabled(enabled)

    def set_undo_enabled(self, enabled: bool) -> None:
        self._undo_btn.setEnabled(enabled)

    def set_active_color(self, color: str) -> None:
        self._active_color = color
        self._erase_btn.set_active(False)
        self._update_color_selection()

    def set_erase_active(self, active: bool) -> None:
        self._erase_btn.set_active(active)
        if active:
            for btn in self._color_buttons:
                btn.set_selected(False)
        else:
            self._update_color_selection()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#444444"), 1))
        painter.setBrush(QColor(24, 24, 24, 220))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)

    def _on_color_clicked(self, color: str) -> None:
        self._active_color = color
        self._erase_btn.set_active(False)
        self._update_color_selection()
        self.color_selected.emit(color)

    def _on_erase_clicked(self) -> None:
        new_state = not self._erase_btn._active
        self._erase_btn.set_active(new_state)
        if new_state:
            for btn in self._color_buttons:
                btn.set_selected(False)
        else:
            self._update_color_selection()
        self.erase_toggled.emit(new_state)

    def _update_color_selection(self) -> None:
        for btn in self._color_buttons:
            btn.set_selected(btn._color == self._active_color)
