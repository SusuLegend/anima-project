"""
Floating Desktop Character UI (PySide6) — Standalone Version

Features:
- Frameless, always-on-top floating window with a character (GIF or drawn placeholder)
- Gentle autonomous movement (random wandering) and idle animation
- Click-and-drag repositioning
- System tray icon with Show/Hide and Quit options

Requirements:
- Python 3.8+
- pip install PySide6

How to run:
- Place a character GIF next to this file and set CHARACTER_GIF path below, or leave None to use a simple drawn placeholder.
- python floating_character.py
"""

import sys
import random
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QThread, Signal
import math
# LLM integration import
from llm_integration import get_llm_response

# ---------------------- Configuration ----------------------
CHARACTER_GIF = str(Path(__file__).with_suffix("").parent / "pikachu.gif")  # Use the anime GIF as the character
WANDER_INTERVAL_MS = 700
WINDOW_OPACITY = 0.95
MOVE_STEP = 12 # pixels per wander step
# -----------------------------------------------------------

# --- Worker Thread for LLM ---
class LLMWorker(QThread):
    finished = Signal(str)

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt

    def run(self):
        from llm_integration import get_llm_response
        reply = get_llm_response(self.prompt)
        self.finished.emit(reply)

class FloatingCharacter(QtWidgets.QWidget):
    def show_chat_message(self, message, duration_ms=8000):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        dialog.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        dialog.setStyleSheet("""
            QDialog { background: transparent; }
            QLabel {
                background: #e1ffc7;
                border-radius: 16px;
                padding: 12px 18px;
                color: #222;
                font-size: 16px;
                border: 2px solid #b2f2a5;
                min-width: 220px;
                max-width: 420px;
            }
        """)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        label = QtWidgets.QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)
        dialog.adjustSize()
        # Always position above the character, even if window moves
        char_geom = self.geometry()
        global_pos = self.mapToGlobal(self.rect().center())
        x = global_pos.x() - dialog.width() // 2
        y = global_pos.y() - self.height() // 2 - dialog.height() - 8
        # Clamp to top of screen if needed
        screen_geom = QtWidgets.QApplication.primaryScreen().availableGeometry()
        y = max(screen_geom.top(), y)
        dialog.move(x, y)
        QtCore.QTimer.singleShot(duration_ms, dialog.accept)
        dialog.exec()

    def show_question_dialog(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        dialog.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        dialog.setStyleSheet("""
            QDialog { background: transparent; }
            QLabel {
                background: #c7e7ff;
                border-radius: 16px;
                padding: 12px 18px;
                color: #222;
                font-size: 16px;
                border: 2px solid #a5d8f2;
                min-width: 220px;
                max-width: 420px;
            }
            QLineEdit {
                background: #fff;
                border-radius: 12px;
                font-size: 15px;
                padding: 8px 12px;
                border: 1.5px solid #b2f2a5;
                color: #222;
            }
        """)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        label = QtWidgets.QLabel("Ask Chika:")
        label.setWordWrap(True)
        layout.addWidget(label)
        input_box = QtWidgets.QLineEdit()
        input_box.setPlaceholderText("Type your question...")
        layout.addWidget(input_box)
        input_box.setFocus()
        def accept_if_enter():
            if input_box.text().strip():
                dialog.accept()
        input_box.returnPressed.connect(accept_if_enter)
        dialog.adjustSize()
        # Always position above the character, even if window moves
        global_pos = self.mapToGlobal(self.rect().center())
        x = global_pos.x() - dialog.width() // 2
        y = global_pos.y() - self.height() // 2 - dialog.height() - 8
        screen_geom = QtWidgets.QApplication.primaryScreen().availableGeometry()
        y = max(screen_geom.top(), y)
        dialog.move(x, y)
        result = dialog.exec()
        return input_box.text().strip() if result == QtWidgets.QDialog.Accepted else None
    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowOpacity(WINDOW_OPACITY)

        self.setFixedSize(200, 200)
        self.dragging = True
        # Initialize velocity to zero; wander timer will set direction later
        self.last_mouse_pos = None
        self.vx = 0
        self.vy = 0

        self._build_ui()

        self.wander_timer = QtCore.QTimer(self, interval=WANDER_INTERVAL_MS)
        self.wander_timer.timeout.connect(self._wander_step)
        self.wander_timer.start()

        self._create_tray()

        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.move(screen.center() - self.rect().center())

    def _create_tray(self):
        self.tray = QtWidgets.QSystemTrayIcon(self)
        icon = QtGui.QIcon.fromTheme("applications-games")
        if icon.isNull():
            pix = QtGui.QPixmap(64, 64)
            pix.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(pix)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QBrush(QtGui.QColor(30, 144, 255)))
            p.drawEllipse(0, 0, 64, 64)
            p.end()
            icon = QtGui.QIcon(pix)
        self.tray.setIcon(icon)

        menu = QtWidgets.QMenu()
        show_action = menu.addAction("Show/Hide")
        show_action.triggered.connect(self._toggle_visibility)
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(QtWidgets.QApplication.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _toggle_visibility(self):
        self.setVisible(not self.isVisible())

    def _on_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_visibility()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.char_label = QtWidgets.QLabel()
        self.char_label.setFixedSize(180, 180)
        self.char_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.char_label, alignment=QtCore.Qt.AlignHCenter)

        self.movie = None
        if CHARACTER_GIF and Path(CHARACTER_GIF).exists():
            try:
                self.movie = QtGui.QMovie(CHARACTER_GIF)
                if self.movie.isValid():
                    self.movie.setScaledSize(QtCore.QSize(180, 180))
                    self.char_label.setMovie(self.movie)
                    self.movie.start()
            except Exception:
                self.movie = None

        if not self.movie:
            pix = QtGui.QPixmap(self.char_label.size())
            pix.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(pix)
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            p.setBrush(QtGui.QBrush(QtGui.QColor(255, 200, 0)))
            p.setPen(QtGui.QPen(QtGui.QColor(150, 70, 0)))
            p.drawEllipse(10, 10, 160, 160)
            p.end()
            self.char_label.setPixmap(pix)

        self.setLayout(layout)

    # ---------- Interaction & Movement ----------
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            text = self.show_question_dialog()
            if text:
                self.show_chat_message("Thinking...", duration_ms=1200)
                QtWidgets.QApplication.processEvents()
                # Start LLM in background thread
                self.llm_worker = LLMWorker(text)
                self.llm_worker.finished.connect(self._show_llm_reply)
                self.llm_worker.start()
            self.dragging = True
            self.last_mouse_pos = event.globalPosition().toPoint()
            event.accept()

    def _show_llm_reply(self, reply):
        self.show_chat_message(reply)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.dragging:
            new_pos = event.globalPosition().toPoint()
            delta = new_pos - self.last_mouse_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.last_mouse_pos = new_pos
            event.accept()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self.dragging = False
        self.last_mouse_pos = None
        event.accept()

    def _wander_step(self):
        if self.dragging or not self.isVisible():
            return
        geom = QtWidgets.QApplication.primaryScreen().availableGeometry()
        x, y = self.x(), self.y()

        # More frequent and visible randomization
        if random.random() < 0.6:  # Increase chance to change direction
            ang = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.7, 1.5) * MOVE_STEP  # More visible step
            self.vx = int(speed * math.cos(ang))
            self.vy = int(speed * math.sin(ang))
        # Occasionally stop or reverse
        if random.random() < 0.1:
            self.vx = -self.vx
            self.vy = -self.vy
        if random.random() < 0.05:
            self.vx = 0
            self.vy = 0

        nx = x + self.vx
        ny = y + self.vy

        nx = max(geom.left(), min(nx, geom.right() - self.width()))
        ny = max(geom.top(), min(ny, geom.bottom() - self.height()))

        self.move(nx, ny)


def main():
    app = QtWidgets.QApplication([])
    app.setApplicationName("FloatingBuddyStandalone")

    win = FloatingCharacter()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()