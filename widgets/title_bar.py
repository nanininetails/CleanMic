from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

from styles import TITLE_BAR_BTN_QSS, TITLE_BAR_CLOSE_BTN_QSS


class CustomTitleBar(QWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)

        self.title_label = QLabel("CleanMic")
        self.title_label.setStyleSheet("color: #E3E4E8; font-weight: bold; font-size: 14px;")

        self.btn_min = QPushButton("—")   
        self.btn_close = QPushButton("✕")

        for btn in [self.btn_min, self.btn_close]:
            btn.setFixedSize(30, 30)
            btn.setStyleSheet(TITLE_BAR_BTN_QSS)
        self.btn_close.setStyleSheet(TITLE_BAR_CLOSE_BTN_QSS)

        self.btn_min.clicked.connect(self.main_window.showMinimized)
        self.btn_close.clicked.connect(self.main_window.close)

        layout.addWidget(self.title_label)
        layout.addStretch()
        for btn in [self.btn_min, self.btn_close]:
            layout.addWidget(btn)
        self.setLayout(layout)
        self._drag_start = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_start:
            delta = event.globalPosition().toPoint() - self._drag_start
            self.main_window.move(self.main_window.pos() + delta)
            self._drag_start = event.globalPosition().toPoint()
            if self.main_window.drawer.isVisible():
                self.main_window.drawer.sync_position()

    def mouseReleaseEvent(self, event):
        self._drag_start = None
