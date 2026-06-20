from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QSpinBox, QDoubleSpinBox, QGridLayout,
)
from PyQt6.QtCore import Qt

from constants import TUNING_PARAMS, DRAWER_GAP
from styles import DRAWER_QSS, DRAWER_BTN_SECONDARY_QSS, DRAWER_BTN_SAVE_QSS


class AdvancedTuningDrawer(QWidget):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(DRAWER_QSS)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 15)

        accent = QWidget()
        accent.setFixedHeight(3)
        accent.setStyleSheet("background-color: #00D2C4;")

        layout.addWidget(accent)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 15, 20, 0)

        self._controls: list[tuple[QSlider, QSpinBox | QDoubleSpinBox]] = []

        grid = QGridLayout()
        grid.setHorizontalSpacing(30)
        grid.setVerticalSpacing(12)

        control_widgets = []
        
        for param in TUNING_PARAMS:
            row = QHBoxLayout()
            row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            lbl = QLabel(param.label)
            lbl.setMinimumWidth(100)

            sld = QSlider(Qt.Orientation.Horizontal)
            sld.setRange(param.min_v, param.max_v)
            sld.setValue(param.default)

            if param.is_float:
                box: QSpinBox | QDoubleSpinBox = QDoubleSpinBox()
                box.setRange(param.min_v / 10, param.max_v / 10)
                box.setValue(param.default / 10)
                box.setSingleStep(0.1)
                sld.valueChanged.connect(lambda v, b=box: b.setValue(v / 10))
                box.valueChanged.connect(lambda v, s=sld: s.setValue(int(v * 10)))
            else:
                box = QSpinBox()
                box.setRange(param.min_v, param.max_v)
                box.setValue(param.default)
                sld.valueChanged.connect(box.setValue)
                box.valueChanged.connect(sld.setValue)

            box.setFixedWidth(90)
            sld.valueChanged.connect(self.parent_window.on_drawer_value_changed)

            row.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(sld, stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(box, alignment=Qt.AlignmentFlag.AlignVCenter)
            
            control_widget = QWidget()
            control_widget.setLayout(row)
            control_widgets.append(control_widget)
            self._controls.append((sld, box))

        grid.addWidget(control_widgets[0], 0, 0)  # Train Time
        grid.addWidget(control_widgets[2], 0, 1)  # Hunting Focus

        grid.addWidget(control_widgets[1], 1, 0)  # Scrub Power
        grid.addWidget(control_widgets[3], 1, 1)  # Word Fade

        grid.addWidget(control_widgets[4], 2, 0)  # Voice Shield

        btn_layout = QHBoxLayout()

        self.btn_copy_from = QPushButton("Copy From...")
        self.btn_copy_from.setStyleSheet(DRAWER_BTN_SECONDARY_QSS)
        self.btn_copy_to = QPushButton("Copy To...")
        self.btn_copy_to.setStyleSheet(DRAWER_BTN_SECONDARY_QSS)
        self.btn_save = QPushButton("Save Changes")
        self.btn_save.setStyleSheet(DRAWER_BTN_SAVE_QSS)

        self.btn_copy_from.clicked.connect(self.parent_window.trigger_copy_from_via_drawer)
        self.btn_copy_to.clicked.connect(self.parent_window.trigger_copy_to_via_drawer)
        self.btn_save.clicked.connect(self.parent_window.trigger_save_custom)

        btn_layout.addWidget(self.btn_copy_from)
        btn_layout.addWidget(self.btn_copy_to)
        btn_layout.addWidget(self.btn_save)
        btn_container = QWidget()
        btn_container.setLayout(btn_layout)

        grid.addWidget(btn_container,2,1)

        content_layout.addLayout(grid)
        layout.addWidget(content)
        self.setLayout(layout)

    def set_values(self, *values: int) -> None:
        for (slider, _), value in zip(self._controls, values):
            slider.setValue(int(value))

    def get_values(self) -> list[int]:
        return [slider.value() for slider, _ in self._controls]

    def set_editable(self, editable: bool) -> None:
        for slider, box in self._controls:
            slider.setEnabled(editable)
            box.setEnabled(editable)

    def sync_position(self) -> None:
        geom = self.parent_window.geometry()
        self.setFixedWidth(geom.width())
        self.move(
            geom.left(),
            geom.bottom() + DRAWER_GAP,
        )
