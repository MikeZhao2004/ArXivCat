"""PyQt6 UI backend - dark Catppuccin theme, mirrors Flet/Tk layout."""
from __future__ import annotations
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPlainTextEdit, QComboBox,
    QCheckBox, QPushButton, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from arxivcat.presenter import Presenter, VERSION, AUTHOR

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

BASE_QSS = (
    f"* {{ font-family: Consolas; color: {TEXT}; }}"
    f"QMainWindow, QWidget#root {{ background: {BG}; }}"
    f"QLineEdit {{ background: {PANEL}; color: {TEXT}; border: 1px solid {MUTED};"
    f"  border-radius: 6px; padding: 6px 10px; font-size: 11pt; }}"
    f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
    f"QPlainTextEdit {{ background: {PANEL}; color: {TEXT}; border: none;"
    f"  border-radius: 6px; font-size: 10pt; padding: 6px 8px; }}"
    f"QTextEdit {{ background: {PANEL}; color: {TEXT}; border: none; font-size: 9pt; }}"
    f"QComboBox {{ background: {PANEL}; color: {TEXT}; border: 1px solid {MUTED};"
    f"  border-radius: 6px; padding: 4px 10px; font-size: 10pt; min-width: 90px; }}"
    f"QComboBox:focus {{ border: 1px solid {ACCENT}; }}"
    f"QComboBox QAbstractItemView {{ background: {PANEL}; color: {TEXT};"
    f"  selection-background-color: {BTN_HOV}; border: 1px solid {MUTED}; }}"
    f"QComboBox::drop-down {{ border: none; }}"
    f"QCheckBox {{ color: {MUTED}; font-size: 9pt; spacing: 6px; }}"
    f"QCheckBox::indicator {{ width: 14px; height: 14px;"
    f"  border: 1px solid {MUTED}; border-radius: 3px; background: {BG}; }}"
    f"QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}"
    f"QScrollBar:vertical {{ background: {PANEL}; width: 8px; margin: 0; border-radius: 4px; }}"
    f"QScrollBar::handle:vertical {{ background: {BTN_HOV}; border-radius: 4px; min-height: 20px; }}"
    f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}"
)


class _Signals(QObject):
    add_log        = pyqtSignal(str)
    set_mini       = pyqtSignal(str, str)
    set_preview    = pyqtSignal(str, str)
    set_btns       = pyqtSignal(bool)
    set_run_busy   = pyqtSignal(bool)
    show_toast_sig = pyqtSignal(str, int)


class _FlatButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setEnabled(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"QPushButton {{ background: {BTN}; color: {MUTED}; border: none;"
            f"  border-radius: 6px; padding: 6px 14px; font-size: 9pt; }}"
            f"QPushButton:enabled {{ color: {TEXT}; }}"
            f"QPushButton:hover:enabled {{ background: {BTN_HOV}; }}"
        )


class _RunButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("Run", parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply(False)

    def _apply(self, busy: bool):
        bg  = MUTED if busy else ACCENT
        hov = MUTED if busy else RUN_HOV
        self.setStyleSheet(
            f"QPushButton {{ background: {bg}; color: {BG}; border: none;"
            f"  border-radius: 6px; padding: 8px 20px;"
            f"  font-size: 10pt; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {hov}; }}"
        )

    def set_busy(self, busy: bool):
        self._apply(busy)
        self.setEnabled(not busy)
        self.setCursor(
            Qt.CursorShape.WaitCursor if busy else Qt.CursorShape.PointingHandCursor
        )


class QtApp:
    def __init__(self):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyleSheet(BASE_QSS)
        self._signals = _Signals()
        self._toast_timer = QTimer()
        self._toast_timer.setSingleShot(True)
        self._build()
        self._connect_signals()
        self._presenter = Presenter(self)

    # UIProtocol
    def add_log(self, msg: str) -> None:
        self._signals.add_log.emit(msg)

    def set_mini_status(self, msg: str, level: str = "info") -> None:
        self._signals.set_mini.emit(msg, level)

    def set_preview(self, content: str, label: str) -> None:
        self._signals.set_preview.emit(content, label)

    def set_buttons_enabled(self, enabled: bool) -> None:
        self._signals.set_btns.emit(enabled)

    def set_run_busy(self, busy: bool) -> None:
        self._signals.set_run_busy.emit(busy)

    def show_toast(self, msg: str, duration_ms: int = 2000) -> None:
        self._signals.show_toast_sig.emit(msg, duration_ms)

    def get_url_input(self) -> str:
        return self._url_edit.text().strip()

    def get_view_mode(self) -> str:
        return self._view_combo.currentText()

    def get_preview_text(self) -> str:
        return self._preview.toPlainText()

    def clear_log(self) -> None:
        self._signals.add_log.emit("__clear__")

    def run(self) -> None:
        self._window.show()
        self._app.exec()

    # signal handlers (runs in main thread)
    def _connect_signals(self):
        s = self._signals
        s.add_log.connect(self._on_add_log)
        s.set_mini.connect(self._on_set_mini)
        s.set_preview.connect(self._on_set_preview)
        s.set_btns.connect(self._on_set_btns)
        s.set_run_busy.connect(self._run_btn.set_busy)
        s.show_toast_sig.connect(self._on_show_toast)
        self._toast_timer.timeout.connect(lambda: self._toast_lbl.setText(""))

    def _on_add_log(self, msg: str):
        if msg == "__clear__":
            self._log_edit.clear()
            return
        color = SUCCESS if msg.startswith("[OK]") else ERROR if msg.startswith("[ERROR]") else TEXT
        self._log_edit.append(
            f'<span style="color:{color};font-family:Consolas;font-size:9pt">{msg}</span>'
        )

    def _on_set_mini(self, msg: str, level: str):
        color = {"ok": SUCCESS, "error": ERROR}.get(level, MUTED)
        self._mini_lbl.setText(msg)
        self._mini_lbl.setStyleSheet(f"color:{color}; font-size:10pt;")

    def _on_set_preview(self, content: str, label: str):
        self._preview.setPlainText(content)
        if label:
            self._view_label.setText(label)
        self._update_word_count()

    def _on_set_btns(self, enabled: bool):
        for b in (self._copy_btn, self._overwrite_btn, self._open_btn, self._strip_btn):
            b.setEnabled(enabled)

    def _on_show_toast(self, msg: str, duration_ms: int):
        self._toast_lbl.setText(msg)
        self._toast_timer.start(duration_ms)

    def _update_word_count(self):
        content = self._preview.toPlainText()
        self._wc_lbl.setText(f"{len(content.split())} words  {len(content)} chars")

    def _on_copy(self):
        self._app.clipboard().setText(self.get_preview_text())
        self.show_toast(f"Copied {self.get_view_mode()}.tex!")

    def _on_view_change(self):
        self._presenter.switch_view()

    def _toggle_log(self, checked: bool):
        self._log_edit.setVisible(checked)

    def _build(self):
        self._window = QMainWindow()
        self._window.setWindowTitle("ArxivCat")
        self._window.resize(780, 660)
        self._window.setMinimumSize(560, 480)

        root = QWidget()
        root.setObjectName("root")
        self._window.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(24, 18, 24, 14)
        outer.setSpacing(0)

        # title
        title_row = QHBoxLayout()
        lbl_title = QLabel("ArxivCat")
        lbl_title.setStyleSheet(f"color:{ACCENT}; font-size:16pt; font-weight:bold;")
        lbl_info = QLabel(f"{AUTHOR}  {VERSION}")
        lbl_info.setStyleSheet(f"color:{MUTED}; font-size:9pt; padding-top:4px;")
        title_row.addWidget(lbl_title)
        title_row.addWidget(lbl_info)
        title_row.addStretch()
        outer.addLayout(title_row)
        outer.addSpacing(10)

        # url input
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("paste an arXiv URL or ID")
        self._url_edit.returnPressed.connect(lambda: self._presenter.run_fetch())
        self._run_btn = _RunButton()
        self._run_btn.clicked.connect(lambda: self._presenter.run_fetch())
        input_row.addWidget(self._url_edit)
        input_row.addWidget(self._run_btn)
        outer.addLayout(input_row)
        outer.addSpacing(6)

        # controls bar
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)
        self._view_combo = QComboBox()
        self._view_combo.addItems(["body", "appendix"])
        self._view_combo.currentTextChanged.connect(self._on_view_change)
        show_log_chk = QCheckBox("show log")
        show_log_chk.toggled.connect(self._toggle_log)
        self._mini_lbl = QLabel("")
        self._mini_lbl.setStyleSheet(f"color:{MUTED}; font-size:10pt;")
        ctrl_row.addWidget(self._view_combo)
        ctrl_row.addWidget(show_log_chk)
        ctrl_row.addStretch()
        ctrl_row.addWidget(self._mini_lbl)
        outer.addLayout(ctrl_row)
        outer.addSpacing(4)

        # log panel
        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setFixedHeight(180)
        self._log_edit.setVisible(False)
        outer.addWidget(self._log_edit)
        outer.addSpacing(4)

        # preview header
        hdr_row = QHBoxLayout()
        self._view_label = QLabel("body.tex")
        self._view_label.setStyleSheet(f"color:{MUTED}; font-size:9pt;")
        self._wc_lbl = QLabel("")
        self._wc_lbl.setStyleSheet(f"color:{MUTED}; font-size:9pt;")
        hdr_row.addWidget(self._view_label)
        hdr_row.addStretch()
        hdr_row.addWidget(self._wc_lbl)
        outer.addLayout(hdr_row)
        outer.addSpacing(2)

        # preview
        self._preview = QPlainTextEdit()
        self._preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._preview.textChanged.connect(self._update_word_count)
        outer.addWidget(self._preview, stretch=1)
        outer.addSpacing(8)

        # bottom buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self._copy_btn      = _FlatButton("Copy")
        self._overwrite_btn = _FlatButton("Overwrite")
        self._open_btn      = _FlatButton("Open Folder")
        self._strip_btn     = _FlatButton("Strip Comments")
        self._copy_btn.clicked.connect(self._on_copy)
        self._overwrite_btn.clicked.connect(lambda: self._presenter.overwrite_file())
        self._open_btn.clicked.connect(lambda: self._presenter.open_folder())
        self._strip_btn.clicked.connect(lambda: self._presenter.strip_comments())
        self._toast_lbl = QLabel("")
        self._toast_lbl.setStyleSheet(f"color:{MUTED}; font-size:9pt;")
        for b in (self._copy_btn, self._overwrite_btn, self._open_btn, self._strip_btn):
            btn_row.addWidget(b)
        btn_row.addStretch()
        btn_row.addWidget(self._toast_lbl)
        outer.addLayout(btn_row)
