"""
Settings Manager UI for AI Virtual Assistant Widget

This module provides a comprehensive settings interface where users can:
- Configure LLM model settings (Ollama model, system prompt)
- Select character assets (GIF files)
- Adjust UI behavior (opacity, movement speed, wander interval)
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