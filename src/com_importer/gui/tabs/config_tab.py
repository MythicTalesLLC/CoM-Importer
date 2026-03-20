"""Configuration and settings tab for Foundry connection and OCR."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...foundry_client import FoundryClientFactory

logger = logging.getLogger(__name__)


class ConfigurationTab(QWidget):
    """Tab for configuring Foundry connection and OCR settings."""

    settings_changed = pyqtSignal()
    client_created = pyqtSignal(object)  # Emits the Foundry client

    def __init__(self):
        """Initialize the configuration tab."""
        super().__init__()
        self.config_file = Path.home() / ".com_importer" / "config.json"
        self.config = self._load_config()
        self._create_ui()

    def _create_ui(self) -> None:
        """Create the user interface."""
        layout = QVBoxLayout(self)

        # Foundry Connection Section
        foundry_group = self._create_foundry_section()
        layout.addWidget(foundry_group)

        # OCR Settings Section
        ocr_group = self._create_ocr_section()
        layout.addWidget(ocr_group)

        # Import Preferences Section
        prefs_group = self._create_preferences_section()
        layout.addWidget(prefs_group)

        # Buttons
        button_layout = QHBoxLayout()
        test_button = QPushButton("Test Connection")
        test_button.clicked.connect(self._test_connection)
        button_layout.addWidget(test_button)

        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self._reset_defaults)
        button_layout.addWidget(reset_button)

        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self._save_config)
        button_layout.addWidget(save_button)

        layout.addStretch()
        layout.addLayout(button_layout)

    def _create_foundry_section(self) -> QGroupBox:
        """Create Foundry connection settings section."""
        group = QGroupBox("Foundry Connection")
        layout = QVBoxLayout()

        # Connection mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Connection Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Remote API", "Local Filesystem"])
        self.mode_combo.setCurrentText(self.config.get("connection_mode", "Remote API"))
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Remote API settings
        self.remote_group = QGroupBox("Remote API Settings")
        remote_layout = QFormLayout()

        self.api_url_input = QLineEdit()
        self.api_url_input.setText(
            self.config.get("api_url", "https://foundryvtt-rest-api-relay.fly.dev")
        )
        remote_layout.addRow("API URL:", self.api_url_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setText(self.config.get("api_key", ""))
        remote_layout.addRow("API Key:", self.api_key_input)

        self.client_id_input = QLineEdit()
        self.client_id_input.setText(self.config.get("client_id", ""))
        remote_layout.addRow("Client ID:", self.client_id_input)

        self.world_name_input = QLineEdit()
        self.world_name_input.setText(self.config.get("world_name", "city-of-mist"))
        remote_layout.addRow("World Name:", self.world_name_input)

        self.remote_group.setLayout(remote_layout)
        layout.addWidget(self.remote_group)

        # Local filesystem settings
        self.local_group = QGroupBox("Local Filesystem Settings")
        local_layout = QFormLayout()

        local_button_layout = QHBoxLayout()
        self.foundry_dir_input = QLineEdit()
        self.foundry_dir_input.setText(self.config.get("foundry_data_dir", ""))
        local_button_layout.addWidget(self.foundry_dir_input)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_foundry_dir)
        local_button_layout.addWidget(browse_button)
        local_layout.addRow("Foundry Data Dir:", local_button_layout)

        self.local_world_input = QLineEdit()
        self.local_world_input.setText(self.config.get("local_world_name", "city-of-mist"))
        local_layout.addRow("World Name:", self.local_world_input)

        self.local_group.setLayout(local_layout)
        layout.addWidget(self.local_group)

        # Update visibility based on mode
        self._on_mode_changed(self.mode_combo.currentText())

        group.setLayout(layout)
        return group

    def _create_ocr_section(self) -> QGroupBox:
        """Create OCR settings section."""
        group = QGroupBox("OCR Settings")
        layout = QFormLayout()

        self.ocr_method_combo = QComboBox()
        self.ocr_method_combo.addItems(
            ["Auto (Tesseract first)", "Tesseract (Local)", "Cloud Vision", "Disabled"]
        )
        self.ocr_method_combo.setCurrentText(
            self.config.get("ocr_method", "Auto (Tesseract first)")
        )
        layout.addRow("OCR Method:", self.ocr_method_combo)

        self.tesseract_path_input = QLineEdit()
        self.tesseract_path_input.setText(self.config.get("tesseract_path", ""))
        self.tesseract_path_input.setPlaceholderText("(Auto-detect if empty)")
        layout.addRow("Tesseract Path:", self.tesseract_path_input)

        self.vision_key_input = QLineEdit()
        self.vision_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.vision_key_input.setText(self.config.get("vision_api_key", ""))
        layout.addRow("Cloud Vision API Key:", self.vision_key_input)

        group.setLayout(layout)
        return group

    def _create_preferences_section(self) -> QGroupBox:
        """Create import preferences section."""
        group = QGroupBox("Import Preferences")
        layout = QVBoxLayout()

        self.auto_lock_check = QCheckBox("Auto-lock dangers after creation")
        self.auto_lock_check.setChecked(self.config.get("auto_lock", False))
        layout.addWidget(self.auto_lock_check)

        self.finalize_check = QCheckBox("Mark as finalized after creation")
        self.finalize_check.setChecked(self.config.get("finalize", False))
        layout.addWidget(self.finalize_check)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _on_mode_changed(self, mode: str) -> None:
        """Handle connection mode change."""
        is_remote = mode == "Remote API"
        self.remote_group.setVisible(is_remote)
        self.local_group.setVisible(not is_remote)

    def _browse_foundry_dir(self) -> None:
        """Browse for Foundry data directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Foundry Data Directory",
            self.foundry_dir_input.text() or str(Path.home()),
        )
        if dir_path:
            self.foundry_dir_input.setText(dir_path)

    def _test_connection(self) -> None:
        """Test the Foundry connection."""
        try:
            if self.mode_combo.currentText() == "Remote API":
                client = FoundryClientFactory.create_rest_client(
                    api_url=self.api_url_input.text(),
                    api_key=self.api_key_input.text(),
                    client_id=self.client_id_input.text(),
                    world_name=self.world_name_input.text(),
                )
            else:
                client = FoundryClientFactory.create_local_client(
                    foundry_data_dir=self.foundry_dir_input.text(),
                    world_name=self.local_world_input.text(),
                )

            success, message = client.test_connection()
            if success:
                QMessageBox.information(self, "Connection Successful", message)
                # Emit the successfully created client
                self.client_created.emit(client)
            else:
                QMessageBox.warning(self, "Connection Failed", message)
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))

    def _reset_defaults(self) -> None:
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config = {}
            # Recreate UI
            for i in reversed(range(self.layout().count())):
                self.layout().itemAt(i).widget().setParent(None)
            self._create_ui()

    def _save_config(self) -> None:
        """Save configuration to file."""
        self.config = {
            "connection_mode": self.mode_combo.currentText(),
            "api_url": self.api_url_input.text(),
            "api_key": self.api_key_input.text(),
            "client_id": self.client_id_input.text(),
            "world_name": self.world_name_input.text(),
            "foundry_data_dir": self.foundry_dir_input.text(),
            "local_world_name": self.local_world_input.text(),
            "ocr_method": self.ocr_method_combo.currentText(),
            "tesseract_path": self.tesseract_path_input.text(),
            "vision_api_key": self.vision_key_input.text(),
            "auto_lock": self.auto_lock_check.isChecked(),
            "finalize": self.finalize_check.isChecked(),
        }

        # Ensure config directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # Write config
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)

        QMessageBox.information(self, "Settings Saved", "Configuration saved successfully")
        self.settings_changed.emit()

    def _load_config(self) -> dict:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to load config: {e}")
        return {}

    def get_config(self) -> dict:
        """Get current configuration."""
        return self.config
