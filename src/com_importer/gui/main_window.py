"""
Main application window for the CoM Importer GUI.

Provides the main QMainWindow with tabbed interface for:
- Single danger/character input
- Batch import
- Configuration
- History and preview
"""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class ComImporterWindow(QMainWindow):
    """Main application window with tabbed interface."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("City of Mist Foundry Importer")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create tabs
        self._create_tabs()

        # Create menu bar
        self._create_menu_bar()

        # Load saved settings
        self._load_settings()

    def _create_tabs(self) -> None:
        """Create the tab interface."""
        from .tabs.batch_import_tab import BatchImportTab
        from .tabs.config_tab import ConfigurationTab
        from .tabs.history_tab import HistoryTab
        from .tabs.single_import_tab import SingleImportTab

        # Tab 1: Single Danger/Character Input
        self.single_import_tab = SingleImportTab()
        self.tabs.addTab(self.single_import_tab, "Single Import")

        # Tab 2: Batch Import
        self.batch_import_tab = BatchImportTab()
        self.tabs.addTab(self.batch_import_tab, "Batch Import")

        # Tab 3: Configuration
        self.config_tab = ConfigurationTab()
        self.tabs.addTab(self.config_tab, "Configuration")

        # Tab 4: History & Preview
        self.history_tab = HistoryTab()
        self.tabs.addTab(self.history_tab, "History")

    def _create_menu_bar(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.close)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        preferences_action = edit_menu.addAction("&Preferences")
        preferences_action.triggered.connect(self._show_preferences)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        about_action = help_menu.addAction("&About")
        about_action.triggered.connect(self._show_about)

    def _load_settings(self) -> None:
        """Load application settings from configuration."""
        # This will load user's saved Foundry connection, OCR settings, etc.
        # For now, just a placeholder
        logger.info("Loading application settings...")

    def _show_preferences(self) -> None:
        """Show preferences dialog."""
        # TODO: Implement preferences dialog
        logger.info("Show preferences")

    def _show_about(self) -> None:
        """Show about dialog."""
        # TODO: Implement about dialog
        logger.info("Show about")

    def closeEvent(self, event):
        """Handle application close."""
        # TODO: Save any unsaved data
        logger.info("Closing application...")
        event.accept()
