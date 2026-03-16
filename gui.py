import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import subprocess
import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from arxivcat import extract_arxiv_id, download_source, extract_body_from_dir


BG      = "#1e1e2e"
PANEL   = "#2a2a3e"
ACCENT  = "#89b4fa"
TEXT    = "#cdd6f4"
MUTED   = "#6c7086"
SUCCESS = "#a6e3a1"
ERROR   = "#f38ba8"
BTN     = "#313244"


class ArxivCatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ArxivCat")
        self.root.geometry("760x620")
        self.root.resizable(True, True)
        self.root.configure(bg=BG)
        self.output_dir = None
        self._build_ui()

    def _build_ui(self):
        # ── 顶部：标题 + 输入 ──────────────────────────────────
        top = tk.Frame(self.root, bg=BG, padx=20, pady=14)
        top.pack(fill="x")

        tk.Label(top, text="ArxivCat", bg=BG, fg=ACCENT,
                 font=("Consolas", 17, "bold")).pack(anchor="w")
        tk.Label(top, text="paste an arXiv URL or ID", bg=BG, fg=MUTED,
                 font=("Consolas", 9)).pack(anchor="w")

        row = tk.Frame(top, bg=BG, pady=8)
        row.pack(fill="x")

        self.url_var = tk.StringVar()
        self.entry = tk.Entry(
            row, textvariable=self.url_var,
            bg=PANEL, fg=TEXT, insertbackground=ACCENT,
            relief="flat", font=("Consolas", 11),
            highlightthickness=1, highlightbackground=MUTED,
            highlightcolor=ACCENT
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.entry.bind("<Return>", lambda e: self._run())

        self.run_btn = tk.Button(
            row, text="  Run  ",
            bg=ACCENT, fg="#1e1e2e", activebackground="#74c7ec",
            font=("Consolas", 10, "bold"), relief="flat",
            cursor="hand2", command=self._run
        )
        self.run_btn.pack(side="left", padx=(8, 0), ipady=6, ipadx=4)

        # ── 控制栏：下拉 + log开关 + 状态提示 ──────────────────
        ctrl = tk.Frame(self.root, bg=BG, padx=20, pady=4)
        ctrl.pack(fill="x")

        # combobox 样式
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TCombobox",
                        fieldbackground=PANEL, background=BTN,
                        foreground=TEXT, selectbackground=BTN,
                        selectforeground=TEXT, arrowcolor=MUTED,
                        bordercolor=MUTED, lightcolor=PANEL, darkcolor=PANEL)
        style.map("Dark.TCombobox",
                  fieldbackground=[("readonly", PANEL)],
                  foreground=[("readonly", TEXT)])

        self.view_var = tk.StringVar(value="body")
        self.view_combo = ttk.Combobox(
            ctrl, textvariable=self.view_var,
            values=["body", "appendix"],
            state="readonly", width=10,
            style="Dark.TCombobox",
            font=("Consolas", 10)
        )
        self.view_combo.pack(side="left", ipady=3)
        self.view_combo.bind("<<ComboboxSelected>>", lambda e: self._on_view_change())

        # log 开关
        self.show_log_var = tk.BooleanVar(value=False)
        self.log_chk = tk.Checkbutton(
            ctrl, text="show log",
            variable=self.show_log_var,
            bg=BG, fg=MUTED, selectcolor=PANEL,
            activebackground=BG, activeforeground=TEXT,
            font=("Consolas", 9), cursor="hand2",
            command=self._toggle_log
        )
        self.log_chk.pack(side="left", padx=(10, 0))

        # 右侧状态提示（隐藏log时显示进度）
        self.mini_status = tk.Label(
            ctrl, text="", bg=BG, fg=MUTED,
            font=("Consolas", 9), anchor="e"
        )
        self.mini_status.pack(side="right", fill="x", expand=True, padx=(20, 0))

        # ── 底部：按钮（先pack，始终可见）────────────────────────
        bottom = tk.Frame(self.root, bg=BG, padx=20, pady=10)
        bottom.pack(fill="x", side="bottom")

        self.copy_btn = tk.Button(
            bottom, text="Copy body.tex",
            bg=BTN, fg=TEXT, activebackground="#45475a",
            font=("Consolas", 10), relief="flat",
            cursor="hand2", state="disabled",
            command=self._copy_current
        )
        self.copy_btn.pack(side="left", ipady=5, ipadx=10)

        self.overwrite_btn = tk.Button(
            bottom, text="Overwrite",
            bg=BTN, fg=TEXT, activebackground="#45475a",
            font=("Consolas", 10), relief="flat",
            cursor="hand2", state="disabled",
            command=self._overwrite_file
        )
        self.overwrite_btn.pack(side="left", padx=(8, 0), ipady=5, ipadx=10)

        self.open_btn = tk.Button(
            bottom, text="Open Folder",
            bg=BTN, fg=TEXT, activebackground="#45475a",
            font=("Consolas", 10), relief="flat",
            cursor="hand2", state="disabled",
            command=self._open_folder
        )
        self.open_btn.pack(side="left", padx=(8, 0), ipady=5, ipadx=10)

        # 字数统计（右下角）
        self.word_count_label = tk.Label(
            bottom, text="", bg=BG, fg=MUTED,
            font=("Consolas", 9), anchor="e"
        )
        self.word_count_label.pack(side="right")

        self.status = tk.Label(bottom, text="", bg=BG, fg=MUTED,
                               font=("Consolas", 9))
        self.status.pack(side="right", padx=(0, 12))

        # ── 中部：log（默认隐藏）+ 预览（可伸缩）────────────────
        mid = tk.Frame(self.root, bg=BG, padx=20)
        mid.pack(fill="both", expand=True)

        self.log_label = tk.Label(mid, text="log", bg=BG, fg=MUTED,
                                  font=("Consolas", 8))
        self.log = scrolledtext.ScrolledText(
            mid, bg=PANEL, fg=TEXT,
            font=("Consolas", 9), relief="flat",
            state="disabled", wrap="word",
            highlightthickness=0, height=7
        )
        self.log.tag_config("ok",   foreground=SUCCESS)
        self.log.tag_config("err",  foreground=ERROR)
        self.log.tag_config("info", foreground=TEXT)

        self.preview_label_var = tk.StringVar(value="body.tex")
        self.preview_label = tk.Label(mid, textvariable=self.preview_label_var,
                                      bg=BG, fg=MUTED, font=("Consolas", 8))
        self.preview_label.pack(anchor="w")

        # 预览区（可编辑）
        self.preview = scrolledtext.ScrolledText(
            mid, bg=PANEL, fg=TEXT,
            font=("Consolas", 10), relief="flat",
            wrap="word", highlightthickness=0,
            insertbackground=ACCENT
        )
        self.preview.pack(fill="both", expand=True, pady=(2, 0))
        self.preview.bind("<KeyRelease>", lambda e: self._update_word_count())

    # ── 事件处理 ───────────────────────────────────────────────

    def _toggle_log(self):
        if self.show_log_var.get():
            self.log_label.pack(anchor="w", before=self.preview_label)
            self.log.pack(fill="x", pady=(2, 10), before=self.preview_label)
        else:
            self.log_label.pack_forget()
            self.log.pack_forget()

    def _set_mini_status(self, msg, color=None):
        self.mini_status.configure(text=msg, fg=color or MUTED)

    def _on_view_change(self):
        view = self.view_var.get()
        self.preview_label_var.set(f"{view}.tex")
        self.copy_btn.configure(text=f"Copy {view}.tex")
        if self.output_dir:
            path = self.output_dir / f"{view}.tex"
            self._show_preview(path)

    def _log(self, msg, tag="info"):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _show_preview(self, path):
        self.preview.delete("1.0", "end")
        if path and path.exists():
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                content = "(无法读取文件)"
        else:
            content = "(文件不存在)"
        self.preview.insert("end", content)
        self._update_word_count()

    def _update_word_count(self):
        content = self.preview.get("1.0", "end-1c")
        chars = len(content)
        words = len(content.split())
        self.word_count_label.configure(text=f"{words} words  {chars} chars")

    def _run(self):
        url = self.url_var.get().strip()
        if not url:
            return
        self.run_btn.configure(state="disabled")
        self.copy_btn.configure(state="disabled")
        self.overwrite_btn.configure(state="disabled")
        self.open_btn.configure(state="disabled")
        self.output_dir = None
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.preview.delete("1.0", "end")
        self.word_count_label.configure(text="")
        threading.Thread(target=self._process, args=(url,), daemon=True).start()

    def _process(self, url):
        base = Path(__file__).parent
        downloads_dir = base / "downloads"
        outputs_dir   = base / "outputs"
        downloads_dir.mkdir(exist_ok=True)
        outputs_dir.mkdir(exist_ok=True)

        arxiv_id = extract_arxiv_id(url)
        if not arxiv_id:
            self._log("[ERROR] 无法识别 arXiv ID", "err")
            self.root.after(0, lambda: self._set_mini_status("ID error", ERROR))
            self._done()
            return

        self._log(f"[INFO] 处理论文: {arxiv_id}")

        # mini status 回调
        def mini(msg, color=None):
            self.root.after(0, lambda: self._set_mini_status(msg, color))

        class LogWriter(io.StringIO):
            def write(self_, s):
                if not s.strip():
                    return
                tag = "ok" if s.startswith("[OK]") else \
                      "err" if s.startswith("[ERROR]") else "info"
                self._log(s.rstrip(), tag)
                # 同步 mini status
                if "下载" in s and "中" in s:
                    mini("downloading...")
                elif "下载完成" in s or "下载" in s and "OK" in s:
                    mini("downloaded", SUCCESS)
                elif "解压" in s and "中" in s:
                    mini("extracting...")
                elif "解压完成" in s:
                    mini("extracted", SUCCESS)
                elif "提取" in s and "正文" in s:
                    mini("parsing...")
                elif "已存在" in s:
                    mini("cached", MUTED)
                elif "[OK]" in s and "保存" in s:
                    mini("done", SUCCESS)
            def flush(self_): pass

        old_stdout = sys.stdout
        sys.stdout = LogWriter()
        folder_name = None
        try:
            paper_dir, folder_name = download_source(arxiv_id, downloads_dir)
            if paper_dir:
                result = extract_body_from_dir(paper_dir, outputs_dir, folder_name)
                if result:
                    self.output_dir = outputs_dir / folder_name
        finally:
            sys.stdout = old_stdout

        if self.output_dir:
            view = self.view_var.get()
            path = self.output_dir / f"{view}.tex"
            self.root.after(0, lambda: self._show_preview(path))
            mini("done", SUCCESS)
        self._done()

    def _done(self):
        self.run_btn.configure(state="normal")
        if self.output_dir:
            view = self.view_var.get()
            self.copy_btn.configure(state="normal", text=f"Copy {view}.tex")
            self.overwrite_btn.configure(state="normal")
            self.open_btn.configure(state="normal")

    def _copy_current(self):
        content = self.preview.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        view = self.view_var.get()
        self.status.configure(text=f"Copied {view}.tex!")
        self.root.after(2000, lambda: self.status.configure(text=""))

    def _overwrite_file(self):
        if not self.output_dir:
            return
        view = self.view_var.get()
        path = self.output_dir / f"{view}.tex"
        content = self.preview.get("1.0", "end-1c")
        path.write_text(content, encoding="utf-8")
        self.status.configure(text=f"Saved {view}.tex")
        self.root.after(2000, lambda: self.status.configure(text=""))

    def _open_folder(self):
        if self.output_dir and self.output_dir.exists():
            subprocess.Popen(f'explorer "{self.output_dir}"')


if __name__ == "__main__":
    root = tk.Tk()
    app = ArxivCatGUI(root)
    root.mainloop()
