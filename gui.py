import flet as ft
import threading
import sys
import io
import re
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from arxivcat import extract_arxiv_id, download_source, extract_body_from_dir

VERSION = "v0.2.0"
AUTHOR  = "by MikeDuke"


def main(page: ft.Page):
    page.title = "ArxivCat"
    page.window.width  = 780
    page.window.height = 660
    page.window.min_width  = 560
    page.window.min_height = 480
    page.bgcolor = "#1e1e2e"
    page.padding = 0
    page.fonts = {"Consolas": "Consolas"}
    page.theme = ft.Theme(font_family="Consolas")

    # ── 启动时清理 downloads/ 缓存（超过 50MB 则清空）─────────
    import os
    _base = Path(os.environ.get("APPDATA", Path.home())) / "ArxivCat"
    _downloads = _base / "downloads"
    if _downloads.exists():
        _size = sum(f.stat().st_size for f in _downloads.rglob("*") if f.is_file())
        if _size > 50 * 1024 * 1024:
            shutil.rmtree(_downloads)
            _downloads.mkdir(parents=True, exist_ok=True)

    # ── 状态 ──────────────────────────────────────────────────
    output_dir: Path | None = None
    body_content    = ""
    appendix_content = ""
    clipboard = ft.Clipboard()
    page.services.append(clipboard)
    page.update()

    # ── 颜色 ──────────────────────────────────────────────────
    BG      = "#1e1e2e"
    PANEL   = "#2a2a3e"
    ACCENT  = "#89b4fa"
    TEXT    = "#cdd6f4"
    MUTED   = "#6c7086"
    SUCCESS = "#a6e3a1"
    ERROR   = "#f38ba8"
    BTN     = "#313244"

    # ── 控件 ──────────────────────────────────────────────────
    url_field = ft.TextField(
        hint_text="paste an arXiv URL or ID",
        hint_style=ft.TextStyle(color=MUTED),
        bgcolor=PANEL,
        color=TEXT,
        cursor_color=ACCENT,
        border_color=MUTED,
        focused_border_color=ACCENT,
        border_radius=6,
        text_style=ft.TextStyle(font_family="Consolas", size=12),
        expand=True,
        height=42,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
    )

    mini_status = ft.Text("", color=MUTED, size=12, font_family="Consolas")

    log_view = ft.ListView(
        expand=False,
        height=220,
        spacing=0,
        auto_scroll=True,
    )
    log_container = ft.Container(
        content=log_view,
        bgcolor=PANEL,
        border_radius=6,
        padding=8,
    )
    log_label = ft.Text("log", color=MUTED, size=11, font_family="Consolas")
    log_section = ft.Column(
        controls=[
            log_label,
            ft.Container(height=2),
            log_container,
        ],
        spacing=0,
        visible=False,
    )

    preview_field = ft.TextField(
        value="",
        multiline=True,
        expand=True,
        bgcolor="transparent",
        color=TEXT,
        cursor_color=ACCENT,
        border_color="transparent",
        focused_border_color="transparent",
        border_radius=6,
        text_style=ft.TextStyle(font_family="Consolas", size=11),
        min_lines=10,
        shift_enter=True,
    )

    view_label   = ft.Text("body.tex",  color=MUTED, size=11, font_family="Consolas")
    word_count   = ft.Text("", color=MUTED, size=11, font_family="Consolas")
    status_text  = ft.Text("", color=MUTED, size=11, font_family="Consolas")

    run_txt = ft.Text("Run", font_family="Consolas", weight=ft.FontWeight.BOLD, size=11, color="#1e1e2e")
    run_btn = ft.Container(
        content=run_txt,
        bgcolor=ACCENT,
        border_radius=6,
        padding=ft.Padding.symmetric(horizontal=20, vertical=10),
        height=42,
        ink=True,
    )
    run_btn._disabled = False

    def _run_hover(e):
        if not run_btn._disabled:
            run_btn.bgcolor = "#74c7ec" if e.data == "true" else ACCENT
            run_btn.update()

    run_btn.on_hover = _run_hover
    # run_btn.on_click already bound at construction

    view_dd = ft.Dropdown(
        value="body",
        options=[ft.dropdown.Option("body"), ft.dropdown.Option("appendix")],
        bgcolor=PANEL,
        color=TEXT,
        border_color=MUTED,
        focused_border_color=ACCENT,
        border_radius=6,
        text_style=ft.TextStyle(font_family="Consolas", size=11),
        width=120,
        height=40,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=4),
    )

    show_log_chk = ft.Checkbox(
        label="show log",
        value=False,
        active_color=ACCENT,
        label_style=ft.TextStyle(color=MUTED, size=12, font_family="Consolas"),
        on_change=lambda e: on_show_log(e),
    )

    def make_btn(label, on_click, disabled=True):
        txt = ft.Text(label, font_family="Consolas", size=10, color=TEXT)
        c = ft.Container(
            content=ft.Row(
                controls=[txt],
                tight=True,
            ),
            bgcolor=BTN,
            border_radius=6,
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            on_click=None,
            expand=False,
            ink=True,
        )
        c._label = label
        c._txt = txt
        c._disabled = disabled
        c._on_click = on_click

        def _hover(e):
            if not c._disabled:
                c.bgcolor = "#45475a" if e.data == "true" else BTN
                c.update()

        def _click(e):
            if not c._disabled:
                c._on_click(e)

        c.on_hover = _hover
        c.on_click = _click
        if disabled:
            txt.color = MUTED
        return c

    def set_btn_disabled(btn, disabled):
        btn._disabled = disabled
        btn._txt.color = MUTED if disabled else TEXT
        btn.update()

    copy_btn           = make_btn("Copy",            lambda e: on_copy(e))
    overwrite_btn      = make_btn("Overwrite",          lambda e: on_overwrite(e))
    open_btn           = make_btn("Open Folder",        lambda e: on_open_folder(e))
    strip_comments_btn = make_btn("Strip Comments",     lambda e: on_strip_comments(e))

    # ── 헬퍼 ──────────────────────────────────────────────────

    def set_buttons_enabled(enabled: bool):
        for btn in [copy_btn, overwrite_btn, open_btn, strip_comments_btn]:
            set_btn_disabled(btn, not enabled)
        page.update()

    def update_word_count():
        content = preview_field.value or ""
        words = len(content.split())
        chars = len(content)
        word_count.value = f"{words} words  {chars} chars"
        page.update()

    def add_log(msg: str):
        if msg.startswith("[OK]"):
                color = SUCCESS
        elif msg.startswith("[ERROR]"):
                color = ERROR
        else:
                color = TEXT
        log_view.controls.append(
            ft.Text(msg, color=color, size=11, font_family="Consolas", selectable=True)
        )
        page.update()

    def set_mini(msg, color=MUTED):
        mini_status.value = msg
        mini_status.color = color
        page.update()

    def show_status(msg, duration=2000):
        status_text.value = msg
        page.update()
        def clear():
            import time; time.sleep(duration / 1000)
            status_text.value = ""
            page.update()
        threading.Thread(target=clear, daemon=True).start()

    def load_preview():
        nonlocal output_dir
        if not output_dir:
            return
        view = view_dd.value
        path = output_dir / f"{view}.tex"
        if path.exists():
            preview_field.value = path.read_text(encoding="utf-8")
        else:
            preview_field.value = "(file not found)"
        view_label.value = f"{view}.tex"
        update_word_count()
        page.update()

    # ── 事件 ──────────────────────────────────────────────────

    def on_view_change(e):
        load_preview()

    def on_show_log(e):
        log_section.visible = show_log_chk.value
        page.update()

    def on_copy(e):
        async def _copy():
            await clipboard.set(preview_field.value or "")
        page.run_task(_copy)
        show_status(f"Copied {view_dd.value}.tex!")

    def on_overwrite(e):
        nonlocal output_dir
        if not output_dir:
            return
        view = view_dd.value
        path = output_dir / f"{view}.tex"
        path.write_text(preview_field.value or "", encoding="utf-8")
        show_status(f"Saved {view}.tex")

    def on_open_folder(e):
        if output_dir and output_dir.exists():
            subprocess.Popen(f'explorer "{output_dir}"')

    def on_strip_comments(e):
        content = preview_field.value or ""
        stripped = re.sub(r'(?<!\\)%.*', '', content)
        stripped = re.sub(r'\n{3}', '\n\n', stripped).strip()
        preview_field.value = stripped
        update_word_count()
        show_status("Comments stripped")

    def on_run(e):
        nonlocal output_dir
        url = url_field.value.strip() if url_field.value else ""
        if not url:
            return
        run_btn._disabled = True
        run_btn.bgcolor = MUTED
        run_btn.update()
        set_buttons_enabled(False)
        output_dir = None
        log_view.controls.clear()
        preview_field.value = ""
        word_count.value = ""
        mini_status.value = ""
        page.update()
        threading.Thread(target=process, args=(url,), daemon=True).start()

    def process(url: str):
        nonlocal output_dir
        import os
        base = Path(os.environ.get("APPDATA", Path.home())) / "ArxivCat"
        downloads_dir = base / "downloads"
        outputs_dir   = base / "outputs"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        outputs_dir.mkdir(parents=True, exist_ok=True)

        arxiv_id = extract_arxiv_id(url)
        if not arxiv_id:
            add_log("[ERROR] 无法识别 arXiv ID")
            set_mini("ID error", ERROR)
            done()
            return

        add_log(f"[INFO] 处理论文: {arxiv_id}")

        class LogWriter(io.StringIO):
            def write(self_, s):
                if not s.strip():
                    return
                add_log(s.rstrip())
                if "Downloading..." in s or "Downloading" in s and "%" in s:
                    set_mini("downloading...", MUTED)
                elif "Download complete" in s:
                    set_mini("downloaded", SUCCESS)
                elif "Extracting" in s:
                    set_mini("extracting...", MUTED)
                elif "Expanding" in s:
                    set_mini("expanding...", MUTED)
                elif "Parsing body" in s:
                    set_mini("parsing...", MUTED)
                elif "Already cached" in s:
                    set_mini("cached", MUTED)
                elif "[OK]" in s and "saved" in s:
                    set_mini("done", SUCCESS)
            def flush(self_): pass

        old_stdout = sys.stdout
        sys.stdout = LogWriter()
        try:
            paper_dir, folder_name = download_source(arxiv_id, downloads_dir)
            if paper_dir:
                result = extract_body_from_dir(paper_dir, outputs_dir, folder_name)
                if result:
                    output_dir = outputs_dir / folder_name
        finally:
            sys.stdout = old_stdout

        if output_dir:
            page.run_thread(load_preview)
            set_mini("done", SUCCESS)
        done()

    def done():
        run_btn._disabled = False
        run_btn.bgcolor = ACCENT
        run_btn.update()
        if output_dir:
            set_buttons_enabled(True)
        page.update()

    # ── preview 字数实时更新 ───────────────────────────────────
    def on_preview_change(e):
        update_word_count()

    preview_field.on_change = on_preview_change
    view_dd.on_select       = on_view_change
    show_log_chk.on_change  = on_show_log
    run_btn.on_click        = on_run
    url_field.on_submit     = on_run
    url_field.on_submit     = on_run

    # ── 布局 ──────────────────────────────────────────────────
    page.add(
        ft.Container(
            expand=True,
            bgcolor=BG,
            padding=ft.Padding.only(left=24, right=24, top=18, bottom=14),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    # 标题行
                    ft.Row(
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                        controls=[
                            ft.Text("ArxivCat", color=ACCENT, size=20,
                                    font_family="Consolas", weight=ft.FontWeight.BOLD),
                            ft.Text(AUTHOR,  color=MUTED, size=11, font_family="Consolas"),
                            ft.Text(VERSION, color=MUTED, size=11, font_family="Consolas"),
                        ]
                    ),
                    ft.Container(height=10),
                    # 输入行
                    ft.Row(
                        spacing=8,
                        controls=[url_field, run_btn]
                    ),
                    ft.Container(height=6),
                    # 控制栏
                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            view_dd,
                            show_log_chk,
                            ft.Container(expand=True),
                            mini_status,
                        ]
                    ),
                    ft.Container(height=6),
                    # log（默认隐藏）
                    log_section,
                    # preview header
                    ft.Row(
                        controls=[
                            view_label,
                            ft.Container(expand=True),
                            word_count,
                        ]
                    ),
                    ft.Container(height=2),
                    # 预览区
                    ft.Container(
                        expand=True,
                        bgcolor=PANEL,
                        border_radius=6,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                        content=preview_field,
                    ),
                    ft.Container(height=8),
                    # 底部按钮行
                    ft.Row(
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            copy_btn,
                            overwrite_btn,
                            open_btn,
                            strip_comments_btn,
                            ft.Container(expand=True),
                            status_text,
                        ]
                    ),
                ]
            )
        )
    )


if __name__ == "__main__":
    ft.run(main)
