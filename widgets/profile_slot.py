from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt


class ProfileSlotWidget(QFrame):
    def __init__(self, text: str, is_empty: bool = False, show_trash: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("profile_slot")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.btn_main = QPushButton(text)
        self.btn_main.setObjectName("main_btn_inner")
        self.btn_main.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.btn_main.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.btn_trash = QPushButton("🗑")
        self.btn_trash.setFixedWidth(36)
        self.btn_trash.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.btn_trash.setObjectName("trash_btn_inner")
        self.btn_trash.setVisible(show_trash and not is_empty)
        self.is_empty = is_empty
        if is_empty:
            self.btn_main.setStyleSheet("color: #5A617A; font-weight: bold;")

        layout.addWidget(self.btn_main)
        layout.addWidget(self.btn_trash)
        self.btn_trash.installEventFilter(self)

    def _refresh_style(self):
        self.style().unpolish(self)
        self.style().polish(self)

    def eventFilter(self, obj, event):
        if obj == self.btn_trash and self.isEnabled():
            if event.type() == event.Type.Enter:
                self.setProperty("trash_hover", True)
                self._refresh_style()
            elif event.type() == event.Type.Leave:
                self.setProperty("trash_hover", False)
                self._refresh_style()
        return super().eventFilter(obj, event)

    def set_active(self, is_active: bool):
        self.setProperty("active_preset", is_active)
        if is_active:
            self.btn_main.setStyleSheet("color: #00D2C4; font-weight: bold;")
        elif self.isEnabled():
            color = "#5A617A" if self.is_empty else "#FFFFFF"
            self.btn_main.setStyleSheet(f"color: {color}; font-weight: bold;")
        else:
            self.btn_main.setStyleSheet("color: #363A4D; font-weight: bold;")
        self._refresh_style()

    def set_empty(self, is_empty: bool):
        self.is_empty = is_empty
        self.btn_trash.setVisible(not is_empty)
        if not self.property("active_preset"):
            color = "#5A617A" if is_empty else "#FFFFFF"
            self.btn_main.setStyleSheet(f"color: {color}; font-weight: bold;")

    def changeEvent(self, event):
        super().changeEvent(event)
        if self.property("active_preset"):
            self.btn_main.setStyleSheet("color: #00D2C4; font-weight: bold;")
        elif self.isEnabled():
            color = "#5A617A" if self.is_empty else "#FFFFFF"
            self.btn_main.setStyleSheet(f"color: {color}; font-weight: bold;")
        else:
            self.btn_main.setStyleSheet("color: #363A4D; font-weight: bold;")