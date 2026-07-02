"""
Connection panel — server/db/login/password fields + test button.
Settings (server, db, login) persisted via QSettings.
"""
from PySide6.QtWidgets import (
    QGroupBox, QFormLayout, QLineEdit, QPushButton,
    QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy,
)
from PySide6.QtCore import Qt, QSettings, Signal
from PySide6.QtGui import QFont

from gui.styles import XH_GREEN, XH_RED, XH_MUTED


class ConnectionPanel(QGroupBox):
    connected = Signal(object)   # emits pyodbc.Connection on success
    disconnected = Signal()

    def __init__(self, parent=None):
        super().__init__("Bağlantı / Подключение", parent)
        self._conn = None
        self._settings = QSettings("XalqHayat", "KorreksiyaGenerator")
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(8, 8, 8, 8)

        self.le_server = QLineEdit()
        self.le_server.setPlaceholderText("172.16.50.4")
        form.addRow("Server:", self.le_server)

        self.le_db = QLineEdit()
        self.le_db.setPlaceholderText("Base_1c77")
        form.addRow("Baza / База:", self.le_db)

        self.le_login = QLineEdit()
        self.le_login.setPlaceholderText("sa")
        form.addRow("Login:", self.le_login)

        self.le_password = QLineEdit()
        self.le_password.setEchoMode(QLineEdit.Password)
        self.le_password.setPlaceholderText("••••••••")
        form.addRow("Şifrə / Пароль:", self.le_password)

        # Button + status indicator row
        btn_row = QHBoxLayout()
        self.btn_test = QPushButton("Yoxla / Проверить")
        self.btn_test.setObjectName("btn_secondary")
        self.btn_test.setMinimumWidth(160)
        self.btn_test.clicked.connect(self._on_test)
        btn_row.addWidget(self.btn_test)
        btn_row.addSpacing(12)

        self.lbl_status = QLabel()
        self.lbl_status.setFont(QFont("Segoe UI", 9))
        btn_row.addWidget(self.lbl_status)
        btn_row.addStretch()

        main = QVBoxLayout(self)
        main.addLayout(form)
        main.addSpacing(6)
        main.addLayout(btn_row)

    def _load_settings(self):
        self.le_server.setText(
            self._settings.value("server", "172.16.50.4"))
        self.le_db.setText(
            self._settings.value("database", "Base_1c77"))
        self.le_login.setText(
            self._settings.value("login", ""))

    def _save_settings(self):
        self._settings.setValue("server",   self.le_server.text().strip())
        self._settings.setValue("database", self.le_db.text().strip())
        self._settings.setValue("login",    self.le_login.text().strip())

    def _on_test(self):
        from core.db import test_connection, get_connection

        server   = self.le_server.text().strip()   or "172.16.50.4"
        database = self.le_db.text().strip()        or "Base_1c77"
        login    = self.le_login.text().strip()
        password = self.le_password.text()

        self.btn_test.setEnabled(False)
        self.lbl_status.setText("Yoxlanılır... / Проверяется...")
        self.lbl_status.setStyleSheet(f"color: {XH_MUTED};")
        # Force repaint
        self.btn_test.repaint()
        self.lbl_status.repaint()

        ok, msg = test_connection(server, database, login, password)

        if ok:
            self._conn = get_connection(server, database, login, password)
            self.lbl_status.setText("● Подключено / Bağlandı")
            self.lbl_status.setStyleSheet(f"color: {XH_GREEN}; font-weight: bold;")
            self._save_settings()
            self.connected.emit(self._conn)
        else:
            self._conn = None
            short = msg[:120] + "…" if len(msg) > 120 else msg
            self.lbl_status.setText(f"● {short}")
            self.lbl_status.setStyleSheet(f"color: {XH_RED};")
            self.disconnected.emit()

        self.btn_test.setEnabled(True)

    def get_connection(self):
        return self._conn
