# Repository Guidelines

## Project Structure & Module Organization

Application code lives in `sheet_music_viewer/`. The main entrypoints are `main.py`, `sheet_music_viewer/__main__.py`, and `sheet_music_viewer/app.py`. UI screens are split by responsibility: `home.py` handles the library and starred views, `viewer.py` owns the fullscreen shell, and `widgets/pdf_canvas.py` contains the custom paint-based PDF canvas for rendering, gestures, zoom, and future overlay work. PDF rendering is isolated in `pdf_document.py`; browsing models and persisted settings live in `library.py` and `settings.py`. Top-level project metadata is in `pyproject.toml`, dependency lock data is in `uv.lock`, and user-facing notes belong in `README.md` or `TODO.md`.

## Build, Test, and Development Commands

- `uv sync`: install and lock project dependencies from `pyproject.toml`.
- `uv run python main.py`: preferred local launch path for the desktop app.
- `uv run sheet-music-viewer`: packaged console-script launch path when the entrypoint is installed correctly.
- `python -m compileall sheet_music_viewer`: quick syntax/import verification for the package.

There is no dedicated build step beyond packaging metadata in `pyproject.toml`.

## Coding Style & Naming Conventions

Use Python 3.12+ with 4-space indentation and type hints on new or modified code. Follow the existing object-oriented layout: one class per major UI responsibility, with helper methods kept private via `_name` when not part of the public surface. Use `snake_case` for functions, methods, and modules; `PascalCase` for Qt widget classes; `UPPER_SNAKE_CASE` for gesture thresholds and other constants. Keep comments sparse and practical.

## Testing Guidelines

The repository does not yet include an automated test suite. For now, verify changes with `python -m compileall sheet_music_viewer` and a short manual run of the affected workflow, especially touch gestures, starred-library behavior, page jumps, navigation, and PDF rendering. When tests are added, place them under `tests/` and use filenames like `test_home.py` or `test_pdf_canvas.py`.

## Commit & Pull Request Guidelines

Recent commits use short imperative subjects such as `settings page` and `small fix to page navigation`. Keep commit messages brief, specific, and action-oriented. Pull requests should include a concise summary, note any gesture or UI behavior changes, link relevant issues if they exist, and include screenshots or short recordings for visible UI updates, especially for library-row styling or touch interaction changes.

## Configuration Notes

Root library location and starred PDF paths are stored through Qt `QSettings`. Do not commit local machine paths, sample PDFs, or generated `__pycache__/` directories.
