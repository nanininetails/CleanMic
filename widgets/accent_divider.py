from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtGui import QColor


class AccentDivider(QWidget):
    def __init__(
        self,
        accent_color: str = "#00D2C4",
        separator_color: str = "#22252E",
        accent_height: int = 2,
        separator_height: int = 1,
        glow_radius: int = 15,
        show_separator: bool = True,
        parent=None,
    ):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if show_separator:
            separator = QWidget()
            separator.setFixedHeight(separator_height)
            separator.setStyleSheet(
                f"background:{separator_color};"
            )
            layout.addWidget(separator)

        accent = QWidget()
        accent.setFixedHeight(accent_height)
        accent.setStyleSheet(
            f"background:{accent_color};"
        )

        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(glow_radius)
        glow.setOffset(0)
        glow.setColor(QColor(accent_color))
        accent.setGraphicsEffect(glow)

        layout.addWidget(accent)