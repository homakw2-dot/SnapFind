import os
import threading
import subprocess
import customtkinter as ctk
from PIL import Image

from db import Database
from scanner import ScanWorker

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ImageDetailModal(ctk.CTkToplevel):
    def __init__(self, parent, file_path, ocr_text):
        super().__init__(parent)
        self.title(f"SnapFind - {os.path.basename(file_path)}")
        self.geometry("850x650")
        self.minsize(600, 400)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")

        title_lbl = ctk.CTkLabel(
            header_frame, 
            text=os.path.basename(file_path), 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_lbl.pack(side="left")

        open_btn = ctk.CTkButton(
            header_frame, 
            text="Открыть файл", 
            width=110,
            command=lambda: os.startfile(file_path) if os.path.exists(file_path) else None
        )
        open_btn.pack(side="right", padx=5)

        main_box = ctk.CTkFrame(self)
        main_box.grid(row=1, column=0, padx=15, pady=10, sticky="nsew")
        main_box.grid_columnconfigure(0, weight=1)
        main_box.grid_columnconfigure(1, weight=1)
        main_box.grid_rowconfigure(0, weight=1)

        self.img_lbl = ctk.CTkLabel(main_box, text="")
        self.img_lbl.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self._load_preview(file_path)

        text_frame = ctk.CTkFrame(main_box)
        text_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(1, weight=1)

        t_lbl = ctk.CTkLabel(text_frame, text="Распознанный текст:", font=ctk.CTkFont(size=13, weight="bold"))
        t_lbl.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.text_box = ctk.CTkTextbox(text_frame, font=ctk.CTkFont(family="Consolas", size=12))
        self.text_box.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.text_box.insert("1.0", ocr_text if ocr_text else "(Текст не обнаружен)")
        self.text_box.configure(state="disabled")

        copy_btn = ctk.CTkButton(text_frame, text="Скопировать весь текст", command=self._copy_text)
        copy_btn.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")

    def _load_preview(self, path):
        try:
            with Image.open(path) as img:
                w, h = img.size
                ratio = min(380 / w, 480 / h)
                nw, nh = int(w * ratio), int(h * ratio)
                resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=resized, dark_image=resized, size=(nw, nh))
                self.img_lbl.configure(image=ctk_img)
        except Exception:
            self.img_lbl.configure(text="Ошибка загрузки изображения")

    def _copy_text(self):
        content = self.text_box.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(content)


class SnapFindApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SnapFind - Smart Screenshot & Image Search")
        self.geometry("980x700")
        self.minsize(800, 550)

        self.db = Database()
        self.worker = ScanWorker(self.db)
        self.thumb_cache = {}

        self._build_ui()
        self._load_results("")

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        top_panel = ctk.CTkFrame(self, corner_radius=10)
        top_panel.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        top_panel.grid_columnconfigure(0, weight=1)

        app_title = ctk.CTkLabel(
            top_panel, 
            text="🔍 SnapFind", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        app_title.grid(row=0, column=0, padx=15, pady=(12, 5), sticky="w")

        count = self.db.count()
        self.stats_lbl = ctk.CTkLabel(
            top_panel, 
            text=f"В базе: {count} изображений", 
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        )
        self.stats_lbl.grid(row=0, column=1, padx=15, pady=(12, 5), sticky="e")

        search_frame = ctk.CTkFrame(top_panel, fg_color="transparent")
        search_frame.grid(row=1, column=0, columnspan=2, padx=15, pady=(5, 12), sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame, 
            placeholder_text="Введите текст для поиска по скриншотам (русский / английский)...",
            height=38,
            font=ctk.CTkFont(size=13)
        )
        self.search_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search_key)

        self.scan_btn = ctk.CTkButton(
            search_frame, 
            text="📁 Сканировать папку", 
            height=38,
            command=self._start_scan_dialog
        )
        self.scan_btn.grid(row=0, column=1, sticky="e")

        self.progress_frame = ctk.CTkFrame(self, height=28, fg_color="transparent")
        self.progress_frame.grid(row=1, column=0, padx=15, pady=(0, 5), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=8)
        self.progress_bar.set(0)

        self.status_lbl = ctk.CTkLabel(
            self.progress_frame, 
            text="Готов к работе", 
            font=ctk.CTkFont(size=12), 
            text_color="gray60"
        )
        self.status_lbl.grid(row=0, column=0, sticky="w")

        self.results_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.results_frame.grid(row=2, column=0, padx=15, pady=(5, 15), sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)

    def _on_search_key(self, event=None):
        query = self.search_entry.get().strip()
        self._load_results(query)

    def _load_results(self, query):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        rows = self.db.search(query, limit=50)

        if not rows:
            empty_lbl = ctk.CTkLabel(
                self.results_frame, 
                text="Ничего не найдено\n\nНажмите 'Сканировать папку', чтобы проиндексировать скриншоты.",
                font=ctk.CTkFont(size=14),
                text_color="gray60"
            )
            empty_lbl.pack(pady=50)
            return

        for row in rows:
            img_id, file_path, ocr_text, created_at = row
            if not os.path.exists(file_path):
                continue
            self._render_card(file_path, ocr_text, query)

    def _render_card(self, file_path, ocr_text, query):
        card = ctk.CTkFrame(self.results_frame, corner_radius=8, fg_color=("gray85", "gray20"))
        card.pack(fill="x", padx=5, pady=5)
        card.grid_columnconfigure(1, weight=1)

        thumb = self._get_thumbnail(file_path)
        img_btn = ctk.CTkButton(
            card, 
            image=thumb, 
            text="", 
            width=100, 
            height=70, 
            fg_color="transparent",
            hover_color=("gray75", "gray28"),
            command=lambda p=file_path, t=ocr_text: ImageDetailModal(self, p, t)
        )
        img_btn.grid(row=0, column=0, rowspan=2, padx=10, pady=8)

        fname = os.path.basename(file_path)
        title_lbl = ctk.CTkLabel(
            card, 
            text=fname, 
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        title_lbl.grid(row=0, column=1, padx=5, pady=(8, 2), sticky="w")

        clean_text = " ".join((ocr_text or "").split())
        preview_text = self._make_snippet(clean_text, query)

        snippet_lbl = ctk.CTkLabel(
            card, 
            text=preview_text if preview_text else "(Текст не распознан)", 
            font=ctk.CTkFont(size=12),
            text_color="gray75" if preview_text else "gray50",
            anchor="w",
            wraplength=520,
            justify="left"
        )
        snippet_lbl.grid(row=1, column=1, padx=5, pady=(0, 8), sticky="w")

        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.grid(row=0, column=2, rowspan=2, padx=10, pady=8, sticky="e")

        copy_btn = ctk.CTkButton(
            btn_box, 
            text="Копировать текст", 
            width=120, 
            height=28,
            command=lambda t=ocr_text: self._copy_to_clip(t)
        )
        copy_btn.pack(pady=2)

        open_btn = ctk.CTkButton(
            btn_box, 
            text="Открыть", 
            width=120, 
            height=28, 
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            command=lambda p=file_path: os.startfile(p)
        )
        open_btn.pack(pady=2)

    def _make_snippet(self, text, query, max_len=140):
        if not text:
            return ""
        if not query:
            return text[:max_len] + ("..." if len(text) > max_len else "")

        lower_t = text.lower()
        idx = lower_t.find(query.lower())
        if idx == -1:
            return text[:max_len] + ("..." if len(text) > max_len else "")

        start = max(0, idx - 40)
        end = min(len(text), idx + len(query) + 80)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return prefix + text[start:end] + suffix

    def _get_thumbnail(self, path):
        if path in self.thumb_cache:
            return self.thumb_cache[path]

        try:
            with Image.open(path) as img:
                w, h = img.size
                ratio = min(90 / w, 65 / h)
                nw, nh = max(1, int(w * ratio)), max(1, int(h * ratio))
                img_resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
                thumb = ctk.CTkImage(light_image=img_resized, dark_image=img_resized, size=(nw, nh))
                self.thumb_cache[path] = thumb
                return thumb
        except Exception:
            return None

    def _copy_to_clip(self, text):
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_lbl.configure(text="✓ Текст скопирован в буфер", text_color="#38bdf8")
        self.after(2500, lambda: self.status_lbl.configure(text="Готов к работе", text_color="gray60"))

    def _start_scan_dialog(self):
        folder = ctk.filedialog.askdirectory(title="Выберите папку со скриншотами")
        if not folder:
            return

        self.scan_btn.configure(state="disabled")
        self.progress_bar.grid(row=0, column=0, padx=(180, 0), sticky="ew")
        self.progress_bar.set(0)

        threading.Thread(target=self._run_scan_thread, args=(folder,), daemon=True).start()

    def _run_scan_thread(self, folder):
        def on_prog(cur, tot):
            val = cur / max(tot, 1)
            self.after(0, lambda: self.progress_bar.set(val))

        def on_stat(msg):
            self.after(0, lambda: self.status_lbl.configure(text=msg, text_color="gray75"))

        indexed, skipped, total = self.worker.scan_directory(folder, on_prog, on_stat)

        def on_done():
            self.scan_btn.configure(state="normal")
            self.progress_bar.grid_forget()
            self.stats_lbl.configure(text=f"В базе: {self.db.count()} изображений")
            self.status_lbl.configure(
                text=f"✓ Готово. Обработано новых: {indexed}, пропущено: {skipped} из {total}",
                text_color="#4ade80"
            )
            self._load_results(self.search_entry.get().strip())

        self.after(0, on_done)
