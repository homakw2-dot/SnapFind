import os
import hashlib
import asyncio
from PIL import Image
import winocr

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

def get_file_hash(filepath):
    hasher = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None

async def extract_text(image_path):
    try:
        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
            res = await winocr.recognize_pil(rgb_img, "ru")
            text = res.text.strip() if res and res.text else ""
            if not text:
                res_en = await winocr.recognize_pil(rgb_img, "en")
                text = res_en.text.strip() if res_en and res_en.text else ""
            return text
    except Exception:
        return ""

class ScanWorker:
    def __init__(self, db):
        self.db = db
        self.is_running = False
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def scan_directory(self, folder_path, progress_callback=None, status_callback=None):
        self.is_running = True
        self._stop_requested = False
        
        image_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in SUPPORTED_EXTS:
                    image_files.append(os.path.join(root, file))

        total = len(image_files)
        indexed_count = 0
        skipped_count = 0

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            for idx, file_path in enumerate(image_files, 1):
                if self._stop_requested:
                    break

                if status_callback:
                    status_callback(f"[{idx}/{total}] {os.path.basename(file_path)}")
                if progress_callback:
                    progress_callback(idx, total)

                f_hash = get_file_hash(file_path)
                if not f_hash:
                    continue

                if self.db.is_indexed(file_path, f_hash):
                    skipped_count += 1
                    continue

                text = loop.run_until_complete(extract_text(file_path))
                self.db.upsert_image(file_path, f_hash, text)
                indexed_count += 1
        finally:
            loop.close()
            self.is_running = False

        return indexed_count, skipped_count, total
