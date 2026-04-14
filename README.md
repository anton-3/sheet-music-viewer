# Sheet Music Viewer

Minimal PyQt6 + PyMuPDF desktop reader for touch-first sheet music viewing on Linux.

## Run

```bash
uv sync
uv run sheet-music-viewer
```

You can also launch it with:

```bash
uv run python main.py
```

## MVP Features

- Configurable root sheet-music directory stored in app settings
- Home screen that shows only folders and `.pdf` files
- Borderless full-screen PDF viewer
- Portrait mode: one centered page
- Landscape mode: two-page spread
- Left/right tap zones for page navigation
- `r` and `Shift+R` for visual rotation
- `Escape` to return to the library

## Structure

- `sheet_music_viewer/app.py`: Qt application bootstrap
- `sheet_music_viewer/home.py`: library browser window
- `sheet_music_viewer/viewer.py`: full-screen viewer shell
- `sheet_music_viewer/widgets/pdf_canvas.py`: custom paint-based PDF canvas for future overlays
- `sheet_music_viewer/pdf_document.py`: PyMuPDF-backed document rendering
- `sheet_music_viewer/settings.py`: persistent app settings
