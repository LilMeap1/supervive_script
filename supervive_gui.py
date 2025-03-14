import sys
import json
import subprocess
import threading
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QProgressBar, QTextEdit, QLabel
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

script_dir = os.path.dirname(os.path.abspath(__file__))  # Get directory of the .exe
supervive_path = os.path.join(script_dir, "DONOTRUN.exe")  # Full path to supervive.py
# File path for teams.json
TEAM_FILE = "teams.json"

# ✅ Thread to Run `supervive.py` Without Freezing the GUI
class ProcessingThread(QThread):
    progress_signal = pyqtSignal(int)  # Signal to update progress bar
    log_signal = pyqtSignal(str)  # Signal to update log window

    def run(self):
        try:
            with open(TEAM_FILE, "r", encoding="utf-8") as file:
                teams = json.load(file)

            # ✅ Count enabled teams and total players
            enabled_teams = [team for team in teams.values() if team["enabled"]]
            total_players = sum(len(team["players"]) for team in enabled_teams)
            if not enabled_teams:
                self.log_signal.emit(" No teams are enabled for processing.")
                self.progress_signal.emit(100)  # Instantly complete progress
                return

            self.log_signal.emit(f"------> Starting processing for {len(enabled_teams)} teams ({total_players} players)...")

           

            if getattr(sys, 'frozen', False):
                python_exe = os.path.join(os.path.dirname(sys.executable), "python.exe")  # Adjust path

            supervive_script = os.path.join(os.path.dirname(sys.executable), "DONOTRUN.exe")  # Ensure correct path
            
            python_exe = sys.executable if sys.executable.endswith("python.exe") else "pythonw.exe"
            process = subprocess.Popen(
                ["DONOTRUN.exe"],  # ✅ Ensures `supervive.py` runs in the correct Python environment
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,  # ✅ Ensures text mode output
                bufsize=1,
                universal_newlines=True
            )

            processed_players = 0

            def read_stream(stream, update_func):
                """ Reads subprocess output line-by-line in real-time """
                while True:
                    line = stream.readline()
                    if not line:
                        break
                    clean_line = self.clean_log(line.strip())
                    if clean_line and not self.is_suppressed_error(clean_line):
                        update_func(clean_line)
                        QApplication.processEvents()  # ✅ Force GUI update instantly

                    # ✅ Detect when a player is processed
                    if "-> Refreshed match history for" in clean_line:
                        nonlocal processed_players
                        processed_players += 1
                        progress = int((processed_players / total_players) * 100)
                        self.progress_signal.emit(progress)

            stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, self.log_signal.emit))
            stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, self.log_signal.emit))

            stdout_thread.start()
            stderr_thread.start()

            process.wait()  # ✅ Wait for process to finish
            stdout_thread.join()
            stderr_thread.join()

            self.log_signal.emit("🎉 All teams successfully processed!")  # ✅ Only log once
            self.progress_signal.emit(100)  # Ensure progress bar reaches 100%

        except Exception as e:
            self.log_signal.emit(f"❌ Error: {str(e)}")

    @staticmethod
    def clean_log(text):
        """ Remove unwanted symbols and unnecessary log messages. """
        unwanted_symbols = ["ðŸ”", "ðŸ‘", "ðŸš", "â€", "âœ"]
        for symbol in unwanted_symbols:
            text = text.replace(symbol, "")
        return text

    @staticmethod
    def is_suppressed_error(text):
        """ Suppresses known errors that don't affect functionality. """
        suppressed_errors = [
            "worksheet.update",  # Google Sheets API warning
            "DeprecationWarning",  # Python warnings
            "All teams successfully processed!"  # ✅ Prevents double logging
        ]
        return any(err in text for err in suppressed_errors)


# ✅ GUI Class
class SuperviveGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Supervive Processing")
        self.setGeometry(100, 100, 600, 350)

        layout = QVBoxLayout()

        # ✅ Title
        self.title_label = QLabel("📊 Supervive Team Processing")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # ✅ Log Window
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        layout.addWidget(self.log_window)

        # ✅ Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)  # Start at 0%
        layout.addWidget(self.progress_bar)

        # ✅ Start Button
        self.start_button = QPushButton("Start Calculating")
        self.start_button.clicked.connect(self.start_processing)
        layout.addWidget(self.start_button)

        self.setLayout(layout)

    def start_processing(self):
        self.log_window.clear()
        self.progress_bar.setValue(0)

        # ✅ Start processing in a separate thread
        self.thread = ProcessingThread()
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.log_signal.connect(self.update_log)
        self.thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_log(self, message):
        self.log_window.append(message)
        self.log_window.ensureCursorVisible()  # Auto-scroll log window
        QApplication.processEvents()  # ✅ Force GUI update instantly

# ✅ Run the GUI
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SuperviveGUI()
    window.show()
    sys.exit(app.exec())
