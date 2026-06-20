import sys
import logging
from PyQt6.QtWidgets import QApplication

from gui import CleanMicGUI

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    setup_logging()
    logging.info("Starting CleanMic application...")

    app = QApplication(sys.argv)

    window = CleanMicGUI()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()