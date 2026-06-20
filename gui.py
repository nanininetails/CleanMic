import json
import logging
import sys
import queue
from typing import Callable

import numpy as np
import pyqtgraph as pg
import sounddevice as sd

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QComboBox, QPushButton,
    QGroupBox, QProgressBar, QCheckBox,
    QFileDialog, QLineEdit, QMenu, QSizePolicy, QGridLayout, QGraphicsDropShadowEffect, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, QSize, QEvent
from PyQt6.QtGui import QCloseEvent, QIcon, QPixmap, QColor
from PyQt6.QtSvgWidgets import QSvgWidget

from constants import (
    EngineType, ProfileKey, PRESET_MAP, CORE_PRESETS,
    CUSTOM_UI_PROFILES, PROFILE_NAME_PREFIX,
    ui_profile_to_slot, slot_to_ui_profile, is_custom_ui_profile,
    VISUAL_TIMER_MS, FFT_DISPLAY_BINS, VU_METER_SCALE, VU_METER_MAX,
    SAVE_FEEDBACK_MS, DEVICE_NAME_MAX_LEN,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    ENGINE_TUNING_ATTRS, ENGINE_TUNING_SCALE,FFT_SMOOTHING_BEFORE, 
    FFT_SMOOTHING_AFTER,PEAK_HOLD_FRAMES, PEAK_DECAY_RATE, METER_MIN_DB, 
    METER_MAX_DB, BOTTOM_BAR_HEIGHT, DRAWER_GAP, DF_PRESET_MAP,
)
from dialogs import CopyDialog, CopyFromDialog, SaveProfileDialog
from profiles import (
    CustomProfile, CustomProfiles, RecordButtonState,
    profiles_file_path, default_custom_profiles,
    is_legacy_profile_format, profiles_from_json, profiles_to_json,
    strip_profile_prefix,
)
from styles import (
    build_main_stylesheet, CONTEXT_MENU_QSS,
    RECORD_BTN_IDLE_QSS, RECORD_BTN_ACTIVE_QSS,
    DRAWER_TOGGLE_BTN_QSS,METER_TRACK_QSS, METER_LABEL_QSS, METER_READOUT_QSS,
    GAIN_SLIDER_QSS, BOTTOM_BAR_QSS, ENGAGE_PANEL_QSS, CHART_SEPARATOR_QSS,
)
from widgets import CustomTitleBar, ProfileSlotWidget, AdvancedTuningDrawer, PeakMeterBar, AccentDivider

logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Record Button
RECORD_BUTTON_LABELS = {
    RecordButtonState.IDLE: "Start Recording",
    RecordButtonState.RECORDING: "Stop Recording & Save",
}

RECORD_BUTTON_STYLES = {
    RecordButtonState.IDLE: RECORD_BTN_IDLE_QSS,
    RecordButtonState.RECORDING: RECORD_BTN_ACTIVE_QSS,
}

class CleanMicGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = None
        self.active_profile_type: ProfileKey = ProfileKey.P1
        self.clean_profile_values: list[int] = []
        self.loading_values: bool = False
        self.smoothed_fft_before = None
        self.smoothed_fft_after = None
        self._calibration_countdown = 0
        self._countdown_timer = QTimer()
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._tick_countdown)

        self._peak_in_db = METER_MIN_DB
        self._peak_out_db = METER_MIN_DB
        self._peak_in_hold = 0
        self._peak_out_hold = 0

        self.profiles_file = profiles_file_path()
        self.custom_profiles: CustomProfiles = self._load_profiles()

        self.drawer = AdvancedTuningDrawer(self)
        self.locked_recording_engine = None
        self._current_record_state = RecordButtonState.IDLE

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.setStyleSheet(build_main_stylesheet())

        self._init_ui()
        self._populate_hardware_devices()

        self.btn_p1.click()
        self.handle_engine_swap(EngineType.DEEP_FILTER)

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_visuals)
        self.timer.start(VISUAL_TIMER_MS)

        self._set_initial_position()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.timer.stop()
        if self.drawer.isVisible():
            self.drawer.hide()
        if self.engine and self.engine.is_running:
            self.engine.stop_stream()
        super().closeEvent(event)

    def changeEvent(self, event) -> None:
        if event.type() ==QEvent.Type.ActivationChange:
            if self.isActiveWindow() and self.drawer.isVisible():
                self.drawer.raise_()
                self.btn_toggle_drawer.setChecked(True)
                self.btn_toggle_drawer.setText("▲ Advanced Tuning")
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Profile persistence
    # ------------------------------------------------------------------

    def _load_profiles(self) -> CustomProfiles:
        if not self.profiles_file.exists():
            return default_custom_profiles()
        try:
            with open(self.profiles_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if is_legacy_profile_format(data):
                logger.warning("Legacy profile format detected; using defaults.")
                return default_custom_profiles()
            return profiles_from_json(data)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Could not load profiles from disk: %s", e)
            return default_custom_profiles()

    def _save_profiles_to_disk(self) -> None:
        try:
            with open(self.profiles_file, "w", encoding="utf-8") as f:
                json.dump(profiles_to_json(self.custom_profiles), f)
        except OSError as e:
            logger.warning("Could not save profiles to disk: %s", e)

    def _get_unique_name(self, base_name: str) -> str:
        existing = [
            strip_profile_prefix(self.custom_profiles[ProfileKey.CUSTOM_1].name),
            strip_profile_prefix(self.custom_profiles[ProfileKey.CUSTOM_2].name),
        ]
        if base_name not in existing:
            return base_name
        count = 2
        while f"{base_name} {count}" in existing:
            count += 1
        return f"{base_name} {count}"

    def _slot_widgets(self) -> dict[ProfileKey, tuple[ProfileSlotWidget, QPushButton]]:
        return {
            ProfileKey.CUSTOM_1: (self.slot1_widget, self.btn_c1),
            ProfileKey.CUSTOM_2: (self.slot2_widget, self.btn_c2),
        }

    def _update_custom_slot_ui(self, slot_key: ProfileKey) -> None:
        profile = self.custom_profiles[slot_key]
        widget, button = self._slot_widgets()[slot_key]
        button.setText(profile.name)
        widget.set_empty(profile.is_empty)

    def _set_record_button_state(self, state: RecordButtonState) -> None:
        self._current_record_state = state

        self.record_btn.setText("")
        self.record_btn.setIconSize(QSize(100, 36))
        self.record_btn.setStyleSheet(RECORD_BUTTON_STYLES[state])
        self.record_btn.setToolTip(RECORD_BUTTON_LABELS[state])

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        base_widget = QWidget()
        base_layout = QVBoxLayout()
        base_layout.setContentsMargins(0, 0, 0, 0)
        base_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        base_layout.addWidget(self.title_bar)

        # Accent line
        accent_container = QWidget()
        accent_layout = QVBoxLayout(accent_container)
        accent_layout.setContentsMargins(1, 0, 1, 0)
        accent_layout.setSpacing(0)

        accent_layout.addWidget(
            AccentDivider(show_separator=True)
        )

        base_layout.addWidget(accent_container)

        # --- The Locked Grid Layout ---
        grid_widget = QWidget()
        main_grid = QGridLayout(grid_widget)
        main_grid.setContentsMargins(0, 0, 0, 0)
        main_grid.setSpacing(0)

        # Assign Panels to Coordinates
        main_grid.addLayout(self._build_left_panel(), 0, 0)
        main_grid.addLayout(self._build_center_panel(), 0, 1)
        main_grid.addLayout(self._build_engage_panel(), 1, 0)
        main_grid.addLayout(self._build_meter_panel(), 1, 1)

        # Lock the Math (Widths)
        main_grid.setColumnStretch(0, 28)
        main_grid.setColumnStretch(1, 72)
        
        # Lock the Math (Heights)
        main_grid.setRowStretch(0, 1)  # Top row stretches to fill space
        main_grid.setRowStretch(1, 0)  # Bottom row does not stretch
        main_grid.setRowMinimumHeight(1, BOTTOM_BAR_HEIGHT) 

        base_layout.addWidget(grid_widget, stretch=1)

        # Advanced tuning toggle — full width strip
        self.btn_toggle_drawer = QPushButton("▼ Advanced Tuning")
        self.btn_toggle_drawer.setCheckable(True)
        self.btn_toggle_drawer.setFixedHeight(40)
        self.btn_toggle_drawer.setStyleSheet(DRAWER_TOGGLE_BTN_QSS)
        self.btn_toggle_drawer.clicked.connect(self._toggle_drawer)
        base_layout.addWidget(self.btn_toggle_drawer)

        central = QWidget()
        central.setLayout(base_layout)
        self.setCentralWidget(central)

        self.mic_select.currentIndexChanged.connect(self._restart_hardware_stream)
        self.mon_select.currentIndexChanged.connect(self._restart_hardware_stream)
        self.loopback_toggle.stateChanged.connect(self._update_loopback)

        self._evaluate_ui_states()

    def _set_initial_position(self) -> None:
        self.drawer.ensurePolished()
        
        drawer_height = self.drawer.sizeHint().height()
        total_height = self.height() + DRAWER_GAP +drawer_height
        
        screen = self.screen().availableGeometry()
        x = int((screen.width()-self.width())/2)
        y = int((screen.height()-total_height)/2)

        self.move(x,y)

    def _build_left_panel(self) -> QVBoxLayout:
        left = QVBoxLayout()
        left.setContentsMargins(10,10,10,10)

        hw_box = QGroupBox("INPUT && VIRTUAL ROUTING")
        hw_layout = QVBoxLayout()
        self.mic_select = QComboBox()
        self.vac_select = QComboBox()
        hw_layout.addWidget(QLabel("Physical Input (Mic)"))
        hw_layout.addWidget(self.mic_select)
        hw_layout.addWidget(QLabel("Virtual Output Device"))
        hw_layout.addWidget(self.vac_select)
        hw_box.setLayout(hw_layout)
        left.addWidget(hw_box)

        loop_box = QGroupBox("LOOPBACK MONITOR")
        loop_layout = QVBoxLayout()
        self.loopback_toggle = QCheckBox("Enable Local Loopback")
        self.mon_select = QComboBox()
        loop_layout.addWidget(self.loopback_toggle)
        loop_layout.addWidget(QLabel("Physical Output (Headphones)"))
        loop_layout.addWidget(self.mon_select)
        loop_box.setLayout(loop_layout)
        left.addWidget(loop_box)


        engine_box = QGroupBox("SUPPRESSION ENGINE && PRESETS")
        engine_layout = QVBoxLayout()

        self.engine_select = QComboBox()
        self.engine_select.addItems([EngineType.DEEP_FILTER, EngineType.STFT])
        self.engine_select.currentTextChanged.connect(self.handle_engine_swap)
        engine_layout.addWidget(self.engine_select)

        self.p1_widget = ProfileSlotWidget(PRESET_MAP[ProfileKey.P1]["name"], show_trash=False)
        self.p2_widget = ProfileSlotWidget(PRESET_MAP[ProfileKey.P2]["name"], show_trash=False)
        self.p3_widget = ProfileSlotWidget(PRESET_MAP[ProfileKey.P3]["name"], show_trash=False)

        self.btn_p1 = self.p1_widget.btn_main
        self.btn_p2 = self.p2_widget.btn_main
        self.btn_p3 = self.p3_widget.btn_main

        core_btns = [
            (ProfileKey.P1, self.btn_p1, PRESET_MAP[ProfileKey.P1]["vals"]),
            (ProfileKey.P2, self.btn_p2, PRESET_MAP[ProfileKey.P2]["vals"]),
            (ProfileKey.P3, self.btn_p3, PRESET_MAP[ProfileKey.P3]["vals"]),
        ]
        
        preset_widgets = {
            ProfileKey.P1: self.p1_widget,
            ProfileKey.P2: self.p2_widget,
            ProfileKey.P3: self.p3_widget,
        }
        
        for key, btn, vals in core_btns:
            widget = preset_widgets[key]

            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, bid=key: self._show_context_menu(pos, b, bid)
            )
            btn.clicked.connect(lambda _, k=key, v=vals, b=btn: self.apply_preset(k, v, True, b))
            engine_layout.addWidget(widget)

        slot1 = self.custom_profiles[ProfileKey.CUSTOM_1]
        slot2 = self.custom_profiles[ProfileKey.CUSTOM_2]
        self.slot1_widget = ProfileSlotWidget(slot1.name, slot1.is_empty)
        self.slot2_widget = ProfileSlotWidget(slot2.name, slot2.is_empty)
        self.btn_c1 = self.slot1_widget.btn_main
        self.btn_c2 = self.slot2_widget.btn_main

        for btn, ui_profile in [(self.btn_c1, ProfileKey.C1), (self.btn_c2, ProfileKey.C2)]:
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, k=ui_profile: self._show_context_menu(pos, b, k)
            )

        self.btn_c1.clicked.connect(
            lambda: self.apply_preset(
                ProfileKey.C1, self.custom_profiles[ProfileKey.CUSTOM_1].values, True, self.btn_c1
            )
        )
        self.btn_c2.clicked.connect(
            lambda: self.apply_preset(
                ProfileKey.C2, self.custom_profiles[ProfileKey.CUSTOM_2].values, True, self.btn_c2
            )
        )
        self.slot1_widget.btn_trash.clicked.connect(lambda: self._delete_custom(ProfileKey.CUSTOM_1))
        self.slot2_widget.btn_trash.clicked.connect(lambda: self._delete_custom(ProfileKey.CUSTOM_2))

        engine_layout.addWidget(self.slot1_widget)
        engine_layout.addWidget(self.slot2_widget)

        self.df1_widget = ProfileSlotWidget("Full Suppression", show_trash=False)
        self.df2_widget = ProfileSlotWidget("Voice Safe", show_trash=False)
        self.df3_widget = ProfileSlotWidget("Light Touch", show_trash=False)
        
        self.df_placeholder1 = QFrame()
        self.df_placeholder1.setObjectName("profile_slot")
        self.df_placeholder1.setFixedHeight(38)
        self.df_placeholder1.setEnabled(False)
        self.df_placeholder1.setVisible(False)

        self.df_placeholder2 = QFrame()
        self.df_placeholder2.setObjectName("profile_slot")
        self.df_placeholder2.setFixedHeight(38)
        self.df_placeholder2.setEnabled(False)
        self.df_placeholder2.setVisible(False)

        self.btn_df1 = self.df1_widget.btn_main
        self.btn_df2 = self.df2_widget.btn_main
        self.btn_df3 = self.df3_widget.btn_main

        self.btn_df1.clicked.connect(lambda: self.apply_df_preset("df1", self.btn_df1))
        self.btn_df2.clicked.connect(lambda: self.apply_df_preset("df2", self.btn_df2))
        self.btn_df3.clicked.connect(lambda: self.apply_df_preset("df3", self.btn_df3))

        for w in [self.df1_widget, self.df2_widget, self.df3_widget, self.df_placeholder1, self.df_placeholder2]:
            w.setVisible(False)
            engine_layout.addWidget(w)

        engine_box.setLayout(engine_layout)
        left.addWidget(engine_box)

        left.addStretch()
        return left

    def _build_engage_panel(self) -> QVBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(10, 10, 10, 10)  # universal padding matching left panel
        row.setSpacing(6)

        self.master_btn = QPushButton("ENGAGE SUPPRESSION")
        self.master_btn.setCheckable(True)
        self.master_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.master_btn.clicked.connect(self._toggle_suppression)

        self.record_btn = QPushButton("")
        self.record_btn.setFixedWidth(100)
        self.record_btn.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding
        )
        self.record_btn.setToolTip("Record Output")
        self.record_btn.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.record_btn.setStyleSheet(RECORD_BUTTON_STYLES[RecordButtonState.IDLE])
        self.record_btn.clicked.connect(self._handle_recording_click)

        row.addWidget(self.master_btn, stretch=8)
        row.addWidget(self.record_btn, stretch=0)

        return row

    def _build_center_panel(self) -> QVBoxLayout:
        center = QVBoxLayout()
        center.setSpacing(0)
        center.setContentsMargins(0, 10, 10, 0)

        pg.setConfigOption("background", "#0E0F14")
        pg.setConfigOption("foreground", "#7A7D8F")
        self.graph_widget = pg.GraphicsLayoutWidget()
        self.graph_widget.ci.layout.setContentsMargins(0, 0, 0, 0)

        self.plot_fft = self.graph_widget.addPlot(title="Frequency Response")
        self.plot_fft.setLogMode(x=True)
        self.plot_fft.setYRange(-140, 40)
        self.plot_fft.showGrid(x=True, y=True, alpha=0.08)
        self.plot_fft.hideButtons()
        self.plot_fft.setMouseEnabled(x=False, y=False)
        self.plot_fft.hideAxis("left")
        self.plot_fft.hideAxis("bottom")

        # Add legends
        self.plot_fft.addLegend(offset=(10, 10))

        # Frequency axis labels
        freq_axis = self.plot_fft.getAxis("bottom")
        freq_axis.setTicks([
            [(f, f"{f}Hz" if f < 1000 else f"{f//1000}kHz")
            for f in [100, 200, 500, 1000, 2000, 5000, 10000]]
        ])

        self.fft_curve_before = self.plot_fft.plot(
            pen=pg.mkPen("#9D00FF", width=2.5),
            fillLevel=-140,
            brush=(157, 0, 255, 40),
            name="Before"
        )
        self.fft_curve_after = self.plot_fft.plot(
            pen=pg.mkPen("#00D2C4", width=2.5),
            fillLevel=-140,
            brush=(0, 210, 196, 40),
            name="After"
        )
        #self.fft_curve_after.setVisible(False)

        # Overlay label for calibration countdown
        self.calibration_label = pg.TextItem(
            text="", color="#00D2C4",
            anchor=(0.5, 0.5)
        )
        self.calibration_label.setFont(
            pg.QtGui.QFont("Segoe UI", 16, pg.QtGui.QFont.Weight.Bold)
        )
        self.plot_fft.addItem(self.calibration_label)
        self.calibration_label.setVisible(False)

        chart_container = QWidget()
        chart_container.setObjectName("chart_container")
        chart_container.setStyleSheet(CHART_SEPARATOR_QSS)
        chart_inner = QVBoxLayout(chart_container)
        chart_inner.setContentsMargins(0, 0, 0, 0)
        chart_inner.addWidget(self.graph_widget)
        center.addWidget(chart_container, stretch=1)
        return center

    def _build_meter_panel(self) -> QVBoxLayout:
        from PyQt6.QtWidgets import QSlider
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        def make_meter_row(idle_icon: str, active_icon: str, main_color: str, peak_color: str):
            row = QHBoxLayout()
            row.setSpacing(10)

            icon_lbl = QLabel()
            icon_lbl.setPixmap(QIcon(idle_icon).pixmap(20,20))
            icon_lbl.setFixedSize(20,20)

            glow = QGraphicsDropShadowEffect()
            glow.setOffset(0,0)
            glow.setBlurRadius(0)
            glow.setColor(QColor(main_color))
            icon_lbl.setGraphicsEffect(glow)

            bar = PeakMeterBar(main_color, peak_color)
            bar.setFixedHeight(6)

            readout = QLabel("-∞ dB")
            readout.setStyleSheet(METER_READOUT_QSS)
            readout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            row.addWidget(icon_lbl)
            row.addWidget(bar, stretch=1)
            row.addWidget(readout)
            return row, bar, readout, glow, icon_lbl, (idle_icon, active_icon)

        in_row, self.meter_in, self.readout_in, self.glow_in, self.icon_in, self.icon_in_path = make_meter_row(
            "assets/meter_in_idle.svg", "assets/meter_in_active.svg", "#9D00FF","#E1B8FF"
        )
        out_row, self.meter_out, self.readout_out, self.glow_out, self.icon_out, self.icon_out_path = make_meter_row(
            "assets/meter_out_idle.svg", "assets/meter_out_active.svg", "#00AB9F", "#A2FAF3"
        )
        layout.addLayout(in_row)
        layout.addLayout(out_row)

        # Gain row
        gain_row = QHBoxLayout()
        gain_row.setSpacing(10)

        gain_lbl = QLabel()
        gain_lbl.setPixmap(QIcon("assets/meter_gain.svg").pixmap(20, 20))
        gain_lbl.setFixedSize(20, 20)

        self._glow_gain = QGraphicsDropShadowEffect()
        self._glow_gain.setOffset(0, 0)
        self._glow_gain.setBlurRadius(0)
        self._glow_gain.setColor(QColor("#79E16C"))
        gain_lbl.setGraphicsEffect(self._glow_gain)

        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(-200, 60)   # -20.0 to +6.0 dB in 0.1 steps
        self.gain_slider.setValue(0)
        self.gain_slider.setFixedHeight(10)
        self.gain_slider.setStyleSheet(GAIN_SLIDER_QSS)
        self.gain_slider.valueChanged.connect(self._on_gain_changed)

        self.readout_gain = QLabel("0.0 dB")
        self.readout_gain.setStyleSheet(METER_READOUT_QSS)
        self.readout_gain.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        gain_row.addWidget(gain_lbl)
        gain_row.addWidget(self.gain_slider, stretch=1)
        gain_row.addWidget(self.readout_gain)
        layout.addLayout(gain_row)

        return layout


    def _refresh_preset_button(self, btn: QPushButton, is_active: bool) -> None:
        btn.setProperty("active_preset", is_active)
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    # ------------------------------------------------------------------
    # Context menus
    # ------------------------------------------------------------------

    def _show_context_menu(self, pos, btn, btn_id: ProfileKey) -> None:
        is_engaged = self.master_btn.isChecked()
        is_deep = self.engine_select.currentText() == EngineType.DEEP_FILTER
        if is_engaged or is_deep:
            return

        menu = QMenu(self)
        menu.setStyleSheet(CONTEXT_MENU_QSS)
        actions: dict = {}

        if btn_id in CORE_PRESETS:
            actions[menu.addAction("Copy To...")] = (
                lambda: self._trigger_master_copy_dialog(PRESET_MAP[btn_id]["vals"])
            )
        elif btn_id in CUSTOM_UI_PROFILES:
            slot_key = ui_profile_to_slot(btn_id)
            profile = self.custom_profiles[slot_key]

            if not profile.is_empty:
                actions[menu.addAction("Rename")] = lambda: self._rename_custom(slot_key)
                actions[menu.addAction("Copy To...")] = (
                    lambda: self._trigger_master_copy_dialog(profile.values)
                )
                actions[menu.addAction("Copy From...")] = (
                    lambda: self._trigger_copy_from_dialog(slot_key, True)
                )
                menu.addSeparator()
                actions[menu.addAction("Delete Profile")] = lambda: self._delete_custom(slot_key)
            else:
                actions[menu.addAction("Copy From...")] = (
                    lambda: self._trigger_copy_from_dialog(slot_key, False)
                )

        if not actions:
            return

        chosen = menu.exec(btn.mapToGlobal(pos))
        handler: Callable[[], None] | None = actions.get(chosen)
        if handler:
            handler()

    # ------------------------------------------------------------------
    # Profile operations
    # ------------------------------------------------------------------

    def trigger_copy_from_via_drawer(self) -> None:
        slot_key = ui_profile_to_slot(self.active_profile_type)
        is_occupied = not self.custom_profiles[slot_key].is_empty
        self._trigger_copy_from_dialog(slot_key, is_occupied)

    def trigger_copy_to_via_drawer(self) -> None:
        self._trigger_master_copy_dialog(self.drawer.get_values())

    def _trigger_master_copy_dialog(self, preset_values: list[int]) -> None:
        is_s1_empty = self.custom_profiles[ProfileKey.CUSTOM_1].is_empty
        is_s2_empty = self.custom_profiles[ProfileKey.CUSTOM_2].is_empty
        dialog = CopyDialog(self, is_s1_empty, is_s2_empty)
        if dialog.exec():
            target_idx = dialog.slot_combo.currentIndex()
            if target_idx == -1:
                return
            slot_key = ProfileKey.CUSTOM_1 if target_idx == 0 else ProfileKey.CUSTOM_2
            raw_name = dialog.name_input.text().strip() or "Copied Profile"
            raw_name = self._get_unique_name(raw_name)
            self._execute_save_to_slot(slot_key, f"{PROFILE_NAME_PREFIX}{raw_name}", preset_values)

    def _trigger_copy_from_dialog(self, target_slot_key: ProfileKey, is_occupied: bool) -> None:
        dialog = CopyFromDialog(self, target_slot_key, is_occupied, self.custom_profiles)
        if dialog.exec():
            raw_name = dialog.name_input.text().strip() or "Imported Profile"
            raw_name = self._get_unique_name(raw_name)
            vals = dialog.source_combo.currentData()
            self._execute_save_to_slot(target_slot_key, f"{PROFILE_NAME_PREFIX}{raw_name}", vals)

    def trigger_save_custom(self) -> None:
        slot_key = ui_profile_to_slot(self.active_profile_type)
        current_name = self.custom_profiles[slot_key].name
        dialog = SaveProfileDialog(self, current_name)
        if dialog.exec():
            new_name = dialog.name_input.text().strip()
            full_name = f"{PROFILE_NAME_PREFIX}{new_name}" if new_name else current_name
            self._execute_save_to_slot(slot_key, full_name, self.drawer.get_values())
            self.drawer.btn_save.setText("✅ Saved!")
            QTimer.singleShot(SAVE_FEEDBACK_MS, lambda: self.drawer.btn_save.setText("Save Changes"))

    def _rename_custom(self, slot_key: ProfileKey) -> None:
        dialog = SaveProfileDialog(self, self.custom_profiles[slot_key].name)
        if dialog.exec():
            new_name = dialog.name_input.text().strip()
            if new_name:
                full_name = f"{PROFILE_NAME_PREFIX}{new_name}"
                self.custom_profiles[slot_key].name = full_name
                self._save_profiles_to_disk()
                self._slot_widgets()[slot_key][1].setText(full_name)

    def _execute_save_to_slot(self, slot_key: ProfileKey, full_name: str, vals: list[int]) -> None:
        self.custom_profiles[slot_key] = CustomProfile.saved(full_name, vals)
        self._save_profiles_to_disk()

        _, button = self._slot_widgets()[slot_key]
        self._update_custom_slot_ui(slot_key)
        button.click()

        self.clean_profile_values = vals.copy()
        self.drawer.btn_save.setEnabled(False)
        self._evaluate_ui_states()

    def _delete_custom(self, slot_key: ProfileKey) -> None:
        self.custom_profiles[slot_key] = CustomProfile.empty(slot_key)
        self._save_profiles_to_disk()
        self._update_custom_slot_ui(slot_key)

        if self.active_profile_type == slot_to_ui_profile(slot_key):
            self.btn_p1.click()

        self._evaluate_ui_states()

    # ------------------------------------------------------------------
    # Hardware
    # ------------------------------------------------------------------

    def _populate_hardware_devices(self) -> None:
        try:
            # Widen the dropdown list so text isnt truncated off
            for combo in (self.mic_select, self.vac_select, self.mon_select):
                combo.view().setMinimumWidth(350)
                #combo.setMaximumWidth(300)

            devices = sd.query_devices()
            target_api = sd.default.hostapi 
            for i, api in enumerate(sd.query_hostapis()):
                if "WASAPI" in api["name"]:
                    target_api = i
                    break  # Filter to system default (e.g., WASAPI)
            
            api_info = sd.query_hostapis(target_api)
            default_in = api_info['default_input_device']
            default_out = api_info['default_output_device']
            vac_found = False

            for i, d in enumerate(devices):
                if d["hostapi"] != target_api:
                    continue  # Skip duplicate devices from other APIs

                full_name = d["name"]
                
                if d["max_input_channels"] > 0:
                    self.mic_select.addItem(f"🎤 {full_name}", i)
                    if i == default_in:
                        self.mic_select.setCurrentIndex(self.mic_select.count() - 1)
                        
                if d["max_output_channels"] > 0:
                    self.mon_select.addItem(f"🎧 {full_name}", i)
                    self.vac_select.addItem(f"🔊 {full_name}", i)
                    
                    if "CABLE Input" in full_name and not vac_found:
                        vac_found = True
                        self.vac_select.setCurrentIndex(self.vac_select.count() - 1)
                    if i == default_out:
                        self.mon_select.setCurrentIndex(self.mon_select.count() - 1)
            self.vac_found = vac_found
        except OSError as e:
            logger.warning("Could not enumerate audio devices: %s", e)


    def _restart_hardware_stream(self) -> None:
        if self.engine and self.engine.is_running:
            was_recording = self.engine.is_recording
            self.engine.is_recording = False
            self.engine.stop_stream()
            self.engine.mic_id = self.mic_select.currentData()
            self.engine.virtual_output_id = self.vac_select.currentData()
            self.engine.speaker_id = self.mon_select.currentData()
            self.engine.is_recording = was_recording
            self.engine.start_stream()

    def _update_loopback(self) -> None:
        if self.engine:
            self.engine.loopback_active = self.loopback_toggle.isChecked()

    def _on_gain_changed(self, value: int) -> None:
        db = value / 10.0
        self.readout_gain.setText(f"{db:+.1f} dB")
        self._glow_gain.setBlurRadius(0 if value == 0 else 12)
        if self.engine:
            self.engine.output_gain_db = db
            self.engine.output_gain = 10 ** (db / 20.0)

    # ------------------------------------------------------------------
    # Engine lifecycle
    # ------------------------------------------------------------------

    def handle_engine_swap(self, selected_text: str) -> None:
        self._evaluate_ui_states()

        was_recording = False
        old_path = ""
        old_buffer = []

        if self.engine:
            if self.engine.is_engaged and self.engine.is_recording:
                print("Saving tape before engine swap")
                self.engine.stop_and_save_recording()
                self.locked_recording_engine = None
                self._set_record_button_state(RecordButtonState.IDLE)
            else:
                was_recording = self.engine.is_recording
                old_path = self.engine.record_path
                old_buffer = self.engine.record_buffer
            self.engine.is_recording = False

            if self.engine.is_running:
                self.engine.stop_stream()
        
        # Reset FFT state
        self.smoothed_fft_before = None
        self.smoothed_fft_after = None
        self.fft_curve_before.setData([], [])
        self.fft_curve_after.setData([], [])

        self.master_btn.setChecked(False)
        self.master_btn.setText("ENGAGE SUPPRESSION")

        # Lazy import: DeepFilterNet pulls in PyTorch; STFT engine is lighter.
        if selected_text == EngineType.DEEP_FILTER:
            from engine_deepfilter import AudioEngine
        else:
            from engine import AudioEngine

        self.engine = AudioEngine()
        self.engine.mic_id = self.mic_select.currentData()
        self.engine.virtual_output_id = self.vac_select.currentData()
        self.engine.speaker_id = self.mon_select.currentData()
        self.engine.loopback_active = self.loopback_toggle.isChecked()

        self.engine.is_recording = was_recording
        self.engine.record_path = old_path
        self.engine.record_buffer = old_buffer

        if was_recording:
            self._set_record_button_state(RecordButtonState.RECORDING)
        else:
            self._set_record_button_state(RecordButtonState.IDLE)

        if selected_text == EngineType.STFT:
            self.btn_p1.click()
        else:
            self.btn_df1.click()
            if self.drawer.isVisible():
                self.drawer.hide()
                self.btn_toggle_drawer.setChecked(False)
                self.btn_toggle_drawer.setText("▼ Advanced Tuning")

        self._update_engine_params()
        self.engine.start_stream()

    def _update_engine_params(self) -> None:
        if not self.engine or self.engine_select.currentText() == EngineType.DEEP_FILTER:
            return
        vals = self.drawer.get_values()
        for attr, v, scale in zip(ENGINE_TUNING_ATTRS, vals, ENGINE_TUNING_SCALE):
            if hasattr(self.engine, attr):
                setattr(self.engine, attr, v * scale)

    # ------------------------------------------------------------------
    # UI state management
    # ------------------------------------------------------------------

    def apply_preset(
        self,
        p_type: ProfileKey,
        vals: list[int],
        auto_open: bool = False,
        btn_ref: QPushButton | None = None,
    ) -> None:
        self.loading_values = True
        self.active_profile_type = p_type
        self.clean_profile_values = vals.copy()
        self.drawer.set_values(*vals)
        self._evaluate_ui_states()
        self.loading_values = False
        self._update_engine_params()

        if btn_ref:
            self.p1_widget.set_active(btn_ref == self.btn_p1)
            self.p2_widget.set_active(btn_ref == self.btn_p2)
            self.p3_widget.set_active(btn_ref == self.btn_p3)
            self.slot1_widget.set_active(btn_ref == self.btn_c1)
            self.slot2_widget.set_active(btn_ref == self.btn_c2)

        if auto_open:
            if self.engine_select.currentText() == EngineType.STFT:
                self.drawer.sync_position()
                self.drawer.show()
                self.btn_toggle_drawer.setChecked(True)
                self.btn_toggle_drawer.setText("▲ Advanced Tuning")
            else:
                self.drawer.hide()
                self.btn_toggle_drawer.setChecked(False)
                self.btn_toggle_drawer.setText("▼ Advanced Tuning")

    def on_drawer_value_changed(self) -> None:
        if self.loading_values:
            return
        self._update_engine_params()
        if is_custom_ui_profile(self.active_profile_type):
            is_dirty = self.drawer.get_values() != self.clean_profile_values
            self.drawer.btn_save.setEnabled(is_dirty)

    def apply_df_preset(self, key: str, btn_ref: QPushButton) -> None:
        self.df1_widget.set_active(btn_ref == self.btn_df1)
        self.df2_widget.set_active(btn_ref == self.btn_df2)
        self.df3_widget.set_active(btn_ref == self.btn_df3)
        if self.engine:
            self.engine.atten_lim_db = DF_PRESET_MAP[key]["atten_lim_db"]

    def _evaluate_ui_states(self) -> None:
        is_stft = self.engine_select.currentText() == EngineType.STFT
        is_engaged = self.master_btn.isChecked()
        is_custom = is_custom_ui_profile(self.active_profile_type)

        for widget in [self.p1_widget, self.p2_widget, self.p3_widget]:
            widget.setEnabled(is_stft and not is_engaged)
        self.slot1_widget.setEnabled(is_stft and not is_engaged)
        self.slot2_widget.setEnabled(is_stft and not is_engaged)
        self.btn_toggle_drawer.setEnabled(True)

        for w in [self.p1_widget, self.p2_widget, self.p3_widget, self.slot1_widget, self.slot2_widget]:
            w.setVisible(is_stft)
        for w in [self.df1_widget, self.df2_widget, self.df3_widget]:
            w.setVisible(not is_stft)
            w.setEnabled(not is_engaged)
        for w in [self.df_placeholder1, self.df_placeholder2]:
            w.setVisible(not is_stft)

        if is_stft:
            self.drawer.set_editable(is_custom and not is_engaged)
            self.drawer.btn_save.setEnabled(False)
            self.drawer.btn_save.setVisible(is_custom)
            self.drawer.btn_copy_from.setVisible(is_custom and not is_engaged)
            self.drawer.btn_copy_to.setVisible(not is_engaged)
            self.drawer.btn_copy_to.setEnabled(not is_engaged)
        else:
            self.drawer.set_editable(False)
            self.drawer.btn_save.setVisible(False)
            self.drawer.btn_copy_from.setVisible(False)
            self.drawer.btn_copy_to.setVisible(True)
            self.drawer.btn_copy_to.setEnabled(False)
        
        if self.engine and self.engine.is_recording and self.locked_recording_engine:
            current_selected = self.engine_select.currentText()
            
            if current_selected != self.locked_recording_engine:
                # Looking at the wrong engine: Lock it down
                self.master_btn.setEnabled(False)
                self.master_btn.setToolTip("Stop recording to Engage Suppression")
                self.master_btn.setText("LOCKED TO PRIMARY")
            else:
                # Looking at the correct engine: Unlock it
                self.master_btn.setEnabled(True)
                self.master_btn.setToolTip("")
                if not is_engaged:
                    self.master_btn.setText("ENGAGE SUPPRESSION")
        else:
            # Sandbox mode (Not recording, or nothing locked yet)
            self.master_btn.setEnabled(True)
            if not is_engaged:
                self.master_btn.setText("ENGAGE SUPPRESSION")

    def _toggle_drawer(self) -> None:
        if self.drawer.isVisible():
            self.drawer.hide()
            self.btn_toggle_drawer.setText("▼ Advanced Tuning")
        else:
            self.drawer.sync_position()
            self.drawer.show()
            self.btn_toggle_drawer.setText("▲ Advanced Tuning")

    def _start_calibration_overlay(self) -> None:
        is_stft = self.engine_select.currentText() == EngineType.STFT
        if not is_stft:
            return
        self._calibration_countdown = int(self.engine.scan_time_seconds)
        self._update_countdown_label()
        self.calibration_label.setVisible(True)
        self._countdown_timer.start()

    def _tick_countdown(self) -> None:
        self._calibration_countdown -= 1
        if self._calibration_countdown <= 0 or getattr(self.engine, "calibration_complete", False):
            self._countdown_timer.stop()
            self.calibration_label.setVisible(False)
        else:
            self._update_countdown_label()

    def _update_countdown_label(self) -> None:
        self.calibration_label.setText(
            f"Training Engine...  {self._calibration_countdown}s"
        )
        view_rect = self.plot_fft.viewRect()
        self.calibration_label.setPos(
            view_rect.center().x(),
            view_rect.center().y()
        )

    def _toggle_suppression(self, checked: bool) -> None:
        if not self.engine:
            return
        self.engine.is_engaged = checked

        if checked and self.engine.is_recording and not self.locked_recording_engine:
            self.locked_recording_engine = self.engine_select.currentText()

        self._evaluate_ui_states()
        if checked:
            self.smoothed_fft_after = None
            if self.engine_select.currentText() == EngineType.STFT:
                self.engine.start_calibration(self.engine.scan_time_seconds)
            self._start_calibration_overlay()
            self.master_btn.setText("ACTIVE (SUPPRESSING)")
        else:
            pass

    def _handle_recording_click(self) -> None:
        if not self.engine:
            return
        if self._current_record_state == RecordButtonState.RECORDING:
            self.engine.stop_and_save_recording()
            self._set_record_button_state(RecordButtonState.IDLE)
            self.locked_recording_engine = None
            self._evaluate_ui_states()
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Audio", "", "WAV (*.wav)")
        if file_path:
            self.engine.record_path = file_path
            self.engine.is_recording = True
            self._set_record_button_state(RecordButtonState.RECORDING)

    # ------------------------------------------------------------------
    # Visual update (timer)
    # ------------------------------------------------------------------

    # VU meters with peak hold
    def _rms_to_db(self, data: np.ndarray) -> float:
        rms = np.sqrt(np.mean(data ** 2))
        if rms < 1e-9:
            return METER_MIN_DB
        return max(20 * np.log10(rms), METER_MIN_DB)

    def _update_meters(self, raw_data: np.ndarray, clean_data: np.ndarray) -> None:
        db_in = self._rms_to_db(raw_data)
        db_out = self._rms_to_db(clean_data)

        # Peak hold IN
        if db_in >= self._peak_in_db:
            self._peak_in_db = db_in
            self._peak_in_hold = PEAK_HOLD_FRAMES
        else:
            if self._peak_in_hold > 0:
                self._peak_in_hold -= 1
            else:
                self._peak_in_db = max(self._peak_in_db - PEAK_DECAY_RATE * 60, db_in)

        # Peak hold OUT
        if db_out >= self._peak_out_db:
            self._peak_out_db = db_out
            self._peak_out_hold = PEAK_HOLD_FRAMES
        else:
            if self._peak_out_hold > 0:
                self._peak_out_hold -= 1
            else:
                self._peak_out_db = max(self._peak_out_db - PEAK_DECAY_RATE * 60, db_out)

        def db_to_meter(db: float) -> int:
            return int(1000 * (db - METER_MIN_DB) / (METER_MAX_DB - METER_MIN_DB))

        self.meter_in.setValues(db_to_meter(db_in), db_to_meter(self._peak_in_db))
        self.meter_out.setValues(db_to_meter(db_out), db_to_meter(self._peak_out_db))

        peak_in_str = f"{self._peak_in_db:.1f} dB" if self._peak_in_db > METER_MIN_DB else "-∞ dB"
        peak_out_str = f"{self._peak_out_db:.1f} dB" if self._peak_out_db > METER_MIN_DB else "-∞ dB"
        self.readout_in.setText(peak_in_str)
        self.readout_out.setText(peak_out_str)

        active_in = db_in > METER_MIN_DB
        self.glow_in.setBlurRadius(12 if active_in else 0)
        self.icon_in.setPixmap(QIcon(self.icon_in_path[int(active_in)]).pixmap(20,20))

        active_out = db_out > METER_MIN_DB
        self.glow_out.setBlurRadius(12 if active_out else 0)
        self.icon_out.setPixmap(QIcon(self.icon_out_path[int(active_out)]).pixmap(20,20))


    def _update_visuals(self) -> None:
        if not self.engine or self.engine.visual_queue.empty():
            return
        try:
            raw_data, clean_data = self.engine.visual_queue.get_nowait()
            while True:
                try:
                    raw_data, clean_data = self.engine.visual_queue.get_nowait()
                except queue.Empty:
                    break
        except queue.Empty:
            return
        
        sr = self.engine.sample_rate
        n = len(raw_data)
        freqs = np.fft.rfftfreq(n, d=1.0 / sr)
        freqs = np.clip(freqs, 1, None)  # avoid log(0)
        mask = freqs <= 18000
        freqs = freqs[mask]

        # Before curve — always
        window = np.hanning(len(raw_data))
        fft_before = np.abs(np.fft.rfft(raw_data*window))[mask]
        fft_before_db = 20 * np.log10(fft_before + 1e-9)
        fft_before_db = np.maximum(fft_before_db, -140)
        
        if (
            self.smoothed_fft_before is not None
            and len(self.smoothed_fft_before) != len(fft_before_db)
            ):
            self.smoothed_fft_before = None

        if self.smoothed_fft_before is None:
            self.smoothed_fft_before = fft_before_db
        else:
            self.smoothed_fft_before = (
                FFT_SMOOTHING_BEFORE * self.smoothed_fft_before +
                (1 - FFT_SMOOTHING_BEFORE) * fft_before_db
            )
        self.fft_curve_before.setData(freqs, self.smoothed_fft_before)

        # After curve — only when engaged and calibration done
        is_stft = self.engine_select.currentText() == EngineType.STFT
        calibration_done = (not is_stft) or getattr(self.engine, "calibration_complete", False)

        if self.master_btn.isChecked() and calibration_done:
            window = np.hanning(len(clean_data))
            fft_after = np.abs(np.fft.rfft(clean_data*window))[mask]
            fft_after_db = 20 * np.log10(fft_after + 1e-9)
            fft_after_db = np.maximum(fft_after_db, -140)

            if (
                self.smoothed_fft_after is not None
                and len(self.smoothed_fft_after) != len(fft_after_db)
                ):
                self.smoothed_fft_after = None
            
            if self.smoothed_fft_after is None:
                self.smoothed_fft_after = fft_after_db
            else:
                self.smoothed_fft_after = (
                    FFT_SMOOTHING_AFTER * self.smoothed_fft_after +
                    (1 - FFT_SMOOTHING_AFTER) * fft_after_db
                )
            self.fft_curve_after.setData(freqs, self.smoothed_fft_after)
        elif not self.master_btn.isChecked():
            self.fft_curve_after.setData([],[])
            self.smoothed_fft_after = None

        #print(f"Before dB range: {fft_before_db.min():.1f} to {fft_before_db.max():.1f}")

        # VU meters
        self._update_meters(raw_data, clean_data)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CleanMicGUI()
    window.show()
    sys.exit(app.exec())
