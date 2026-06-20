DIALOG_BASE_QSS = """
    QDialog { background-color: #161821; border: 1px solid #00D2C4; border-radius: 6px; }
    QLabel { color: #E3E4E8; font-size: 12px; font-weight: bold; margin-bottom: 2px; }
    QLineEdit, QComboBox { margin-bottom: 15px; }
    QPushButton { padding: 8px; border-radius: 4px; font-weight: bold; }
"""

SAVE_DIALOG_QSS = """
    QDialog { background-color: #161821; border: 1px solid #00D2C4; border-radius: 6px; }
    QLabel { color: #E3E4E8; font-size: 12px; font-weight: bold; margin-bottom: 5px; }
    QPushButton { padding: 8px; border-radius: 4px; font-weight: bold; }
"""

BTN_CANCEL = "background-color: #2A2D3D; color: #FFF; border: none;"
BTN_PRIMARY = "background-color: #00D2C4; color: #0E0F14; border: none;"
BTN_DANGER = "background-color: #FF0055; color: #FFF; border: none;"
BTN_SAVE = "background-color: #F2C94C; color: #0E0F14; border: none;"
BTN_DISABLED = "background-color: #1C1E2A; color: #363A4D;"

DIALOG_TITLE_QSS = "color: #00D2C4; font-size: 14px; margin-bottom: 10px;"

TITLE_BAR_BTN_QSS = """
    QPushButton { background-color: transparent; color: #8F92A1; border: none; font-weight: bold; }
    QPushButton:hover { background-color: #2A2D3D; color: #FFF; border-radius: 4px; }
"""

TITLE_BAR_CLOSE_BTN_QSS = """
    QPushButton { background-color: transparent; color: #8F92A1; border: none; font-weight: bold; }
    QPushButton:hover { background-color: #FF0055; color: #FFF; border-radius: 4px; }
"""

DRAWER_QSS = """
    QWidget { background-color: #161821; }
    QLabel { color: #E3E4E8; font-weight: bold; font-size: 11px; }
    QSlider::groove:horizontal { background: #0E0F14; height: 6px; border-radius: 3px; }
    QSlider::handle:horizontal { background: #00D2C4; width: 14px; margin: -4px 0; border-radius: 7px; }
    QSlider::handle:horizontal:disabled { background: #363A4D; }
    QSpinBox, QDoubleSpinBox { background-color: #0E0F14; color: #00D2C4; border: 1px solid #2A2D3D;
                               border-radius: 3px; padding: 2px 15px 2px 5px; }
    QSpinBox:disabled, QDoubleSpinBox:disabled { color: #8F92A1; border: 1px solid #1C1E2A; }
"""

DRAWER_BTN_SECONDARY_QSS = """
    QPushButton { background-color: #2A2D3D; color: #FFF; border: none; padding: 6px;
                  border-radius: 4px; font-weight: bold; margin-top: 5px; }
    QPushButton:hover { background-color: #00D2C4; color: #0E0F14; }
"""

DRAWER_BTN_SAVE_QSS = """
    QPushButton { background-color: #F2C94C; color: #0E0F14; border: none; padding: 6px;
                  border-radius: 4px; font-weight: bold; margin-top: 5px; }
    QPushButton:hover { background-color: #FFD966; }
    QPushButton:disabled { background-color: #1C1E2A; color: #363A4D; }
"""

CONTEXT_MENU_QSS = """
    QMenu { background-color: #161821; border: 1px solid #2A2D3D; color: #E3E4E8;
            border-radius: 4px; font-weight: bold; }
    QMenu::item { padding: 8px 24px; }
    QMenu::item:selected { background-color: #00D2C4; color: #0E0F14; }
    QMenu::separator { height: 1px; background: #2A2D3D; margin: 4px 0px; }
"""

RECORD_BTN_IDLE_QSS = """
    QPushButton {
        background-color: #1C1E2A; 
        border: 1px solid #FF0055;
        qproperty-icon: url(assets/record_idle.svg);
    }
    QPushButton:hover {
        border: 1px solid #00D2C4;
    }
"""

RECORD_BTN_ACTIVE_QSS = """
    QPushButton {
        background-color: #1C1E2A; 
        border: 1px solid #FF0055;
        qproperty-icon: url(assets/record_active.svg);
    }
"""

DRAWER_TOGGLE_BTN_QSS = """
    QPushButton { background-color: transparent; color: #8F92A1; border: none;
                  text-align: left; padding-left: 20px; }
    QPushButton:hover {
        background: qlineargradient(
            x1:0, y1:1,
            x2:0, y2:0,
            stop:0 rgba(0,210,196,100),
            stop:1 rgba(0,210,196,0)
            ); 
        color: #E3E4E8; 
        }
    QPushButton:disabled { background-color: #0E0F14; color: #0E0F14; }
    QPushButton:checked {
        background: qlineargradient(
            x1:0, y1:1,
            x2:0, y2:0,
            stop:0 rgba(0,210,196,100),
            stop:1 rgba(0,210,196,0)
            ); 
        color: #E3E4E8; 
        }
"""

METER_TRACK_QSS = """
    QProgressBar {
        background-color: #0E0F14;
        border: 1px solid #2A2D3D;
        border-radius: 2px;
        height: 6px;
    }
    QProgressBar::chunk {
        border-radius: 2px;
    }
"""

METER_LABEL_QSS = "color: #5A617A; font-size: 11px; font-weight: bold;"
METER_READOUT_QSS = "color: #8F92A1; font-size: 11px; font-family: 'Consolas'; min-width: 52px; text-align: right;"

GAIN_SLIDER_QSS = """
    QSlider::groove:horizontal {
        background: #0E0F14;
        height: 4px;
        border-radius: 2px;
        border: 1px solid #2A2D3D;
    }
    QSlider::handle:horizontal {
        background: #E3E4E8;
        width: 20px;
        height: 15px;
        margin: -10px 0;
        border-radius: 10px;
    }
    QSlider::sub-page:horizontal {
        background: #79E16C;
        border-radius: 2px;
    }
"""

BOTTOM_BAR_QSS = """
    QWidget#bottom_bar {
        background-color: transparent;
    }
"""

CHART_SEPARATOR_QSS = """
    QWidget#chart_container {
        border-top: 1px solid #2A2D3D;
    }
"""

ENGAGE_PANEL_QSS = """
    QWidget#engage_panel {
        background-color: #0E0F14;
        border-top: 1px solid #2A2D3D;
        border-right: 1px solid #2A2D3D;
    }
"""

def build_main_stylesheet() -> str:
    return """
        QMainWindow { background-color: #0E0F14; border: 1px solid #2A2D3D;}
        QLabel { color: #E3E4E8; font-family: 'Segoe UI'; font-size: 12px; font-weight: bold; }
        QGroupBox { border: 1px solid #2A2D3D; border-radius: 6px; margin-top: 15px;
                    color: #7A7D8F; font-weight: bold; padding-top: 15px; }
        QComboBox, QLineEdit { background-color: #161821; border: 1px solid #2A2D3D;
                               border-radius: 4px; padding: 6px; color: #E3E4E8; }
        QPushButton { background-color: #242736; border: 1px solid #363A4D; border-radius: 4px;
                      padding: 8px; color: #FFFFFF; font-weight: bold; }
        QPushButton:hover { background-color: #363A4D; }
        QPushButton:checked { background-color: #00D2C4; color: #0E0F14; }
        QPushButton:disabled { background-color: #161821; color: #363A4D; border: 1px dashed #2A2D3D; }

        QFrame#profile_slot { background-color: #242736; border: 1px solid #363A4D; border-radius: 4px; min-height: 38px; }
        QFrame#profile_slot:hover { background-color: #363A4D; }
        QFrame#profile_slot[active_preset="true"] { border: 2px solid #00D2C4; background-color: #1C1E2A; }
        QFrame#profile_slot[active_preset="true"]:hover { background-color: #1C1E2A; }
        QFrame#profile_slot[trash_hover="true"],
        QFrame#profile_slot[active_preset="true"][trash_hover="true"] {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0.4 #1C1E2A, stop:1 #FF0055);
            border: 2px solid #FF0055;
        }
        QFrame#profile_slot:disabled { background-color: #161821; border: 1px dashed #2A2D3D; }
        QFrame#profile_slot[active_preset="true"]:disabled { border: 2px dashed #007A72; }
        QPushButton#main_btn_inner {
            background: transparent; border: none;
            font-weight: bold; text-align: left; padding-left: 15px;
        }
        QPushButton#main_btn_inner:disabled { background: transparent; border: none; color: #363A4D; }
        QFrame#profile_slot[active_preset="true"] QPushButton#main_btn_inner { color: #00D2C4; }
        QFrame#profile_slot:disabled QPushButton#main_btn_inner { color: #363A4D; }
        QFrame#profile_slot QPushButton#trash_btn_inner {
            background-color: transparent; border: none; color: #8F92A1; font-size: 14px;
        }
        QFrame#profile_slot QPushButton#trash_btn_inner:hover { color: #FFF; }
        QFrame#profile_slot:disabled QPushButton#trash_btn_inner { color: #363A4D; }

        QProgressBar { border: 1px solid #2A2D3D; border-radius: 4px; background-color: #161821;
                       text-align: center; color: transparent; width: 20px; }
        QCheckBox { color: #E3E4E8; font-weight: bold; }
    """
