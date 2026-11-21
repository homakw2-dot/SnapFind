import os
import asyncio
from PIL import Image
import winocr

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
MAX_DIMENSION = 1400
CONCURRENCY = 6

async def extract_text_from_file(image_path):
    try:
        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
            w, h = rgb_img.size
            if max(w, h) > MAX_DIMENSION:
                ratio = MAX_DIMENSION / max(w, h)
                nw, nh = int(w * ratio), int(h * ratio)
                rgb_img = rgb_img.resize((nw, nh), Image.Resampling.BILINEAR)

            res = await winocr.recognize_pil(rgb_img, "ru")
            return res.text.strip() if res and res.text else ""
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

        async def _run_all():
            nonlocal indexed_count, skipped_count
            sem = asyncio.Semaphore(CONCURRENCY)
            processed_counter = 0

            async def _process_file(file_path):
                nonlocal indexed_count, skipped_count, processed_counter
                if self._stop_requested:
                    return

                try:
                    stat = os.stat(file_path)
                    f_size = stat.st_size
                    f_mtime = stat.st_mtime
                except Exception:
                    return

                if self.db.is_indexed(file_path, f_size, f_mtime):
                    skipped_count += 1
                    processed_counter += 1
                    if progress_callback:
                        progress_callback(processed_counter, total)
                    return

                async with sem:
                    if self._stop_requested:
                        return
                    if status_callback:
                        status_callback(f"[{processed_counter + 1}/{total}] {os.path.basename(file_path)}")

                    text = await extract_text_from_file(file_path)
                    self.db.upsert_image(file_path, f_size, f_mtime, text)
                    indexed_count += 1
                    processed_counter += 1

                    if progress_callback:
                        progress_callback(processed_counter, total)

            tasks = [_process_file(fp) for fp in image_files]
            await asyncio.gather(*tasks)

        try:
            loop.run_until_complete(_run_all())
        finally:
            loop.close()
            self.is_running = False

        return indexed_count, skipped_count, total
