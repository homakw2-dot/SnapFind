# SnapFind 🔍

A fast, privacy-focused desktop application for indexing and searching text across screenshots and images locally on Windows.

No cloud uploads, no heavy models, no tracking. Everything runs 100% offline using native Windows OCR and SQLite.

![SnapFind Preview](docs/preview.png)

## Features

- **Instant Text Search**: Search through thousands of screenshots by any keyword, error code, phrase, or number.
- **100% Offline & Private**: Uses native Windows Media OCR API. Zero data leaves your computer.
- **Fast Local Indexing**: Computes image hashes to avoid re-scanning unmodified files.
- **Modern Dark GUI**: Built with CustomTkinter with responsive cards, thumbnails, and preview modal.
- **One-Click Text Extraction**: Instantly copy full recognized text or specific snippets directly to your clipboard.
- **Bilingual OCR**: Seamlessly handles Cyrillic and Latin text concurrently (Russian + English).

## Tech Stack

- **Python 3.10+**
- **GUI**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- **OCR Engine**: [winocr](https://github.com/intxcc/winocr) (Windows.Media.Ocr native bindings)
- **Database**: SQLite3
- **Image Processing**: Pillow

## Quickstart

### 1. Clone the repository
```bash
git clone https://github.com/Homak2/SnapFind.git
cd SnapFind
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run
```bash
python main.py
```

## How It Works

1. Click **«Сканировать папку»** and choose your screenshots or pictures folder.
2. The background worker parses images, extracts text via native Windows OCR, and stores hashes in a local `snapfind.db`.
3. Type any text in the search bar — matching images appear instantly with snippet highlights and thumbnails.
4. Click thumbnail to open the inspector view or hit **«Копировать текст»** to grab the OCR text.

## License

MIT
