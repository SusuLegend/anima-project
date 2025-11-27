"""
Settings Manager UI for AI Virtual Assistant Widget

This module provides a comprehensive settings interface where users can:
- Configure LLM model settings (Ollama model, system prompt)
- Select character assets (GIF files)
- Adjust UI behavior (opacity, movement speed, wander interval)
- Configure RAG pipeline settings (Pinecone)
- Set up email notifications
- Save/load settings to/from JSON
- Launch the application with configured settings

Requirements:
- PySide6
- All dependencies from the main application
"""

import sys
import json
import os
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QFileDialog, QTabWidget, QGroupBox, QCheckBox, QMessageBox, QDialog
)

# Default configuration
DEFAULT_CONFIG = {
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

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"


class SettingsManager(QMainWindow):
    """Main settings window for configuring the AI assistant"""
    
    def __init__(self):
        super().__init__()
        self.config = self.load_config()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("AI Virtual Assistant - Settings Manager")
        self.setMinimumSize(800, 600)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Title
        title = QLabel("⚙️ Settings Manager")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Tab widget for different setting categories
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_llm_tab(), "🤖 LLM Model")
        self.tabs.addTab(self.create_ui_tab(), "🎨 Character & UI")
        self.tabs.addTab(self.create_rag_tab(), "📚 RAG Pipeline")
        self.tabs.addTab(self.create_notifications_tab(), "📧 Notifications")
        main_layout.addWidget(self.tabs)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Save Settings")
        self.save_btn.setStyleSheet("padding: 10px; font-size: 14px;")
        self.save_btn.clicked.connect(self.save_settings)
        
        self.load_btn = QPushButton("📂 Load Settings")
        self.load_btn.setStyleSheet("padding: 10px; font-size: 14px;")
        self.load_btn.clicked.connect(self.load_settings_dialog)
        
        self.reset_btn = QPushButton("🔄 Reset to Defaults")
        self.reset_btn.setStyleSheet("padding: 10px; font-size: 14px;")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        
        self.start_btn = QPushButton("▶️ START APPLICATION")
        self.start_btn.setStyleSheet("""
            padding: 15px;
            font-size: 16px;
            font-weight: bold;
            background-color: #4CAF50;
            color: white;
            border-radius: 8px;
        """)
        self.start_btn.clicked.connect(self.start_application)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.load_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.start_btn)
        
        main_layout.addLayout(button_layout)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
    def create_llm_tab(self):
        """Create LLM model settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Model selection
        model_group = QGroupBox("Ollama Model Configuration")
        model_layout = QVBoxLayout()
        
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model Name:"))
        self.model_input = QLineEdit(self.config["llm"]["model"])
        self.model_input.setPlaceholderText("e.g., llama3.2:latest, mistral:latest")
        model_row.addWidget(self.model_input)
        model_layout.addLayout(model_row)
        
        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("Timeout (seconds):"))
        self.timeout_input = QDoubleSpinBox()
        self.timeout_input.setRange(5.0, 300.0)
        self.timeout_input.setValue(self.config["llm"]["timeout"])
        self.timeout_input.setSingleStep(5.0)
        timeout_row.addWidget(self.timeout_input)
        timeout_row.addStretch()
        model_layout.addLayout(timeout_row)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # System prompt
        prompt_group = QGroupBox("System Prompt (Character Personality)")
        prompt_layout = QVBoxLayout()
        
        prompt_layout.addWidget(QLabel("Define how the AI assistant should behave:"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlainText(self.config["llm"]["system_prompt"])
        self.prompt_input.setMinimumHeight(200)
        prompt_layout.addWidget(self.prompt_input)
        
        # Preset buttons
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Presets:"))
        
        chika_btn = QPushButton("Chika Fujiwara")
        chika_btn.clicked.connect(lambda: self.prompt_input.setPlainText(
            "You are Chika Fujiwara from the anime 'Kaguya-sama: Love is War'. "
            "Always answer in a cute, bubbly, and playful manner, as if you are Chika. "
            "If asked about yourself, respond as Chika would."
        ))
        preset_layout.addWidget(chika_btn)
        
        assistant_btn = QPushButton("Professional Assistant")
        assistant_btn.clicked.connect(lambda: self.prompt_input.setPlainText(
            "You are a helpful, professional AI assistant. "
            "Provide clear, concise, and accurate responses to user queries."
        ))
        preset_layout.addWidget(assistant_btn)
        
        friendly_btn = QPushButton("Friendly Companion")
        friendly_btn.clicked.connect(lambda: self.prompt_input.setPlainText(
            "You are a friendly and supportive AI companion. "
            "Be warm, empathetic, and engaging in your responses."
        ))
        preset_layout.addWidget(friendly_btn)
        
        preset_layout.addStretch()
        prompt_layout.addLayout(preset_layout)
        
        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)
        
        layout.addStretch()
        return tab
        
    def create_ui_tab(self):
        """Create UI and character settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Character asset
        asset_group = QGroupBox("Character Asset")
        asset_layout = QVBoxLayout()
        
        asset_row = QHBoxLayout()
        asset_row.addWidget(QLabel("Character GIF:"))
        self.asset_input = QLineEdit(self.config["ui"]["character_gif"])
        asset_row.addWidget(self.asset_input)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_character_gif)
        asset_row.addWidget(browse_btn)
        asset_layout.addLayout(asset_row)
        
        # Preview button
        preview_btn = QPushButton("👁️ Preview Asset")
        preview_btn.clicked.connect(self.preview_asset)
        asset_layout.addWidget(preview_btn)
        
        asset_group.setLayout(asset_layout)
        layout.addWidget(asset_group)
        
        # Window settings
        window_group = QGroupBox("Window Settings")
        window_layout = QVBoxLayout()
        
        # Opacity
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Window Opacity:"))
        self.opacity_input = QDoubleSpinBox()
        self.opacity_input.setRange(0.1, 1.0)
        self.opacity_input.setValue(self.config["ui"]["window_opacity"])
        self.opacity_input.setSingleStep(0.05)
        opacity_row.addWidget(self.opacity_input)
        opacity_row.addStretch()
        window_layout.addLayout(opacity_row)
        
        # Window size
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Window Size:"))
        self.width_input = QSpinBox()
        self.width_input.setRange(100, 500)
        self.width_input.setValue(self.config["ui"]["window_size"][0])
        size_row.addWidget(self.width_input)
        size_row.addWidget(QLabel("x"))
        self.height_input = QSpinBox()
        self.height_input.setRange(100, 500)
        self.height_input.setValue(self.config["ui"]["window_size"][1])
        size_row.addWidget(self.height_input)
        size_row.addStretch()
        window_layout.addLayout(size_row)
        
        window_group.setLayout(window_layout)
        layout.addWidget(window_group)
        
        # Movement settings
        movement_group = QGroupBox("Movement Behavior")
        movement_layout = QVBoxLayout()
        
        step_row = QHBoxLayout()
        step_row.addWidget(QLabel("Move Step (pixels):"))
        self.step_input = QSpinBox()
        self.step_input.setRange(1, 50)
        self.step_input.setValue(self.config["ui"]["move_step"])
        step_row.addWidget(self.step_input)
        step_row.addStretch()
        movement_layout.addLayout(step_row)
        
        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("Wander Interval (ms):"))
        self.interval_input = QSpinBox()
        self.interval_input.setRange(100, 5000)
        self.interval_input.setValue(self.config["ui"]["wander_interval_ms"])
        self.interval_input.setSingleStep(100)
        interval_row.addWidget(self.interval_input)
        interval_row.addStretch()
        movement_layout.addLayout(interval_row)
        
        movement_group.setLayout(movement_layout)
        layout.addWidget(movement_group)
        
        layout.addStretch()
        return tab
        
    def create_rag_tab(self):
        """Create RAG pipeline settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Enable RAG
        self.rag_enabled = QCheckBox("Enable RAG (Retrieval Augmented Generation)")
        self.rag_enabled.setChecked(self.config["rag"]["enabled"])
        self.rag_enabled.stateChanged.connect(self.toggle_rag_settings)
        layout.addWidget(self.rag_enabled)
        
        # RAG settings group
        self.rag_group = QGroupBox("Pinecone Configuration")
        rag_layout = QVBoxLayout()
        
        api_key_row = QHBoxLayout()
        api_key_row.addWidget(QLabel("Pinecone API Key:"))
        self.pinecone_key_input = QLineEdit(self.config["rag"]["pinecone_api_key"])
        self.pinecone_key_input.setEchoMode(QLineEdit.Password)
        api_key_row.addWidget(self.pinecone_key_input)
        show_key_btn = QPushButton("👁️")
        show_key_btn.setMaximumWidth(40)
        show_key_btn.clicked.connect(lambda: self.pinecone_key_input.setEchoMode(
            QLineEdit.Normal if self.pinecone_key_input.echoMode() == QLineEdit.Password else QLineEdit.Password
        ))
        api_key_row.addWidget(show_key_btn)
        rag_layout.addLayout(api_key_row)
        
        index_row = QHBoxLayout()
        index_row.addWidget(QLabel("Index Name:"))
        self.index_name_input = QLineEdit(self.config["rag"]["index_name"])
        index_row.addWidget(self.index_name_input)
        rag_layout.addLayout(index_row)
        
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Embedding Model:"))
        self.embedding_model_input = QComboBox()
        self.embedding_model_input.addItems([
            "all-MiniLM-L6-v2",
            "all-mpnet-base-v2",
            "paraphrase-MiniLM-L6-v2"
        ])
        self.embedding_model_input.setCurrentText(self.config["rag"]["embedding_model"])
        model_row.addWidget(self.embedding_model_input)
        model_row.addStretch()
        rag_layout.addLayout(model_row)
        
        cloud_row = QHBoxLayout()
        cloud_row.addWidget(QLabel("Cloud Provider:"))
        self.cloud_input = QComboBox()
        self.cloud_input.addItems(["aws", "gcp", "azure"])
        self.cloud_input.setCurrentText(self.config["rag"]["cloud"])
        cloud_row.addWidget(self.cloud_input)
        
        cloud_row.addWidget(QLabel("Region:"))
        self.region_input = QLineEdit(self.config["rag"]["region"])
        cloud_row.addWidget(self.region_input)
        rag_layout.addLayout(cloud_row)
        
        self.rag_group.setLayout(rag_layout)
        self.rag_group.setEnabled(self.config["rag"]["enabled"])
        layout.addWidget(self.rag_group)
        
        # Info label
        info = QLabel(
            "ℹ️ RAG allows the assistant to retrieve relevant information from documents.\n"
            "You'll need a Pinecone account and API key to use this feature."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info)
        
        layout.addStretch()
        return tab
        
    def create_notifications_tab(self):
        """Create notifications settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Enable email notifications
        self.email_enabled = QCheckBox("Enable Email Notifications (Gmail)")
        self.email_enabled.setChecked(self.config["notifications"]["email_enabled"])
        self.email_enabled.stateChanged.connect(self.toggle_email_settings)
        layout.addWidget(self.email_enabled)
        
        # Email settings group
        self.email_group = QGroupBox("Gmail Configuration")
        email_layout = QVBoxLayout()
        
        credential_row = QHBoxLayout()
        credential_row.addWidget(QLabel("Credentials File:"))
        self.email_credential_input = QLineEdit(self.config["notifications"]["email_credential_path"])
        credential_row.addWidget(self.email_credential_input)
        
        browse_cred_btn = QPushButton("Browse...")
        browse_cred_btn.clicked.connect(self.browse_email_credential)
        credential_row.addWidget(browse_cred_btn)
        email_layout.addLayout(credential_row)
        
        poll_row = QHBoxLayout()
        poll_row.addWidget(QLabel("Poll Interval (seconds):"))
        self.poll_interval_input = QSpinBox()
        self.poll_interval_input.setRange(5, 300)
        self.poll_interval_input.setValue(self.config["notifications"]["poll_interval"])
        poll_row.addWidget(self.poll_interval_input)
        poll_row.addStretch()
        email_layout.addLayout(poll_row)
        
        self.email_group.setLayout(email_layout)
        self.email_group.setEnabled(self.config["notifications"]["email_enabled"])
        layout.addWidget(self.email_group)
        
        # Setup instructions
        instructions = QLabel(
            "📝 Setup Instructions:\n"
            "1. Create a Google Cloud project\n"
            "2. Enable Gmail API\n"
            "3. Download OAuth 2.0 credentials as JSON\n"
            "4. Select the credentials file above\n"
            "5. First run will open browser for authentication"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(instructions)
        
        layout.addStretch()
        return tab
        
    def toggle_rag_settings(self, state):
        """Enable/disable RAG settings based on checkbox"""
        self.rag_group.setEnabled(state == Qt.Checked)
        
    def toggle_email_settings(self, state):
        """Enable/disable email settings based on checkbox"""
        self.email_group.setEnabled(state == Qt.Checked)
        
    def browse_character_gif(self):
        """Browse for character GIF file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Character GIF",
            str(Path(__file__).parent.parent.parent / "assets"),
            "GIF Files (*.gif);;All Files (*.*)"
        )
        if file_path:
            self.asset_input.setText(file_path)
            
    def browse_email_credential(self):
        """Browse for email credential JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Email Credential File",
            str(Path(__file__).parent.parent / "notifications"),
            "JSON Files (*.json);;All Files (*.*)"
        )
        if file_path:
            self.email_credential_input.setText(file_path)
            
    def preview_asset(self):
        """Preview the selected character asset"""
        asset_path = Path(self.asset_input.text())
        if not asset_path.exists():
            QMessageBox.warning(self, "File Not Found", f"Asset file not found:\n{asset_path}")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Asset Preview")
        layout = QVBoxLayout(dialog)
        
        label = QLabel()
        movie = QtGui.QMovie(str(asset_path))
        if movie.isValid():
            movie.setScaledSize(QtCore.QSize(300, 300))
            label.setMovie(movie)
            movie.start()
            layout.addWidget(label)
            dialog.exec()
        else:
            QMessageBox.warning(self, "Invalid File", "Could not load the asset file.")
            
    def collect_config(self):
        """Collect configuration from UI inputs"""
        return {
            "llm": {
                "model": self.model_input.text(),
                "system_prompt": self.prompt_input.toPlainText(),
                "timeout": self.timeout_input.value()
            },
            "ui": {
                "character_gif": self.asset_input.text(),
                "window_opacity": self.opacity_input.value(),
                "window_size": [self.width_input.value(), self.height_input.value()],
                "move_step": self.step_input.value(),
                "wander_interval_ms": self.interval_input.value()
            },
            "rag": {
                "enabled": self.rag_enabled.isChecked(),
                "pinecone_api_key": self.pinecone_key_input.text(),
                "index_name": self.index_name_input.text(),
                "embedding_model": self.embedding_model_input.currentText(),
                "cloud": self.cloud_input.currentText(),
                "region": self.region_input.text()
            },
            "notifications": {
                "email_enabled": self.email_enabled.isChecked(),
                "email_credential_path": self.email_credential_input.text(),
                "poll_interval": self.poll_interval_input.value()
            }
        }
        
    def save_settings(self):
        """Save current settings to file"""
        self.config = self.collect_config()
        try:
            with open(CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.statusBar().showMessage("✅ Settings saved successfully!", 3000)
            QMessageBox.information(self, "Success", "Settings saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{e}")
            
    def load_config(self):
        """Load configuration from file or use defaults"""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()
        
    def load_settings_dialog(self):
        """Load settings from a selected file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Settings File",
            str(Path(__file__).parent.parent.parent),
            "JSON Files (*.json);;All Files (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    self.config = json.load(f)
                self.refresh_ui()
                self.statusBar().showMessage("✅ Settings loaded successfully!", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load settings:\n{e}")
                
    def refresh_ui(self):
        """Refresh UI with current config values"""
        # LLM tab
        self.model_input.setText(self.config["llm"]["model"])
        self.prompt_input.setPlainText(self.config["llm"]["system_prompt"])
        self.timeout_input.setValue(self.config["llm"]["timeout"])
        
        # UI tab
        self.asset_input.setText(self.config["ui"]["character_gif"])
        self.opacity_input.setValue(self.config["ui"]["window_opacity"])
        self.width_input.setValue(self.config["ui"]["window_size"][0])
        self.height_input.setValue(self.config["ui"]["window_size"][1])
        self.step_input.setValue(self.config["ui"]["move_step"])
        self.interval_input.setValue(self.config["ui"]["wander_interval_ms"])
        
        # RAG tab
        self.rag_enabled.setChecked(self.config["rag"]["enabled"])
        self.pinecone_key_input.setText(self.config["rag"]["pinecone_api_key"])
        self.index_name_input.setText(self.config["rag"]["index_name"])
        self.embedding_model_input.setCurrentText(self.config["rag"]["embedding_model"])
        self.cloud_input.setCurrentText(self.config["rag"]["cloud"])
        self.region_input.setText(self.config["rag"]["region"])
        
        # Notifications tab
        self.email_enabled.setChecked(self.config["notifications"]["email_enabled"])
        self.email_credential_input.setText(self.config["notifications"]["email_credential_path"])
        self.poll_interval_input.setValue(self.config["notifications"]["poll_interval"])
        
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.config = DEFAULT_CONFIG.copy()
            self.refresh_ui()
            self.statusBar().showMessage("🔄 Settings reset to defaults", 3000)
            
    def start_application(self):
        """Save settings and start the main application"""
        # Validate settings
        asset_path = Path(self.asset_input.text())
        if not asset_path.exists():
            QMessageBox.warning(
                self,
                "Missing Asset",
                f"Character GIF not found:\n{asset_path}\n\nPlease select a valid file."
            )
            return
            
        if self.rag_enabled.isChecked() and not self.pinecone_key_input.text():
            QMessageBox.warning(
                self,
                "Missing API Key",
                "RAG is enabled but Pinecone API key is not set.\n\nPlease provide an API key or disable RAG."
            )
            return
            
        if self.email_enabled.isChecked():
            email_cred_path = Path(self.email_credential_input.text())
            if not email_cred_path.exists():
                QMessageBox.warning(
                    self,
                    "Missing Credentials",
                    f"Email credential file not found:\n{email_cred_path}\n\nPlease select a valid file or disable email notifications."
                )
                return
        
        # Save settings
        self.save_settings()
        
        # Launch application
        try:
            import subprocess
            main_script = Path(__file__).parent / "character_UI.py"
            subprocess.Popen([sys.executable, str(main_script)])
            
            self.statusBar().showMessage("✅ Application launched!", 2000)
            QMessageBox.information(
                self,
                "Application Started",
                "The AI Virtual Assistant has been launched with your settings!"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Launch Error",
                f"Failed to start application:\n{e}"
            )


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application-wide style
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #ddd;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QPushButton {
            background-color: #e0e0e0;
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        QPushButton:pressed {
            background-color: #c0c0c0;
        }
    """)
    
    window = SettingsManager()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()