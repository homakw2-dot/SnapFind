# SnapFind

Fast and privacy-focused desktop tool for searching text across screenshots and images locally on Windows.

Everything runs 100% offline using native Windows OCR and SQLite.

## Highlights

- **Instant Search**: Search through hundreds of screenshots by any keyword, number, or phrase.
- **High Performance**: Asynchronous multi-worker engine processing multiple images concurrently.
- **Smart Cache**: Fast file metadata checks (`os.stat`) to skip unchanged images in milliseconds.
- **100% Offline & Private**: Native Windows Media OCR integration with zero cloud dependencies.
- **Clean Dark UI**: Built with CustomTkinter with responsive cards, thumbnails, and preview modal.
- **Direct Copy**: Copy full extracted text or snippets straight to the clipboard.

## Requirements

- Windows 10 / 11
- Python 3.10+

## Setup

```bash
git clone https://github.com/homakw2-dot/SnapFind.git
cd SnapFind
pip install -r requirements.txt
```

## Running

Launch the app:
```bash
python main.py
```
Or double-click `SnapFind.pyw` to run directly without opening a terminal window.
