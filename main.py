# Monkey Patch for the df logging errors
import sys
import os
import subprocess

# --- 1. HEADLESS STREAM PATCH (Prevents TypeError: NoneType) ---
if sys.stdout is None: sys.stdout = open(os.devnull, 'w')
if sys.stderr is None: sys.stderr = open(os.devnull, 'w')

# --- 2. WORKING DIRECTORY FIX (Prevents double-click path mismatch) ---
if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

# --- 3. GIT SUBPROCESS SHIELD ---
orig_check_output = subprocess.check_output
def safe_check_output(args, *extra_args, **kwargs):
    cmd = " ".join(args) if isinstance(args, list) else str(args)
    if "git" in cmd: return b"frozen"
    return orig_check_output(args, *extra_args, **kwargs)
subprocess.check_output = safe_check_output

orig_run = subprocess.run
def safe_run(args, *extra_args, **kwargs):
    cmd = " ".join(args) if isinstance(args, list) else str(args)
    if "git" in cmd:
        class MockProcess:
            returncode = 0
            stdout = b"frozen"
            stderr = b""
        return MockProcess()
    return orig_run(args, *extra_args, **kwargs)
subprocess.run = safe_run

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