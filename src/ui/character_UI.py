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

import sys, json, random
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import QThread, Signal
import math
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.ai_brain.gemini_integration import GeminiIntegration

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"
def load_config():
    """Load configuration from config.json or use defaults"""
    default_config = {
        "llm": {
            "model": "llama3.2:latest",
            "system_prompt": "You are Chika Fujiwara from the anime 'Kaguya-sama: Love is War'. Always answer in a cute, bubbly, and playful manner, as if you are Chika. If asked about yourself, respond as Chika would.",
            "timeout": 30.0
        },
        "ui": {
            "character_gif": "assets/expression1.gif",
            "window_opacity": 0.95,
            "window_size": [200, 200],
            "move_step": 12,
            "wander_interval_ms": 700
        },
        "rag": {
            "enabled": False,
            "pinecone_api_key": "",
            "index_name": "rag-documents",
            "embedding_model": "all-MiniLM-L6-v2",
            "cloud": "aws",
            "region": "us-east-1"
        },
        "notifications": {
            "email_enabled": False,
            "email_credential_path": "src/notifications/email_credential.json",
            "poll_interval": 10
        }
    }
    
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                print("✅ Loaded configuration from config.json")
                return config
        except Exception as e:
            print(f"⚠️ Error loading config: {e}")
            print("Using default configuration")
            return default_config
    else:
        print("⚠️ config.json not found, using default configuration")
        print(f"Run settings_manager.py to create a configuration file")
        return default_config

# Load configuration
CONFIG = load_config()

# ---------------------- Configuration ----------------------
CHARACTER_GIF = str(Path(__file__).parent.parent.parent / CONFIG["ui"]["character_gif"])  # Use the path from config.json
print("Character GIF path:", CHARACTER_GIF)
WANDER_INTERVAL_MS = 700
WINDOW_OPACITY = 0.95
MOVE_STEP = 12 # pixels per wander step
# -----------------------------------------------------------

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
        self.dragging = False  # Changed from True
        self.move_mode = False  # NEW
        # Initialize velocity to zero; wander timer will set direction later
        self.last_mouse_pos = None
        self.vx = 0
        self.vy = 0
        self.menu_visible = False  # NEW
        self.menu_buttons = []  # NEW

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
        print(f"Character GIF path: {CHARACTER_GIF}")
        if CHARACTER_GIF and Path(CHARACTER_GIF).exists():
            print("GIF file exists.")
            try:
                self.movie = QtGui.QMovie(CHARACTER_GIF)
                if self.movie.isValid():
                    print("QMovie loaded GIF successfully.")
                    self.movie.setScaledSize(QtCore.QSize(180, 180))
                    self.movie.setCacheMode(QtGui.QMovie.CacheAll)
                    self.movie.setSpeed(100)  # 100% speed
                    # PySide6 QMovie does not support setLoopCount; it loops by default
                    self.char_label.setMovie(self.movie)
                    self.movie.start()
                else:
                    print("QMovie failed to load GIF: invalid format or corrupted file.")
            except Exception as e:
                print(f"Exception loading GIF: {e}")
                self.movie = None
        else:
            print("GIF file does not exist at the specified path.")

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
    def _create_circular_menu(self):
        """Create circular menu buttons around the character"""
        if self.menu_visible:
            self._hide_circular_menu()
            return
        
        self.menu_visible = True
        center_x, center_y = 100, 100  # Center of the 200x200 widget
        radius = 110
        
        # Define buttons: (angle_degrees, label, icon_text, callback)
        buttons_config = [
            (0, "Prompt", "💬", self._on_prompt_click),
            (120, "Move", "✋", self._on_move_click),
            (240, "Settings", "⚙️", self._on_settings_click),
        ]
        
        for angle, label, icon, callback in buttons_config:
            btn = QtWidgets.QPushButton(icon, self)
            btn.setFixedSize(50, 50)
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #4a90e2, stop:1 #357abd);
                    border: 3px solid white;
                    border-radius: 25px;
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #5ba3ff, stop:1 #4a90e2);
                    border: 3px solid #ffe082;
                }
                QPushButton:pressed {
                    background: #2d5f8d;
                }
            """)
            btn.setToolTip(label)
            btn.clicked.connect(callback)
            
            # Calculate position
            angle_rad = math.radians(angle - 90)  # -90 to start from top
            x = center_x + radius * math.cos(angle_rad) - 25  # -25 to center button
            y = center_y + radius * math.sin(angle_rad) - 25
            
            btn.move(int(x), int(y))
            btn.show()
            btn.raise_()
            self.menu_buttons.append(btn)

    def _hide_circular_menu(self):
        """Hide and remove circular menu buttons"""
        for btn in self.menu_buttons:
            btn.deleteLater()
        self.menu_buttons.clear()
        self.menu_visible = False

    def _on_prompt_click(self):
        """Handle prompt button click"""
        self._hide_circular_menu()
        text = self.show_question_dialog()
        if text:
            self.show_chat_message("Thinking...", duration_ms=1200)
            QtWidgets.QApplication.processEvents()
            if not hasattr(self, 'llm_convo'):
                self.llm_convo = GeminiIntegration(system_prompt=CONFIG["llm"].get("system_prompt"))
            reply = self.llm_convo.get_response(text)
            self._show_llm_reply(reply)

    def _on_move_click(self):
        """Toggle move mode"""
        self.move_mode = not self.move_mode
        self._hide_circular_menu()
        if self.move_mode:
            self.show_chat_message("Move mode ON - Click and drag me!", duration_ms=2000)
            self.setCursor(QtCore.Qt.OpenHandCursor)
        else:
            self.show_chat_message("Move mode OFF", duration_ms=2000)
            self.unsetCursor()

    def _on_settings_click(self):
        """Open settings manager"""
        self._hide_circular_menu()
        import subprocess
        settings_path = Path(__file__).parent.parent.parent / "settings_manager.py"
        if settings_path.exists():
            try:
                subprocess.Popen([sys.executable, str(settings_path)])
                self.show_chat_message("Opening settings...", duration_ms=2000)
            except Exception as e:
                self.show_chat_message(f"Error: {e}", duration_ms=3000)
        else:
            self.show_chat_message("Settings manager not found!", duration_ms=3000)
        
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            # Check if clicking on a menu button
            if self.menu_visible:
                for btn in self.menu_buttons:
                    if btn.geometry().contains(event.pos()):
                        return  # Let button handle the click
                # Clicked outside menu - hide it
                self._hide_circular_menu()
                return
        
        # Check if in move mode
        if self.move_mode:
            self.dragging = True
            self.last_mouse_pos = event.globalPosition().toPoint()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        else:
            # Show circular menu
            self._create_circular_menu()
        
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
        if self.dragging:  # Added check
            self.dragging = False
            self.last_mouse_pos = None
            if self.move_mode:  # NEW
                self.setCursor(QtCore.Qt.OpenHandCursor)  # NEW
            event.accept()

    def _wander_step(self):
        if self.dragging or not self.isVisible() or self.move_mode or self.menu_visible:  # Added "or self.move_mode or self.menu_visible"
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