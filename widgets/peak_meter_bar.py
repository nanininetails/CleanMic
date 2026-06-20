from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor

class PeakMeterBar(QWidget):
    def __init__(self, main_color: str, peak_color: str, parent=None):
        super().__init__(parent)
        self.main_color = QColor(main_color)
        self.peak_color = QColor(peak_color)
        
        # Audio Engine Targets
        self._target_current = 0  
        self._target_peak = 0     
        
        # Smoothly animated display values
        self._display_current = 0.0
        self._display_peak = 0.0

        # Dedicated 60 FPS UI Timer
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.start(16) # ~60 frames per second

    def setValues(self, current: int, peak: int):
        self._target_current = max(0, min(1000, current))
        self._target_peak = max(0, min(1000, peak))

    def _animate(self):
        # Math: Smoothly glide the display value toward the target value
        self._display_current += (self._target_current - self._display_current) * 0.25
        self._display_peak += (self._target_peak - self._display_peak) * 0.15 # Shadow moves a bit slower
        
        # Only repaint if the bar is actively moving to save CPU
        if abs(self._target_current - self._display_current) > 0.5 or abs(self._target_peak - self._display_peak) > 0.5:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        w = rect.width()
        h = rect.height()

        # 1. Draw track background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#1A1B23"))
        painter.drawRoundedRect(0, 0, w, h, 2, 2)

        # 2. Draw the LIGHT peak shadow first
        if self._display_peak > 0:
            peak_w = int(w * (self._display_peak / 1000.0))
            painter.setBrush(self.peak_color)
            painter.drawRoundedRect(0, 0, peak_w, h, 2, 2)

        # 3. Draw the MAIN bouncing bar on top
        if self._display_current > 0:
            bar_w = int(w * (self._display_current / 1000.0))
            painter.setBrush(self.main_color)
            painter.drawRoundedRect(0, 0, bar_w, h, 2, 2)