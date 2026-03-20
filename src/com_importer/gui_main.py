"""
GUI entry point for the City of Mist Foundry Importer application.

This module provides the main application launcher for the PyQt6-based GUI.
"""

import sys

from PyQt6.QtWidgets import QApplication

from .gui.main_window import ComImporterWindow


def main(argv: list[str] | None = None) -> int:
    """
    Launch the GUI application.

    Args:
        argv: Command line arguments (for testing)

    Returns:
        Application exit code
    """
    app = QApplication(argv or sys.argv)

    # Set application metadata
    app.setApplicationName("CoM Importer")
    app.setApplicationVersion("0.1.0")

    # Create and show main window
    window = ComImporterWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
