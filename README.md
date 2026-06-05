revreader

A small Python EPUB reader with terminal and Qt GUI modes.

Usage

- Terminal: revreader -t mybook.epub
- GUI: revreader mybook.epub  (or run and press Ctrl+O)

Dependencies

- Python 3.8+
- For GUI: PySide6 (or PyQt6). Install with: pip install PySide6

Notes

- The GUI attempts to load embedded fonts and inline images from EPUB files.
- The terminal reader renders plain text with headings and pagination.

Author: rumyp
