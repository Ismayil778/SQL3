"""
Entry point — Xalq Həyat Korrektəedici Müxabirləşmələr Generator.

Usage:
    python main.py
"""
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from gui.main_window import MainWindow


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Xalq Həyat Korreksiya")
    app.setOrganizationName("XalqHayat")
    app.setOrganizationDomain("xalqhayat.az")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
