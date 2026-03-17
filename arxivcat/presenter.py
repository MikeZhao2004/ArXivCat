"""Presenter: all business logic. Zero dependency on any UI framework."""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from arxivcat.ui.base import UIProtocol

from arxivcat.core import (
    extract_arxiv_id,
    download_source,
    extract_body_from_dir,
)

VERSION = "v0.2.0"
AUTHOR  = "by MikeDuke"


class Presenter:
    def __init__(self, ui: "UIProtocol"):
        self.ui = ui
        self.output_dir: Path | None = None
        self._init_cache()

    # ── init ──────────────────────────────────────────────────

    def _init_cache(self):
        """Clean downloads cache if > 50 MB on startup."""
        base = Path(os.environ.get("APPDATA", Path.home())) / "ArxivCat"
        downloads = base / "downloads"
        if downloads.exists():
            size = sum(f.stat().st_size for f in downloads.rglob("*") if f.is_file())
            if size > 50 * 1024 * 1024:
                shutil.rmtree(downloads)
                downloads.mkdir(parents=True, exist_ok=True)

    # ── public actions ────────────────────────────────────────

    def run_fetch(self):
        """Called when user clicks Run. Spawns background thread."""
        url = self.ui.get_url_input().strip()
        if not url:
            return
        self.ui.set_run_busy(True)
        self.ui.set_buttons_enabled(False)
        self.ui.clear_log()
        self.ui.set_preview("", "")
        self.ui.set_mini_status("", "info")
        self.output_dir = None
        threading.Thread(target=self._process, args=(url,), daemon=True).start()

    def copy_preview(self):
        return self.ui.get_preview_text()

    def overwrite_file(self):
        if not self.output_dir:
            return
        view = self.ui.get_view_mode()
        path = self.output_dir / f"{view}.tex"
        path.write_text(self.ui.get_preview_text(), encoding="utf-8")
        self.ui.show_toast(f"Saved {view}.tex")

    def open_folder(self):
        if self.output_dir and self.output_dir.exists():
            subprocess.Popen(f'explorer "{self.output_dir}"')

    def strip_comments(self):
        content = self.ui.get_preview_text()
        stripped = re.sub(r'(?<!\\)%.*', '', content)
        stripped = re.sub(r'\n{3,}', '\n\n', stripped).strip()
        self.ui.set_preview(stripped, self.ui.get_view_mode() + ".tex")
        self.ui.show_toast("Comments stripped")

    def switch_view(self):
        """Called when dropdown changes. Reload preview from disk."""
        self._load_preview()

    # ── internal ──────────────────────────────────────────────

    def _load_preview(self):
        if not self.output_dir:
            return
        view = self.ui.get_view_mode()
        path = self.output_dir / f"{view}.tex"
        content = path.read_text(encoding="utf-8") if path.exists() else "(file not found)"
        self.ui.set_preview(content, f"{view}.tex")

    def _process(self, url: str):
        base = Path(os.environ.get("APPDATA", Path.home())) / "ArxivCat"
        downloads_dir = base / "downloads"
        outputs_dir   = base / "outputs"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        outputs_dir.mkdir(parents=True, exist_ok=True)

        arxiv_id = extract_arxiv_id(url)
        if not arxiv_id:
            self.ui.add_log("[ERROR] 无法识别 arXiv ID")
            self.ui.set_mini_status("ID error", "error")
            self._done()
            return

        self.ui.add_log(f"[INFO] 处理论文: {arxiv_id}")

        # redirect stdout from core functions to ui log
        class LogWriter(io.StringIO):
            def write(self_, s):
                s = s.rstrip()
                if not s:
                    return
                self.ui.add_log(s)
                if "Downloading" in s and "%" in s:
                    self.ui.set_mini_status("downloading...", "info")
                elif "Download complete" in s:
                    self.ui.set_mini_status("downloaded", "ok")
                elif "Extracting" in s:
                    self.ui.set_mini_status("extracting...", "info")
                elif "Expanding" in s:
                    self.ui.set_mini_status("expanding...", "info")
                elif "Parsing body" in s:
                    self.ui.set_mini_status("parsing...", "info")
                elif "Already cached" in s:
                    self.ui.set_mini_status("cached", "info")
                elif "[OK]" in s and "saved" in s:
                    self.ui.set_mini_status("done", "ok")
            def flush(self_): pass

        old_stdout = sys.stdout
        sys.stdout = LogWriter()
        try:
            paper_dir, folder_name = download_source(arxiv_id, downloads_dir)
            if paper_dir:
                result = extract_body_from_dir(paper_dir, outputs_dir, folder_name)
                if result:
                    self.output_dir = outputs_dir / folder_name
        finally:
            sys.stdout = old_stdout

        if self.output_dir:
            self._load_preview()
            self.ui.set_mini_status("done", "ok")
        self._done()

    def _done(self):
        self.ui.set_run_busy(False)
        if self.output_dir:
            self.ui.set_buttons_enabled(True)
