"""Flet UI backend."""
from __future__ import annotations

import threading
import flet as ft

from arxivcat.presenter import Presenter, VERSION, AUTHOR


class FletApp:
    # ── colours ───────────────────────────────────────────────
    BG      = "#1e1e2e"
    PANEL   = "#2a2a3e"
    ACCENT  = "#89b4fa"
    TEXT    = "#cdd6f4"
    MUTED   = "#6c7086"
    SUCCESS = "#a6e3a1"
    ERROR   = "#f38ba8"
    BTN     = "#313244"

    def __init__(self):
        self._presenter = Presenter(self)
        self._page: ft.Page | None = None
        self._output_dir = None

    # ── UIProtocol ────────────────────────────────────────────

    def add_log(self, msg: str) -> None:
        if msg.startswith("[OK]"):
            color = self.SUCCESS
        elif msg.startswith("[ERROR]"):
            color = self.ERROR
        else:
            color = self.TEXT
        self._log_view.controls.append(
            ft.Text(msg, color=color, size=11, font_family="Consolas", selectable=True)
        )
        if self._page:
            self._page.update()

    def set_mini_status(self, msg: str, level: str = "info") -> None:
        color = {"ok": self.SUCCESS, "error": self.ERROR}.get(level, self.MUTED)
        self._mini_status.value = msg
        self._mini_status.color = color
        if self._page:
            self._page.update()

    def set_preview(self, content: str, label: str) -> None:
        self._preview_field.value = content
        if label:
            self._view_label.value = label
        self._update_word_count()
        if self._page:
            self._page.update()

    def set_buttons_enabled(self, enabled: bool) -> None:
        for btn in [self._copy_btn, self._overwrite_btn,
                    self._open_btn, self._strip_btn]:
            self._set_btn_disabled(btn, not enabled)
        if self._page:
            self._page.update()

    def set_run_busy(self, busy: bool) -> None:
        self._run_btn._disabled = busy
        self._run_btn.bgcolor = self.MUTED if busy else self.ACCENT
        self._run_btn.update()

    def show_toast(self, msg: str, duration_ms: int = 2000) -> None:
        self._status_text.value = msg
        if self._page:
            self._page.update()
        def _clear():
            import time
            time.sleep(duration_ms / 1000)
            self._status_text.value = ""
            if self._page:
                self._page.update()
        threading.Thread(target=_clear, daemon=True).start()

    def get_url_input(self) -> str:
        return self._url_field.value or ""

    def get_view_mode(self) -> str:
        return self._view_dd.value or "body"

    def get_preview_text(self) -> str:
        return self._preview_field.value or ""

    def clear_log(self) -> None:
        self._log_view.controls.clear()
        if self._page:
            self._page.update()

    def run(self) -> None:
        ft.app(target=self._build)

    # ── internal helpers ──────────────────────────────────────

    def _update_word_count(self):
        content = self._preview_field.value or ""
        words = len(content.split())
        chars = len(content)
        self._word_count.value = f"{words} words  {chars} chars"
        if self._page:
            self._page.update()

    def _make_btn(self, label: str, on_click, disabled: bool = True):
        txt = ft.Text(label, font_family="Consolas", size=10, color=self.TEXT)
        c = ft.Container(
            content=ft.Row(controls=[txt], tight=True),
            bgcolor=self.BTN,
            border_radius=6,
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            ink=True,
        )
        c._label   = label
        c._txt     = txt
        c._disabled = disabled
        c._on_click = on_click

        def _hover(e):
            if not c._disabled:
                c.bgcolor = "#45475a" if e.data == "true" else self.BTN
                c.update()

        def _click(e):
            if not c._disabled:
                c._on_click(e)

        c.on_hover = _hover
        c.on_click = _click
        if disabled:
            txt.color = self.MUTED
        return c

    def _set_btn_disabled(self, btn, disabled: bool):
        btn._disabled = disabled
        btn._txt.color = self.MUTED if disabled else self.TEXT
        btn.update()

    # ── build ─────────────────────────────────────────────────

    def _build(self, page: ft.Page):
        self._page = page
        page.title = "ArxivCat"
        page.window.width       = 780
        page.window.height      = 660
        page.window.min_width   = 560
        page.window.min_height  = 480
        page.bgcolor            = self.BG
        page.padding            = 0
        page.fonts              = {"Consolas": "Consolas"}
        page.theme              = ft.Theme(font_family="Consolas")

        clipboard = ft.Clipboard()
        page.services.append(clipboard)
        page.update()

        # ── widgets ───────────────────────────────────────────
        self._url_field = ft.TextField(
            hint_text="paste an arXiv URL or ID",
            hint_style=ft.TextStyle(color=self.MUTED),
            bgcolor=self.PANEL,
            color=self.TEXT,
            cursor_color=self.ACCENT,
            border_color=self.MUTED,
            focused_border_color=self.ACCENT,
            border_radius=6,
            text_style=ft.TextStyle(font_family="Consolas", size=12),
            expand=True,
            height=42,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        )

        self._mini_status = ft.Text("", color=self.MUTED, size=12, font_family="Consolas")

        self._log_view = ft.ListView(
            expand=False, height=220, spacing=0, auto_scroll=True,
        )
        log_container = ft.Container(
            content=self._log_view,
            bgcolor=self.PANEL,
            border_radius=6,
            padding=8,
        )
        self._log_section = ft.Column(
            controls=[
                ft.Text("log", color=self.MUTED, size=11, font_family="Consolas"),
                ft.Container(height=2),
                log_container,
            ],
            spacing=0,
            visible=False,
        )

        self._preview_field = ft.TextField(
            value="",
            multiline=True,
            expand=True,
            bgcolor="transparent",
            color=self.TEXT,
            cursor_color=self.ACCENT,
            border_color="transparent",
            focused_border_color="transparent",
            border_radius=6,
            text_style=ft.TextStyle(font_family="Consolas", size=11),
            min_lines=10,
            shift_enter=False,
            on_change=lambda e: self._update_word_count(),
        )

        self._view_label  = ft.Text("body.tex",  color=self.MUTED, size=11, font_family="Consolas")
        self._word_count  = ft.Text("",           color=self.MUTED, size=11, font_family="Consolas")
        self._status_text = ft.Text("",           color=self.MUTED, size=11, font_family="Consolas")

        run_txt = ft.Text("Run", font_family="Consolas",
                          weight=ft.FontWeight.BOLD, size=11, color="#1e1e2e")
        self._run_btn = ft.Container(
            content=run_txt,
            bgcolor=self.ACCENT,
            border_radius=6,
            padding=ft.Padding.symmetric(horizontal=20, vertical=10),
            height=42,
            ink=True,
        )
        self._run_btn._disabled = False

        def _run_hover(e):
            if not self._run_btn._disabled:
                self._run_btn.bgcolor = "#74c7ec" if e.data == "true" else self.ACCENT
                self._run_btn.update()

        self._run_btn.on_hover = _run_hover
        self._run_btn.on_click = lambda e: self._presenter.run_fetch()

        self._view_dd = ft.Dropdown(
            value="body",
            options=[ft.dropdown.Option("body"), ft.dropdown.Option("appendix")],
            bgcolor=self.PANEL,
            color=self.TEXT,
            border_color=self.MUTED,
            focused_border_color=self.ACCENT,
            border_radius=6,
            text_style=ft.TextStyle(font_family="Consolas", size=11),
            width=120,
            height=40,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            on_select=lambda e: self._presenter.switch_view(),
        )

        show_log_chk = ft.Checkbox(
            label="show log",
            value=False,
            active_color=self.ACCENT,
            label_style=ft.TextStyle(color=self.MUTED, size=12, font_family="Consolas"),
            on_change=lambda e: self._toggle_log(e),
        )

        self._copy_btn      = self._make_btn("Copy",           lambda e: self._on_copy(clipboard))
        self._overwrite_btn = self._make_btn("Overwrite",      lambda e: self._presenter.overwrite_file())
        self._open_btn      = self._make_btn("Open Folder",    lambda e: self._presenter.open_folder())
        self._strip_btn     = self._make_btn("Strip Comments", lambda e: self._presenter.strip_comments())

        self._url_field.on_submit = lambda e: self._presenter.run_fetch()

        # ── layout ────────────────────────────────────────────
        page.add(
            ft.Container(
                expand=True,
                bgcolor=self.BG,
                padding=ft.Padding.only(left=24, right=24, top=18, bottom=14),
                content=ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[
                        ft.Row(
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                            controls=[
                                ft.Text("ArxivCat", color=self.ACCENT, size=20,
                                        font_family="Consolas", weight=ft.FontWeight.BOLD),
                                ft.Text(AUTHOR,  color=self.MUTED, size=11, font_family="Consolas"),
                                ft.Text(VERSION, color=self.MUTED, size=11, font_family="Consolas"),
                            ]
                        ),
                        ft.Container(height=10),
                        ft.Row(spacing=8, controls=[self._url_field, self._run_btn]),
                        ft.Container(height=6),
                        ft.Row(
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                self._view_dd,
                                show_log_chk,
                                ft.Container(expand=True),
                                self._mini_status,
                            ]
                        ),
                        ft.Container(height=6),
                        self._log_section,
                        ft.Row(controls=[
                            self._view_label,
                            ft.Container(expand=True),
                            self._word_count,
                        ]),
                        ft.Container(height=2),
                        ft.Container(
                            expand=True,
                            bgcolor=self.PANEL,
                            border_radius=6,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                            content=self._preview_field,
                        ),
                        ft.Container(height=8),
                        ft.Row(
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            wrap=False,
                            controls=[
                                self._copy_btn,
                                self._overwrite_btn,
                                self._open_btn,
                                self._strip_btn,
                                ft.Container(expand=True),
                                self._status_text,
                            ]
                        ),
                    ]
                )
            )
        )

    def _toggle_log(self, e):
        self._log_section.visible = e.control.value
        if self._page:
            self._page.update()

    def _on_copy(self, clipboard):
        async def _do():
            await clipboard.set(self._preview_field.value or "")
        if self._page:
            self._page.run_task(_do)
        self.show_toast(f"Copied {self._view_dd.value}.tex!")
