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

## Current Features

- Configurable root sheet-music directory stored in app settings
- Library view that shows only folders and `.pdf` files
- Settings gear in the top-right corner with a modal settings dialog
- Touch-friendly library scrolling with tap-to-open behavior
- Right-swipe in the library to go back out of a folder
- Borderless full-screen PDF viewer
- Portrait mode: one centered page
- Landscape mode: two-page spread
- Outer left/right tap zones for page navigation
- Downward swipe to close the PDF and return to the library
- Even-page PDFs stop correctly on the final two-page spread
- `r` and `Shift+R` for visual rotation
- `Escape` to return to the library

## Structure

- `sheet_music_viewer/app.py`: Qt application bootstrap
- `sheet_music_viewer/home.py`: library browser window
- `sheet_music_viewer/viewer.py`: full-screen viewer shell
- `sheet_music_viewer/widgets/pdf_canvas.py`: custom paint-based PDF canvas for future overlays
- `sheet_music_viewer/pdf_document.py`: PyMuPDF-backed document rendering
- `sheet_music_viewer/settings.py`: persistent app settings
