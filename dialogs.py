from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit,
)
from PyQt6.QtCore import Qt

from constants import ProfileKey, PRESET_MAP, CORE_PRESETS, CUSTOM_SLOTS
from profiles import CustomProfiles, strip_profile_prefix
from styles import (
    DIALOG_BASE_QSS, SAVE_DIALOG_QSS, DIALOG_TITLE_QSS,
    BTN_CANCEL, BTN_PRIMARY, BTN_DANGER, BTN_SAVE, BTN_DISABLED,
)


class CopyDialog(QDialog):
    def __init__(self, parent, is_s1_empty: bool, is_s2_empty: bool):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFixedSize(350, 260)
        self.setStyleSheet(parent.styleSheet() + DIALOG_BASE_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Copy to Custom Slot")
        title.setStyleSheet(DIALOG_TITLE_QSS)
        layout.addWidget(title)

        self.slot_combo = QComboBox()
        self.slot_combo.addItem("Custom Slot 1")
        self.slot_combo.addItem("Custom Slot 2")

        model = self.slot_combo.model()
        if not is_s1_empty:
            model.item(0).setEnabled(False)
            self.slot_combo.setItemText(0, "Custom Slot 1 (Occupied)")
        if not is_s2_empty:
            model.item(1).setEnabled(False)
            self.slot_combo.setItemText(1, "Custom Slot 2 (Occupied)")

        if is_s1_empty:
            self.slot_combo.setCurrentIndex(0)
        elif is_s2_empty:
            self.slot_combo.setCurrentIndex(1)
        else:
            self.slot_combo.setCurrentIndex(-1)

        layout.addWidget(QLabel("Destination:"))
        layout.addWidget(self.slot_combo)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter new profile name...")
        layout.addWidget(QLabel("Profile Name:"))
        layout.addWidget(self.name_input)

        layout.addStretch()
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet(BTN_CANCEL)
        self.btn_save = QPushButton("Save & Copy")
        self.btn_save.setStyleSheet(BTN_PRIMARY)

        if not is_s1_empty and not is_s2_empty:
            self.btn_save.setEnabled(False)
            self.btn_save.setText("No Slots Available")
            self.btn_save.setStyleSheet(BTN_DISABLED)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)


class CopyFromDialog(QDialog):
    def __init__(self, parent, target_slot: ProfileKey, is_occupied: bool, custom_profiles: CustomProfiles):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFixedSize(350, 260)
        self.setStyleSheet(parent.styleSheet() + DIALOG_BASE_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(f"Copy into {target_slot}")
        title.setStyleSheet(DIALOG_TITLE_QSS)
        layout.addWidget(title)

        self.source_combo = QComboBox()
        for key in CORE_PRESETS:
            self.source_combo.addItem(PRESET_MAP[key]["name"], userData=PRESET_MAP[key]["vals"])

        for key in CUSTOM_SLOTS:
            slot = custom_profiles[key]
            if key != target_slot and not slot.is_empty:
                self.source_combo.addItem(slot.name, userData=slot.values)

        layout.addWidget(QLabel("Source Profile:"))
        layout.addWidget(self.source_combo)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter new profile name...")
        layout.addWidget(QLabel("New Profile Name:"))
        layout.addWidget(self.name_input)

        layout.addStretch()
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(BTN_CANCEL)
        btn_save = QPushButton("Save & Overwrite" if is_occupied else "Save & Import")
        btn_save.setStyleSheet(BTN_DANGER if is_occupied else BTN_PRIMARY)
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)


class SaveProfileDialog(QDialog):
    def __init__(self, parent, current_name: str):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFixedSize(320, 200)
        self.setStyleSheet(parent.styleSheet() + SAVE_DIALOG_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Save Custom Profile")
        title.setStyleSheet(DIALOG_TITLE_QSS)
        layout.addWidget(title)

        self.name_input = QLineEdit()
        self.name_input.setText(strip_profile_prefix(current_name))
        layout.addWidget(QLabel("Profile Name:"))
        layout.addWidget(self.name_input)

        layout.addStretch()
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(BTN_CANCEL)
        btn_save = QPushButton("Save Changes")
        btn_save.setStyleSheet(BTN_SAVE)
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)
