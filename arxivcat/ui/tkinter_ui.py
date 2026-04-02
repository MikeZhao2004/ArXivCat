"""Tkinter UI backend – dark Catppuccin theme, mirrors the Flet layout."""
from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from tkinter import ttk
from typing import Callable

from arxivcat.presenter import Presenter, VERSION, AUTHOR

# ── palette (Catppuccin Mocha) ────────────────────────────────
BG      = "#1e1e2e"
PANEL   = "#2a2a3e"
ACCENT  = "#89b4fa"
TEXT    = "#cdd6f4"
MUTED   = "#6c7086"
SUCCESS = "#a6e3a1"
ERROR   = "#f38ba8"
BTN     = "#313244"
BTN_HOV = "#45475a"
RUN_HOV = "#74c7ec"


def _enable_windows_dpi(root: tk.Tk) -> None:
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    try:
        dpi = ctypes.windll.user32.GetDpiForWindow(root.winfo_id())
        if dpi > 0:
            root.tk.call("tk", "scaling", dpi / 72.0)
    except Exception:
        pass


class _FlatButton(tk.Label):
    """Clickable label styled like the Flet container buttons."""

    def __init__(self, parent, text: str, command: Callable, **kw):
        super().__init__(
            parent, text=text,
            bg=BTN, fg=MUTED,
            font=("Consolas", 9),
            padx=14, pady=6,
            cursor="hand2", **kw,
        )
        self._command = command
        self._enabled = False
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self.config(fg=TEXT if enabled else MUTED)

    def _on_enter(self, _):
        if self._enabled:
            self.config(bg=BTN_HOV)

    def _on_leave(self, _):
        self.config(bg=BTN)

    def _on_click(self, _):
        if self._enabled:
            self._command()


class _RunButton(tk.Label):
    """Accent-coloured Run button."""

    def __init__(self, parent, command: Callable):
        super().__init__(
            parent, text="Run",
            bg=ACCENT, fg=BG,
            font=("Consolas", 10, "bold"),
            padx=20, pady=8,
            cursor="hand2",
        )
        self._command = command
        self._busy = False
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def set_busy(self, busy: bool):
        self._busy = busy
        self.config(bg=MUTED if busy else ACCENT,
                    cursor="watch" if busy else "hand2")

    def _on_enter(self, _):
        if not self._busy:
            self.config(bg=RUN_HOV)

    def _on_leave(self, _):
        self.config(bg=MUTED if self._busy else ACCENT)

    def _on_click(self, _):
        if not self._busy:
            self._command()


class TkApp:
    """Tkinter implementation of UIProtocol."""

    def __init__(self):
        self._toast_after = None
        self._log_visible = False
        self._build()
        self._presenter = Presenter(self)

    # ── UIProtocol ────────────────────────────────────────────

    def add_log(self, msg: str) -> None:
        color = SUCCESS if msg.startswith("[OK]") else ERROR if msg.startswith("[ERROR]") else TEXT
        self._log_text.config(state="normal")
        self._log_text.insert("end", msg + "\n", (color,))
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def set_mini_status(self, msg: str, level: str = "info") -> None:
        color = {"ok": SUCCESS, "error": ERROR}.get(level, MUTED)
        self._root.after(0, lambda: (
            self._mini_var.set(msg),
            self._mini_lbl.config(fg=color),
        ))

    def set_preview(self, content: str, label: str) -> None:
        def _do():
            self._preview.config(state="normal")
            self._preview.delete("1.0", "end")
            self._preview.insert("1.0", content)
            if label:
                self._view_label_var.set(label)
            self._update_word_count()
        self._root.after(0, _do)

    def set_buttons_enabled(self, enabled: bool) -> None:
        self._root.after(0, lambda: [
            b.set_enabled(enabled)
            for b in (self._copy_btn, self._overwrite_btn,
                      self._open_btn, self._strip_btn)
        ])

    def set_run_busy(self, busy: bool) -> None:
        self._root.after(0, lambda: self._run_btn.set_busy(busy))

    def show_toast(self, msg: str, duration_ms: int = 2000) -> None:
        def _do():
            self._toast_var.set(msg)
            if self._toast_after:
                self._root.after_cancel(self._toast_after)
            self._toast_after = self._root.after(
                duration_ms, lambda: self._toast_var.set(""))
        self._root.after(0, _do)

    def get_url_input(self) -> str:
        v = self._url_var.get().strip()
        return "" if v == self._placeholder else v

    def get_view_mode(self) -> str:
        return self._view_var.get()

    def get_preview_text(self) -> str:
        return self._preview.get("1.0", "end-1c")

    def clear_log(self) -> None:
        self._root.after(0, lambda: (
            self._log_text.config(state="normal"),
            self._log_text.delete("1.0", "end"),
            self._log_text.config(state="disabled"),
        ))

    def run(self) -> None:
        self._root.mainloop()

    # ── internal helpers ──────────────────────────────────────

    def _update_word_count(self):
        content = self.get_preview_text()
        self._wc_var.set(f"{len(content.split())} words  {len(content)} chars")

    def _toggle_log(self):
        if self._log_visible:
            self._log_frame.pack_forget()
            self._log_visible = False
        else:
            self._log_frame.pack(fill="x", side="top", after=self._ctrl_row, pady=(0, 4))
            self._log_visible = True

    def _on_view_change(self, *_):
        self._presenter.switch_view()

    def _on_copy(self):
        self._root.clipboard_clear()
        self._root.clipboard_append(self.get_preview_text())
        self.show_toast(f"Copied {self.get_view_mode()}.tex!")

    # ── build ─────────────────────────────────────────────────

    def _build(self):
        root = tk.Tk()
        _enable_windows_dpi(root)
        root.title("ArxivCat")
        root.geometry("780x660")
        root.minsize(560, 480)
        root.configure(bg=BG)
        self._root = root

        outer = tk.Frame(root, bg=BG)
        outer.pack(fill="both", expand=True, padx=24, pady=(18, 14))
        self._main_col = outer

        title_row = tk.Frame(outer, bg=BG)
        title_row.pack(fill="x")
        tk.Label(title_row, text="ArxivCat", bg=BG, fg=ACCENT,
                 font=("Consolas", 16, "bold")).pack(side="left")
        tk.Label(title_row, text=f"  {AUTHOR}  {VERSION}",
                 bg=BG, fg=MUTED, font=("Consolas", 9)).pack(side="left", pady=(4, 0))

        tk.Frame(outer, bg=BG, height=10).pack(fill="x")

        input_row = tk.Frame(outer, bg=BG)
        input_row.pack(fill="x")
        input_row.columnconfigure(0, weight=1)

        self._placeholder = "paste an arXiv URL or ID"
        self._url_var = tk.StringVar()
        url_entry = tk.Entry(
            input_row,
            textvariable=self._url_var,
            bg=PANEL, fg=MUTED,
            insertbackground=ACCENT,
            relief="flat",
            font=("Consolas", 11),
            bd=0,
        )
        url_entry.grid(row=0, column=0, sticky="ew", ipady=8, padx=(0, 8))
        url_entry.insert(0, self._placeholder)

        def _focus_in(e):
            if url_entry.get() == self._placeholder:
                url_entry.delete(0, "end")
                url_entry.config(fg=TEXT)

        def _focus_out(e):
            if not url_entry.get():
                url_entry.insert(0, self._placeholder)
                url_entry.config(fg=MUTED)

        url_entry.bind("<FocusIn>", _focus_in)
        url_entry.bind("<FocusOut>", _focus_out)
        url_entry.bind("<Return>", lambda e: self._presenter.run_fetch())

        self._run_btn = _RunButton(input_row, command=lambda: self._presenter.run_fetch())
        self._run_btn.grid(row=0, column=1)

        tk.Frame(outer, bg=BG, height=6).pack(fill="x")

        ctrl_row = tk.Frame(outer, bg=BG)
        ctrl_row.pack(fill="x")
        self._ctrl_row = ctrl_row

        self._view_var = tk.StringVar(value="body")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "AC.TCombobox",
            fieldbackground=PANEL,
            background=PANEL,
            foreground=TEXT,
            selectbackground=PANEL,
            selectforeground=TEXT,
            arrowcolor=MUTED,
            bordercolor=MUTED,
            lightcolor=PANEL,
            darkcolor=PANEL,
        )
        style.map(
            "AC.TCombobox",
            fieldbackground=[("readonly", PANEL)],
            foreground=[("readonly", TEXT)],
        )
        ttk.Combobox(
            ctrl_row,
            textvariable=self._view_var,
            values=["body", "appendix"],
            state="readonly",
            width=10,
            font=("Consolas", 10),
            style="AC.TCombobox",
        ).pack(side="left")
        self._view_var.trace_add("write", self._on_view_change)

        show_log_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            ctrl_row,
            text="show log",
            variable=show_log_var,
            bg=BG,
            fg=MUTED,
            activebackground=BG,
            activeforeground=TEXT,
            selectcolor=BG,
            font=("Consolas", 9),
            command=self._toggle_log,
        ).pack(side="left", padx=(10, 0))

        self._mini_var = tk.StringVar()
        self._mini_lbl = tk.Label(
            ctrl_row,
            textvariable=self._mini_var,
            bg=BG,
            fg=MUTED,
            font=("Consolas", 10),
        )
        self._mini_lbl.pack(side="right")

        tk.Frame(outer, bg=BG, height=4).pack(fill="x")

        log_wrap = tk.Frame(outer, bg=PANEL, pady=4, padx=6)
        self._log_frame = log_wrap

        self._log_text = tk.Text(
            log_wrap,
            bg=PANEL,
            fg=TEXT,
            font=("Consolas", 9),
            height=10,
            relief="flat",
            state="disabled",
            wrap="word",
        )
        self._log_text.pack(fill="both", expand=True)
        self._log_text.tag_config(SUCCESS, foreground=SUCCESS)
        self._log_text.tag_config(ERROR, foreground=ERROR)
        self._log_text.tag_config(TEXT, foreground=TEXT)

        btn_row = tk.Frame(outer, bg=BG)
        btn_row.pack(fill="x", side="bottom", pady=(8, 0))

        self._copy_btn = _FlatButton(btn_row, "Copy", self._on_copy)
        self._overwrite_btn = _FlatButton(btn_row, "Overwrite", lambda: self._presenter.overwrite_file())
        self._open_btn = _FlatButton(btn_row, "Open Folder", lambda: self._presenter.open_folder())
        self._strip_btn = _FlatButton(btn_row, "Strip Comments", lambda: self._presenter.strip_comments())

        for b in (self._copy_btn, self._overwrite_btn, self._open_btn, self._strip_btn):
            b.pack(side="left", padx=(0, 6))

        self._toast_var = tk.StringVar()
        tk.Label(btn_row, textvariable=self._toast_var,
                 bg=BG, fg=MUTED, font=("Consolas", 9)).pack(side="right")

        tk.Frame(outer, bg=BG, height=2).pack(fill="x", side="top")
        self._preview_header = tk.Frame(outer, bg=BG)
        self._preview_header.pack(fill="x", side="top")
        self._view_label_var = tk.StringVar(value="body.tex")
        tk.Label(self._preview_header, textvariable=self._view_label_var,
                 bg=BG, fg=MUTED, font=("Consolas", 9)).pack(side="left")
        self._wc_var = tk.StringVar()
        tk.Label(self._preview_header, textvariable=self._wc_var,
                 bg=BG, fg=MUTED, font=("Consolas", 9)).pack(side="right")

        preview_wrap = tk.Frame(outer, bg=PANEL)
        preview_wrap.pack(fill="both", expand=True)

        preview_scroll = tk.Scrollbar(preview_wrap, bg=PANEL,
                                      troughcolor=PANEL, activebackground=BTN_HOV)
        preview_scroll.pack(side="right", fill="y")

        self._preview = tk.Text(
            preview_wrap,
            bg=PANEL,
            fg=TEXT,
            insertbackground=ACCENT,
            font=("Consolas", 10),
            relief="flat",
            wrap="word",
            yscrollcommand=preview_scroll.set,
            padx=8,
            pady=6,
            undo=True,
        )
        self._preview.pack(fill="both", expand=True)
        preview_scroll.config(command=self._preview.yview)
        self._preview.bind("<KeyRelease>", lambda e: self._update_word_count())
