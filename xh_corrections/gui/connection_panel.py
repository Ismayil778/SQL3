"""
Connection panel — server/db/login/password + Windows Auth checkbox + test button.
Parameterisable so the same widget can serve both Base_1c77 and XalqLife.
Settings are persisted per-panel via a settings_prefix key.
"""
from PySide6.QtWidgets import (
    QGroupBox, QFormLayout, QLineEdit, QPushButton,
    QLabel, QHBoxLayout, QVBoxLayout, QCheckBox,
)
from PySide6.QtCore import QSettings, Signal
from PySide6.QtGui import QFont

from gui.styles import XH_GREEN, XH_RED, XH_MUTED


class ConnectionPanel(QGroupBox):
    connected    = Signal(object)   # emits pyodbc.Connection on success
    disconnected = Signal()

    def __init__(
        self,
        title: str = "Bağlantı / Подключение",
        default_db: str = "Base_1c77",
        settings_prefix: str = "conn",
        parent=None,
    ):
        super().__init__(title, parent)
        self._default_db      = default_db
        self._settings_prefix = settings_prefix
        self._conn            = None
        self._settings        = QSettings("XalqHayat", "KorreksiyaGenerator")
        self._build_ui()
        self._load_settings()

    # ------------------------------------------------------------------ #
    def _key(self, k: str) -> str:
        return f"{self._settings_prefix}_{k}"

    def _build_ui(self):
        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(8, 8, 8, 8)

        self.le_server = QLineEdit()
        self.le_server.setPlaceholderText("172.16.50.4")
        form.addRow("Server:", self.le_server)

        self.le_db = QLineEdit()
        self.le_db.setPlaceholderText(self._default_db)
        form.addRow("Baza / База:", self.le_db)

        self.chk_win_auth = QCheckBox("Windows Authentication")
        self.chk_win_auth.toggled.connect(self._on_auth_toggle)
        form.addRow("", self.chk_win_auth)

        self.le_login = QLineEdit()
        self.le_login.setPlaceholderText("sa")
        form.addRow("Login:", self.le_login)

        self.le_password = QLineEdit()
        self.le_password.setEchoMode(QLineEdit.Password)
        self.le_password.setPlaceholderText("••••••••")
        form.addRow("Şifrə / Пароль:", self.le_password)

        btn_row = QHBoxLayout()
        self.btn_test = QPushButton("Yoxla / Проверить")
        self.btn_test.setObjectName("btn_secondary")
        self.btn_test.setMinimumWidth(140)
        self.btn_test.clicked.connect(self._on_test)
        btn_row.addWidget(self.btn_test)
        btn_row.addSpacing(10)

        self.lbl_status = QLabel()
        self.lbl_status.setFont(QFont("Segoe UI", 9))
        btn_row.addWidget(self.lbl_status)
        btn_row.addStretch()

        main = QVBoxLayout(self)
        main.addLayout(form)
        main.addSpacing(4)
        main.addLayout(btn_row)

    def _on_auth_toggle(self, checked: bool):
        self.le_login.setEnabled(not checked)
        self.le_password.setEnabled(not checked)
        if checked:
            self.le_login.setPlaceholderText("Windows аккаунт")
            self.le_password.clear()
        else:
            self.le_login.setPlaceholderText("sa")

    def _load_settings(self):
        self.le_server.setText(self._settings.value(self._key("server"), "172.16.50.4"))
        self.le_db.setText(self._settings.value(self._key("database"), self._default_db))
        self.le_login.setText(self._settings.value(self._key("login"), ""))
        win_auth = self._settings.value(self._key("windows_auth"), False, type=bool)
        self.chk_win_auth.setChecked(win_auth)

    def _save_settings(self):
        self._settings.setValue(self._key("server"),       self.le_server.text().strip())
        self._settings.setValue(self._key("database"),     self.le_db.text().strip())
        self._settings.setValue(self._key("login"),        self.le_login.text().strip())
        self._settings.setValue(self._key("windows_auth"), self.chk_win_auth.isChecked())

    def _on_test(self):
        from core.db import test_connection, get_connection

        server       = self.le_server.text().strip()   or "172.16.50.4"
        database     = self.le_db.text().strip()       or self._default_db
        login        = self.le_login.text().strip()
        password     = self.le_password.text()
        windows_auth = self.chk_win_auth.isChecked()

        self.btn_test.setEnabled(False)
        self.lbl_status.setText("Yoxlanılır...")
        self.lbl_status.setStyleSheet(f"color: {XH_MUTED};")
        self.btn_test.repaint()
        self.lbl_status.repaint()

        ok, msg = test_connection(server, database, login, password, windows_auth)

        if ok:
            self._conn = get_connection(server, database, login, password, windows_auth)
            self.lbl_status.setText("● Bağlandı")
            self.lbl_status.setStyleSheet(f"color: {XH_GREEN}; font-weight: bold;")
            self._save_settings()
            self.connected.emit(self._conn)
        else:
            self._conn = None
            short = msg[:100] + "…" if len(msg) > 100 else msg
            self.lbl_status.setText(f"● {short}")
            self.lbl_status.setStyleSheet(f"color: {XH_RED};")
            self.disconnected.emit()

        self.btn_test.setEnabled(True)

    def get_connection(self):
        return self._conn
