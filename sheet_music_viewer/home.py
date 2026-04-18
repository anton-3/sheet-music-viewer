from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScroller,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sheet_music_viewer.library import LibraryItem, list_library_items, pdf_page_count
from sheet_music_viewer.settings import AppSettings


TAP_DRAG_THRESHOLD = 18
BACK_SWIPE_DISTANCE = 90


class LibraryListWidget(QListWidget):
    item_tapped = pyqtSignal(QListWidgetItem)
    back_swiped = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._press_pos: QPoint | None = None
        self._dragging = False

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._press_pos is not None:
            distance = (event.position().toPoint() - self._press_pos).manhattanLength()
            if distance > TAP_DRAG_THRESHOLD:
                self._dragging = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
            delta = event.position().toPoint() - self._press_pos
            distance = delta.manhattanLength()
            should_activate = not self._dragging and distance <= TAP_DRAG_THRESHOLD
            should_go_back = (
                delta.x() >= BACK_SWIPE_DISTANCE
                and abs(delta.x()) > abs(delta.y())
            )
            item = self.itemAt(event.position().toPoint()) if should_activate else None
            self._press_pos = None
            self._dragging = False
            super().mouseReleaseEvent(event)
            if should_go_back:
                self.back_swiped.emit()
                return
            if item is not None:
                self.item_tapped.emit(item)
            return
        self._press_pos = None
        self._dragging = False
        super().mouseReleaseEvent(event)


class StarButton(QPushButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("", parent)
        self.setCheckable(True)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setPen(QColor("#b18900") if self.isChecked() else QColor("#2a2a2a"))
        font = painter.font()
        font.setPixelSize(18)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, -1, 0, -1), Qt.AlignmentFlag.AlignCenter, "\u2605")


class LibraryRowWidget(QWidget):
    star_toggled = pyqtSignal(Path)

    def __init__(self, item: LibraryItem, starred: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._item = item
        self.setObjectName("pdfRowWidget")
        self.setAutoFillBackground(False)

        label_text = f"[DIR] {item.display_name}" if item.is_directory else item.display_name
        self.label = QLabel(label_text)
        self.label.setObjectName("pdfRowLabel")
        self.label.setWordWrap(False)
        self.label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(12)
        layout.addWidget(self.label, stretch=1)

        self.pages_label: QLabel | None = None
        if not item.is_directory and item.page_count is not None:
            self.pages_label = QLabel(f"{item.page_count} pages")
            self.pages_label.setObjectName("pdfRowPagesLabel")
            self.pages_label.setWordWrap(False)
            self.pages_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
            layout.addWidget(self.pages_label, stretch=0)

        self.star_button: QPushButton | None = None
        if not item.is_directory:
            self.star_button = StarButton()
            self.star_button.setObjectName("rowStarButton")
            self.star_button.setChecked(starred)
            self.star_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.star_button.setToolTip("Toggle starred PDF")
            self.star_button.clicked.connect(self._emit_star_toggled)
            layout.addWidget(self.star_button, stretch=0)

    def sizeHint(self) -> QSize:
        return QSize(0, 60)

    def _emit_star_toggled(self, checked: bool) -> None:
        del checked
        self.star_toggled.emit(self._item.path)


class SettingsDialog(QDialog):
    def __init__(self, current_root: Path | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selected_root: Path | None = current_root

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(520)

        self.root_value_label = QLabel(self._format_root(current_root))
        self.root_value_label.setWordWrap(True)

        change_root_button = QPushButton("Change Root Folder")
        change_root_button.clicked.connect(self._choose_root_directory)

        root_row = QHBoxLayout()
        root_row.setSpacing(12)
        root_row.addWidget(self.root_value_label, stretch=1)
        root_row.addWidget(change_root_button, stretch=0)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        layout.addLayout(root_row)
        layout.addStretch(1)
        layout.addWidget(buttons)

    def selected_root_directory(self) -> Path | None:
        return self._selected_root

    def _choose_root_directory(self) -> None:
        default_text = str(self._selected_root) if self._selected_root else "~/Documents"
        while True:
            typed_path, accepted = QInputDialog.getText(
                self,
                "Set Library Root",
                "Enter the folder path containing your sheet music PDFs:",
                text=default_text,
            )
            if not accepted:
                return

            candidate = Path(typed_path).expanduser()
            if candidate.exists() and candidate.is_dir():
                self._selected_root = candidate.resolve()
                self.root_value_label.setText(self._format_root(self._selected_root))
                return

            QMessageBox.warning(self, "Invalid Folder", f"'{candidate}' is not a readable directory.")

    def _format_root(self, path: Path | None) -> str:
        return str(path) if path else "Not configured"


class HomeWindow(QMainWindow):
    pdf_requested = pyqtSignal(object)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self._root_directory: Path | None = None
        self._current_directory: Path | None = None
        self._history: list[Path] = []
        self._starred_mode = False

        self.setWindowTitle("Sheet Music Viewer")
        self.resize(1000, 700)
        self._build_ui()
        self._apply_styles()
        self._ensure_root_directory()

    def show_home(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _build_ui(self) -> None:
        self.path_label = QLabel("No library selected")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.path_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self._go_back)

        self.starred_view_button = StarButton()
        self.starred_view_button.setObjectName("starButton")
        self.starred_view_button.setToolTip("Show starred PDFs")
        self.starred_view_button.clicked.connect(self._toggle_starred_view)

        self.settings_button = QPushButton("\u2699")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setToolTip("Settings")
        self.settings_button.clicked.connect(self._open_settings_dialog)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.back_button)
        header_layout.addWidget(self.path_label, stretch=1)
        header_layout.addWidget(self.starred_view_button)
        header_layout.addWidget(self.settings_button)

        self.list_widget = LibraryListWidget()
        self._configure_library_list()
        self.list_widget.itemActivated.connect(self._activate_item)
        self.list_widget.item_tapped.connect(self._activate_item)
        self.list_widget.back_swiped.connect(self._go_back)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addLayout(header_layout)
        layout.addWidget(self.list_widget)
        self.setCentralWidget(container)

    def _configure_library_list(self) -> None:
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setAutoScroll(False)
        self.list_widget.setUniformItemSizes(False)
        self.list_widget.setSpacing(2)

        QScroller.grabGesture(
            self.list_widget.viewport(),
            QScroller.ScrollerGestureType.LeftMouseButtonGesture,
        )
        QScroller.grabGesture(
            self.list_widget.viewport(),
            QScroller.ScrollerGestureType.TouchGesture,
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #e8e8e8;
                color: #1c1c1c;
                font-size: 16px;
            }
            QPushButton {
                background: #d3d3d3;
                border: 1px solid #9a9a9a;
                padding: 10px 16px;
                min-width: 100px;
            }
            QPushButton#settingsButton {
                font-size: 22px;
                min-width: 52px;
                max-width: 52px;
                padding: 8px;
            }
            QPushButton#starButton {
                font-size: 22px;
                min-width: 52px;
                max-width: 52px;
                padding: 8px;
                color: #2a2a2a;
                background: #d3d3d3;
            }
            QPushButton#starButton:checked {
                color: #b18900;
                background: #e1d19a;
            }
            QPushButton#rowStarButton {
                font-size: 18px;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
                padding: 0;
                color: #2a2a2a;
                background: #d3d3d3;
            }
            QPushButton#rowStarButton:checked {
                color: #b18900;
                background: #e1d19a;
            }
            QWidget#pdfRowWidget,
            QLabel#pdfRowLabel {
                background: transparent;
            }
            QLabel#pdfRowPagesLabel {
                background: transparent;
                color: #888888;
                font-size: 13px;
            }
            QPushButton:disabled {
                color: #7d7d7d;
                background: #dcdcdc;
            }
            QDialog {
                background: #efefef;
                color: #1c1c1c;
            }
            QLabel#settingsHintLabel {
                color: #666666;
            }
            QListWidget {
                background: #f4f4f4;
                border: 1px solid #b8b8b8;
                outline: none;
            }
            QListWidget::item {
                padding: 0;
                border-bottom: 1px solid #d6d6d6;
            }
            QListWidget::item:selected {
                background: #cfcfcf;
                color: #111111;
            }
            """
        )

    def _ensure_root_directory(self) -> None:
        stored_root = self.settings.get_root_directory()
        if stored_root:
            self._set_root_directory(stored_root)
            return
        if root_directory := self._prompt_for_root_directory():
            self.settings.set_root_directory(root_directory)
            self._set_root_directory(root_directory)

    def _prompt_for_root_directory(self, initial_path: Path | None = None) -> Path | None:
        default_text = str(initial_path) if initial_path else "~/Documents"
        while True:
            typed_path, accepted = QInputDialog.getText(
                self,
                "Set Library Root",
                "Enter the folder path containing your sheet music PDFs:",
                text=default_text,
            )
            if not accepted:
                return None

            candidate = Path(typed_path).expanduser()
            if candidate.exists() and candidate.is_dir():
                return candidate.resolve()

            QMessageBox.warning(self, "Invalid Folder", f"'{candidate}' is not a readable directory.")

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self._root_directory, self)
        if dialog.exec() != QDialog.DialogCode.Accepted and dialog.selected_root_directory() == self._root_directory:
            return

        new_root = dialog.selected_root_directory()
        if new_root is None or new_root == self._root_directory:
            return

        self.settings.set_root_directory(new_root)
        self._set_root_directory(new_root)

    def _set_root_directory(self, root_directory: Path) -> None:
        self._root_directory = root_directory.resolve()
        self._history.clear()
        self._starred_mode = False
        self.starred_view_button.setChecked(False)
        self._navigate_to(self._root_directory)

    def _navigate_to(self, directory: Path) -> None:
        self._current_directory = directory
        self._refresh_header()
        self._reload_list()

    def _reload_list(self) -> None:
        self.list_widget.clear()
        items = self._current_items()

        if not items:
            message = (
                "No starred PDFs yet."
                if self._starred_mode
                else "This folder has no PDFs or subfolders."
            )
            empty = QListWidgetItem(message)
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(empty)
            return

        starred_paths = self.settings.get_starred_pdfs()
        for item in items:
            widget_item = QListWidgetItem()
            widget_item.setData(Qt.ItemDataRole.UserRole, item)
            row_widget = LibraryRowWidget(item, item.path in starred_paths, self.list_widget)
            row_widget.star_toggled.connect(self._toggle_pdf_star)
            widget_item.setSizeHint(row_widget.sizeHint())
            self.list_widget.addItem(widget_item)
            self.list_widget.setItemWidget(widget_item, row_widget)

    def _activate_item(self, widget_item: QListWidgetItem) -> None:
        item = widget_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(item, LibraryItem):
            return
        if item.is_directory:
            if self._starred_mode:
                return
            assert self._current_directory is not None
            self._history.append(self._current_directory)
            self._navigate_to(item.path)
            return
        self.pdf_requested.emit(item.path)

    def _go_back(self) -> None:
        if self._starred_mode:
            return
        if not self._history:
            return
        previous = self._history.pop()
        self._navigate_to(previous)

    def _toggle_starred_view(self) -> None:
        self._starred_mode = self.starred_view_button.isChecked()
        self._refresh_header()
        self._reload_list()

    def _toggle_pdf_star(self, path: Path) -> None:
        self.settings.toggle_pdf_star(path)
        self._reload_list()

    def _refresh_header(self) -> None:
        if self._starred_mode:
            self.path_label.setText("Starred Sheet Music")
            self.back_button.setEnabled(False)
            return

        directory = self._current_directory
        self.path_label.setText(str(directory) if directory else "No library selected")
        self.back_button.setEnabled(bool(self._root_directory and directory and directory != self._root_directory))

    def _current_items(self) -> list[LibraryItem]:
        if self._starred_mode:
            return self._starred_items()

        assert self._current_directory is not None
        try:
            return list_library_items(self._current_directory)
        except OSError as exc:
            QMessageBox.warning(self, "Folder Error", f"Could not read '{self._current_directory}': {exc}")
            return []

    def _starred_items(self) -> list[LibraryItem]:
        if not self._root_directory:
            return []

        root_directory = self._root_directory.resolve()
        starred_paths = sorted(self.settings.get_starred_pdfs(), key=lambda path: path.name.lower())
        items: list[LibraryItem] = []
        for path in starred_paths:
            try:
                resolved = path.resolve()
                resolved.relative_to(root_directory)
            except (OSError, ValueError):
                continue
            items.append(
                LibraryItem(path=resolved, is_directory=False, page_count=pdf_page_count(resolved)),
            )
        return items
