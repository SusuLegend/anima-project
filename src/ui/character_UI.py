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
import os
import psutil
import requests
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
class QuestionBubble(QtWidgets.QDialog):
    """Interactive question input speech bubble"""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_widget = parent
        self.input_text = ""
        
        # Window setup
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # Dimensions
        bubble_width = 350
        bubble_height = 120
        
        # Padding values
        horizontal_padding = 20
        vertical_padding = 15
        
        # Tail properties
        self.tail_height = 20
        
        # Set widget size
        self.setFixedSize(bubble_width, bubble_height + self.tail_height)
        
        # Layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(horizontal_padding, vertical_padding, horizontal_padding, vertical_padding + self.tail_height)
        layout.setSpacing(10)
        
        # Label
        self.label = QtWidgets.QLabel("Ask Chika:")
        self.label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #222;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.label)
        
        # Input box
        self.input_box = QtWidgets.QLineEdit()
        self.input_box.setPlaceholderText("Type your question...")
        self.input_box.setStyleSheet("""
            QLineEdit {
                background: white;
                border: 2px solid #4a90e2;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 15px;
                color: #222;
            }
            QLineEdit:focus {
                border: 2px solid #357abd;
            }
        """)
        self.input_box.returnPressed.connect(self._accept_if_valid)
        layout.addWidget(self.input_box)
        
    def paintEvent(self, event):
        """Draw the manga-style speech bubble"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        # Bubble dimensions
        bubble_rect = QtCore.QRectF(0, 0, self.width(), self.height() - self.tail_height)
        
        # Create path for bubble with tail
        path = QtGui.QPainterPath()
        
        # Main bubble (rounded rectangle)
        path.addRoundedRect(bubble_rect, 15, 15)
        
        # Tail (pointing down to character)
        tail_start_x = self.width() / 2 - 15
        tail_tip_x = self.width() / 2
        tail_end_x = self.width() / 2 + 15
        tail_start_y = self.height() - self.tail_height
        tail_tip_y = self.height()
        
        tail = QtGui.QPainterPath()
        tail.moveTo(tail_start_x, tail_start_y)
        tail.lineTo(tail_tip_x, tail_tip_y)
        tail.lineTo(tail_end_x, tail_start_y)
        tail.closeSubpath()
        
        path.addPath(tail)
        
        # Draw white fill with black outline (classic manga style)
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 3))  # Black outline
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))  # White fill
        painter.drawPath(path)
        
        # Optional: Add inner shadow effect for depth
        shadow_pen = QtGui.QPen(QtGui.QColor(200, 200, 200), 1)
        painter.setPen(shadow_pen)
        inner_rect = bubble_rect.adjusted(2, 2, -2, -2)
        painter.drawRoundedRect(inner_rect, 13, 13)
        
    def show_bubble(self):
        """Position and show the speech bubble above the character"""
        # Position above the character
        global_pos = self.parent_widget.mapToGlobal(self.parent_widget.rect().center())
        x = global_pos.x() - self.width() // 2
        y = global_pos.y() - self.parent_widget.height() // 2 - self.height() - 5
        
        # Clamp to screen bounds
        screen_geom = QtWidgets.QApplication.primaryScreen().availableGeometry()
        x = max(screen_geom.left(), min(x, screen_geom.right() - self.width()))
        y = max(screen_geom.top(), y)
        
        self.move(x, y)
        self.show()
        
        # Set focus to input box
        self.input_box.setFocus()
    
    def _accept_if_valid(self):
        """Accept dialog if input is not empty"""
        if self.input_box.text().strip():
            self.input_text = self.input_box.text().strip()
            self.accept()
    
    def get_input(self):
        """Return the input text"""
        return self.input_text
    
class SpeechBubble(QtWidgets.QWidget):
    """Custom manga-style speech bubble widget"""
    def __init__(self, parent, message, duration_ms=8000):
        super().__init__(parent)
        self.parent_widget = parent
        self.message = message
        self.duration_ms = duration_ms
        
        # Window setup
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # Calculate dimensions dynamically based on message length
        message_length = len(message)
        
        # Adjust max dimensions based on message length
        if message_length < 30:
            max_bubble_width = 250
            max_bubble_height = 80
        elif message_length > 100:
            max_bubble_width = 400
            max_bubble_height = 120
        elif message_length > 200:
            max_bubble_width = 500
            max_bubble_height = 180
        else:
            max_bubble_width = 600
            max_bubble_height = 250
        
        min_bubble_width = 160
        
        # Padding values
        horizontal_padding = 30
        vertical_padding = 20
        
        # Create text label to measure size
        self.text_label = QtWidgets.QLabel(message)
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(QtCore.Qt.AlignCenter)  # Center text
        self.text_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #222;
                font-size: 15px;
                font-weight: bold;
                padding: 0px;
            }
        """)
        
        # Calculate appropriate width based on text length
        font_metrics = self.text_label.fontMetrics()
        text_width = font_metrics.horizontalAdvance(message)
        
        # Determine bubble width (adjustable based on message length)
        # For short messages, use a compact width
        if text_width < min_bubble_width - (horizontal_padding * 2):
            bubble_width = text_width + (horizontal_padding * 2)
            bubble_width = max(bubble_width, min_bubble_width)  # Ensure minimum
        elif text_width > max_bubble_width - (horizontal_padding * 2):
            bubble_width = max_bubble_width
        else:
            bubble_width = text_width + (horizontal_padding * 2)
            
        # Set label width for proper word wrap
        self.text_label.setMaximumWidth(bubble_width - (horizontal_padding * 2))
        self.text_label.setMinimumWidth(bubble_width - (horizontal_padding * 2))
        self.text_label.adjustSize()
        
        # Calculate height based on wrapped text
        text_height = self.text_label.sizeHint().height()
        bubble_height = text_height + (vertical_padding * 2)
        
        # Cap at max height, but remove the cap if text is short
        if bubble_height > max_bubble_height:
            bubble_height = max_bubble_height
            # Enable scrolling for very long text by adjusting label
            self.text_label.setMaximumHeight(max_bubble_height - (vertical_padding * 2))
        
        # Tail properties
        self.tail_height = 20
        
        # Set widget size
        self.setFixedSize(bubble_width, bubble_height + self.tail_height)
        
        # Layout for text - centered both horizontally and vertically
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(horizontal_padding, vertical_padding, horizontal_padding, vertical_padding + self.tail_height)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.text_label, alignment=QtCore.Qt.AlignCenter)
        
    def paintEvent(self, event):
        """Draw the manga-style speech bubble"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        # Bubble dimensions
        bubble_rect = QtCore.QRectF(0, 0, self.width(), self.height() - self.tail_height)
        
        # Create path for bubble with tail
        path = QtGui.QPainterPath()
        
        # Main bubble (rounded rectangle)
        path.addRoundedRect(bubble_rect, 15, 15)
        
        # Tail (pointing down to character)
        tail_start_x = self.width() / 2 - 15
        tail_tip_x = self.width() / 2
        tail_end_x = self.width() / 2 + 15
        tail_start_y = self.height() - self.tail_height
        tail_tip_y = self.height()
        
        tail = QtGui.QPainterPath()
        tail.moveTo(tail_start_x, tail_start_y)
        tail.lineTo(tail_tip_x, tail_tip_y)
        tail.lineTo(tail_end_x, tail_start_y)
        tail.closeSubpath()
        
        path.addPath(tail)
        
        # Draw white fill with black outline (classic manga style)
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 3))  # Black outline
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))  # White fill
        painter.drawPath(path)
        
        # Optional: Add inner shadow effect for depth
        shadow_pen = QtGui.QPen(QtGui.QColor(200, 200, 200), 1)
        painter.setPen(shadow_pen)
        inner_rect = bubble_rect.adjusted(2, 2, -2, -2)
        painter.drawRoundedRect(inner_rect, 13, 13)
        
    def show_bubble(self):
        """Position and show the speech bubble above the character"""
        # Position above the character
        global_pos = self.parent_widget.mapToGlobal(self.parent_widget.rect().center())
        x = global_pos.x() - self.width() // 2
        y = global_pos.y() - self.parent_widget.height() // 2 - self.height() - 5
        
        # Clamp to screen bounds
        screen_geom = QtWidgets.QApplication.primaryScreen().availableGeometry()
        x = max(screen_geom.left(), min(x, screen_geom.right() - self.width()))
        y = max(screen_geom.top(), y)
        
        self.move(x, y)
        self.show()
        
        # Auto-close after duration
        QtCore.QTimer.singleShot(self.duration_ms, self.close)

class ToolsDialog(QtWidgets.QDialog):
    """Dialog for selecting and executing tools from the tools folder"""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_widget = parent
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the tools dialog UI"""
        self.setWindowTitle("🔧 Tools")
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowStaysOnTopHint)
        self.setMinimumSize(500, 400)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Title
        title = QtWidgets.QLabel("Select a tool to use:")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # Tab widget for different listener categories
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self.create_google_tools_tab(), "📧 Google")
        tabs.addTab(self.create_microsoft_tools_tab(), "📅 Microsoft")
        tabs.addTab(self.create_whatsapp_tools_tab(), "💬 WhatsApp")
        tabs.addTab(self.create_other_tools_tab(), "🌐 Other")
        layout.addWidget(tabs)
        
        # Close button
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def create_google_tools_tab(self):
        """Create Google tools tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # Gmail section
        gmail_group = QtWidgets.QGroupBox("Gmail")
        gmail_layout = QtWidgets.QVBoxLayout()
        
        check_emails_btn = QtWidgets.QPushButton("📬 Check New Emails")
        check_emails_btn.clicked.connect(lambda: self.execute_tool("gmail", "check_emails"))
        gmail_layout.addWidget(check_emails_btn)
        
        gmail_group.setLayout(gmail_layout)
        layout.addWidget(gmail_group)
        
        layout.addStretch()
        return tab
    
    def create_microsoft_tools_tab(self):
        """Create Microsoft tools tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # Outlook section
        outlook_group = QtWidgets.QGroupBox("Outlook")
        outlook_layout = QtWidgets.QVBoxLayout()
        
        check_outlook_btn = QtWidgets.QPushButton("📧 Check Outlook Data")
        check_outlook_btn.clicked.connect(lambda: self.execute_tool("outlook", "check_all"))
        outlook_layout.addWidget(check_outlook_btn)
        
        check_emails_btn = QtWidgets.QPushButton("📬 Check New Emails")
        check_emails_btn.clicked.connect(lambda: self.execute_tool("outlook", "check_emails"))
        outlook_layout.addWidget(check_emails_btn)
        
        check_events_btn = QtWidgets.QPushButton("📅 Check Calendar Events")
        check_events_btn.clicked.connect(lambda: self.execute_tool("outlook", "check_events"))
        outlook_layout.addWidget(check_events_btn)
        
        check_tasks_btn = QtWidgets.QPushButton("✅ Check Tasks")
        check_tasks_btn.clicked.connect(lambda: self.execute_tool("outlook", "check_tasks"))
        outlook_layout.addWidget(check_tasks_btn)
        
        outlook_group.setLayout(outlook_layout)
        layout.addWidget(outlook_group)
        
        layout.addStretch()
        return tab
    
    def create_whatsapp_tools_tab(self):
        """Create WhatsApp tools tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        whatsapp_group = QtWidgets.QGroupBox("WhatsApp")
        whatsapp_layout = QtWidgets.QVBoxLayout()
        
        check_messages_btn = QtWidgets.QPushButton("💬 Check New Messages")
        check_messages_btn.clicked.connect(lambda: self.execute_tool("whatsapp", "check_messages"))
        whatsapp_layout.addWidget(check_messages_btn)
        
        whatsapp_group.setLayout(whatsapp_layout)
        layout.addWidget(whatsapp_group)
        
        layout.addStretch()
        return tab
    
    def create_other_tools_tab(self):
        """Create other tools tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # Weather section
        weather_group = QtWidgets.QGroupBox("Weather")
        weather_layout = QtWidgets.QVBoxLayout()
        
        check_weather_btn = QtWidgets.QPushButton("🌤️ Check Weather")
        check_weather_btn.clicked.connect(lambda: self.execute_tool("weather", "check_weather"))
        weather_layout.addWidget(check_weather_btn)
        
        weather_group.setLayout(weather_layout)
        layout.addWidget(weather_group)
        
        # Web Search section
        search_group = QtWidgets.QGroupBox("Web Search")
        search_layout = QtWidgets.QVBoxLayout()
        
        web_search_btn = QtWidgets.QPushButton("🔍 Web Search")
        web_search_btn.clicked.connect(lambda: self.execute_tool("search", "web_search"))
        search_layout.addWidget(web_search_btn)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        layout.addStretch()
        return tab
    
    def execute_tool(self, category, action):
        """Execute a tool based on category and action"""
        self.parent_widget.show_chat_message(f"Executing {action}...", duration_ms=2000)
        QtWidgets.QApplication.processEvents()
        
        try:
            from urllib.parse import urlencode
            
            base_url = "http://127.0.0.1:8576"
            
            if category == "gmail":
                # Note: Gmail API not yet exposed via tools_app.py
                result = "Gmail integration coming soon!"
                
            elif category == "outlook":
                response = requests.get(f"{base_url}/outlook", timeout=50)
                if response.status_code == 200:
                    data = response.json()
                    if action == "check_all":
                        emails = data.get('emails', [])
                        events = data.get('events', [])
                        tasks = data.get('tasks', [])
                        result = f"📧 {len(emails)} new emails, 📅 {len(events)} events, ✅ {len(tasks)} tasks"
                    elif action == "check_emails":
                        emails = data.get('emails', [])
                        if emails:
                            email_list = "\n".join([f"• {e.get('subject', 'No subject')}" for e in emails[:3]])
                            result = f"📬 {len(emails)} new emails:\n{email_list}"
                        else:
                            result = "📭 No new emails"
                    elif action == "check_events":
                        events = data.get('events', [])
                        if events:
                            event_list = "\n".join([f"• {e.get('subject', 'No title')}" for e in events[:3]])
                            result = f"📅 {len(events)} upcoming events:\n{event_list}"
                        else:
                            result = "📅 No upcoming events"
                    elif action == "check_tasks":
                        tasks = data.get('tasks', [])
                        if tasks:
                            task_list = "\n".join([f"• {t.get('title', 'No title')}" for t in tasks[:3]])
                            result = f"✅ {len(tasks)} tasks:\n{task_list}"
                        else:
                            result = "✅ No pending tasks"
                else:
                    result = f"Error: {response.status_code}"
                    
            elif category == "whatsapp":
                response = requests.get(f"{base_url}/whatsapp", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    messages = data.get('messages', [])
                    if messages:
                        msg_list = "\n".join([f"• {m.get('senderName', 'Unknown')}: {m.get('text', '')[:30]}..." for m in messages[-3:]])
                        result = f"💬 {len(messages)} messages:\n{msg_list}"
                    else:
                        result = "💬 No new messages"
                else:
                    result = f"Error: {response.status_code}"
                    
            elif category == "weather":
                # Prompt for city
                city, ok = QtWidgets.QInputDialog.getText(
                    self, "Weather Check", "Enter city name:"
                )
                if ok and city:
                    params = urlencode({"city": city, "days": 1, "formatted": True})
                    response = requests.get(f"{base_url}/weather?{params}", timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get('text', 'No data')
                    else:
                        result = f"Error: {response.status_code}"
                else:
                    return
                    
            elif category == "search":
                # Prompt for search query
                query, ok = QtWidgets.QInputDialog.getText(
                    self, "Web Search", "Enter search query:"
                )
                if ok and query:
                    params = urlencode({"query": query, "max_results": 3, "formatted": True})
                    response = requests.get(f"{base_url}/search?{params}", timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get('text', 'No results')
                    else:
                        result = f"Error: {response.status_code}"
                else:
                    return
            else:
                result = "Unknown tool category"
            
            self.parent_widget.show_chat_message(result)
            
        except requests.exceptions.ConnectionError:
            self.parent_widget.show_chat_message(
                "⚠️ Cannot connect to tools API. Please make sure tools_app.py is running.",
                duration_ms=5000
            )
        except Exception as e:
            self.parent_widget.show_chat_message(f"Error: {str(e)}", duration_ms=5000)
            print(f"Tool execution error: {e}")

class FloatingCharacter(QtWidgets.QWidget):
    def show_chat_message(self, message, duration_ms=None):
        """Show message in a manga-style speech bubble with auto-adjusted duration"""
        # Calculate duration based on message length if not provided
        if duration_ms is None:
            # Base duration: 3 seconds
            # Add 50ms per character (average reading speed ~200 words/min = ~20 chars/sec)
            # Minimum 2 seconds, maximum 20 seconds
            char_count = len(message)
            calculated_duration = 3000 + (char_count * 50)
            duration_ms = max(2000, min(calculated_duration, 20000))
        
        dialog = SpeechBubble(self, message, duration_ms)
        dialog.show_bubble()

    def show_question_dialog(self):
        """Show question input in a manga-style speech bubble"""
        dialog = QuestionBubble(self)
        dialog.show_bubble()
        result = dialog.exec()
        return dialog.get_input() if result == QtWidgets.QDialog.Accepted else None

    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowOpacity(WINDOW_OPACITY)

        self.setFixedSize(200, 200)
        self.dragging = False
        self.move_mode = False
        self.last_mouse_pos = None
        self.vx = 0
        self.vy = 0
        self.menu_visible = False
        self.menu_buttons = []

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
                    self.movie.setSpeed(100)
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
        """Create circular menu buttons hovering over the character at 10, 11, and 12 o'clock positions"""
        if self.menu_visible:
            self._hide_circular_menu()
            return
        
        self.menu_visible = True
        
        # Get the center position of the character window in global coordinates
        global_center = self.mapToGlobal(self.rect().center())
        center_x, center_y = global_center.x(), global_center.y()
        radius = 100  # Closer distance to keep buttons over the GIF
        
        # Define buttons at 10, 11, and 12 o'clock: (angle_degrees, label, icon_text, callback)
        # Angles: 240° (10 o'clock), 270° (12 o'clock), 300° (11 o'clock)
        buttons_config = [
            (360, "Prompt", "💬", self._on_prompt_click),      
            (310, "Move", "✋", self._on_move_click),      
            (260, "Close", "❌", self._on_quick_close_click),
            (210, "Tools", "🔧", self._on_tools_click)         
        ]
        
        for angle, label, icon, callback in buttons_config:
            # Create as a top-level widget
            btn = QtWidgets.QPushButton(icon)
            btn.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
            btn.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            btn.setFixedSize(60, 60)
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #4a90e2, stop:1 #357abd);
                    border: 3px solid white;
                    border-radius: 30px;
                    color: white;
                    font-size: 24px;
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
            
            # Calculate position in global coordinates
            angle_rad = math.radians(angle - 90)  # -90 to start from top
            x = center_x + radius * math.cos(angle_rad) - 30  # -30 to center button (half of 60)
            y = center_y + radius * math.sin(angle_rad) - 30
            
            btn.move(int(x), int(y))
            btn.show()
            self.menu_buttons.append(btn)

    def _hide_circular_menu(self):
        """Hide and remove circular menu buttons"""
        for btn in self.menu_buttons:
            btn.close()
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
        """Activate move mode"""
        self._hide_circular_menu()
        
        if not self.move_mode:
            # Enable move mode
            self.move_mode = True
            self.show_chat_message("Move mode ON - Click and drag me!", duration_ms=2000)
            self.setCursor(QtCore.Qt.OpenHandCursor)

    def _on_quick_close_click(self):
        """Quick close - shut down both character and settings manager"""
        self._hide_circular_menu()
        
        reply = QtWidgets.QMessageBox.question(
            self,
            "Quick Close",
            "Close both Character and Settings Manager?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                # Find and terminate settings manager
                current_pid = os.getpid()
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = proc.info.get('cmdline')
                        if cmdline and any('settings_manager.py' in str(arg) for arg in cmdline):
                            if proc.info['pid'] != current_pid:
                                proc.terminate()
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except Exception as e:
                print(f"Error closing settings manager: {e}")
            
            # Close this character window
            QtWidgets.QApplication.quit()
    def _on_tools_click(self):
        """Show tools selection dialog"""
        self._hide_circular_menu()
        dialog = ToolsDialog(self)
        dialog.exec()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            # If menu is visible, clicking anywhere hides it
            if self.menu_visible:
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
        if self.dragging:
            self.dragging = False
            self.last_mouse_pos = None
            
            if self.move_mode:
                # Ask if user wants to disable move mode after dragging
                reply = QtWidgets.QMessageBox.question(
                    self,
                    "Move Mode",
                    "Are you done moving? Disable move mode?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                )
                if reply == QtWidgets.QMessageBox.Yes:
                    self.move_mode = False
                    self.show_chat_message("Move mode OFF", duration_ms=2000)
                    self.unsetCursor()
                else:
                    # Keep move mode active
                    self.setCursor(QtCore.Qt.OpenHandCursor)
            event.accept()

    def _wander_step(self):
        if self.dragging or not self.isVisible() or self.move_mode or self.menu_visible:
            return
        geom = QtWidgets.QApplication.primaryScreen().availableGeometry()
        x, y = self.x(), self.y()

        # More frequent and visible randomization
        if random.random() < 0.6:
            ang = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.7, 1.5) * MOVE_STEP
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
