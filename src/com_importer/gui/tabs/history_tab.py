"""History and preview tab for viewing recently created actors."""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class HistoryTab(QWidget):
    """Tab for viewing and managing import history."""

    def __init__(self):
        """Initialize the history tab."""
        super().__init__()
        self._create_ui()

    def _create_ui(self) -> None:
        """Create the user interface."""
        layout = QVBoxLayout(self)

        # History table
        layout.addWidget(QLabel("Recently Imported Actors:"))

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Name", "Type", "Date", "Status"])
        self.history_table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.history_table)

        # JSON preview
        layout.addWidget(QLabel("JSON Preview:"))
        self.preview_text = QPlainTextEdit()
        self.preview_text.setReadOnly(True)
        layout.addWidget(self.preview_text)

        # Action buttons
        button_layout = QHBoxLayout()

        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(self._edit_selected)
        button_layout.addWidget(edit_button)

        delete_button = QPushButton("Delete from Foundry")
        delete_button.clicked.connect(self._delete_selected)
        button_layout.addWidget(delete_button)

        export_button = QPushButton("Export as JSON")
        export_button.clicked.connect(self._export_selected)
        button_layout.addWidget(export_button)

        refresh_button = QPushButton("Refresh from Foundry")
        refresh_button.clicked.connect(self._refresh_history)
        button_layout.addWidget(refresh_button)

        layout.addLayout(button_layout)

    def _on_selection_changed(self) -> None:
        """Handle table selection change."""
        selected = self.history_table.selectedItems()
        if selected:
            # TODO: Load and display JSON preview
            pass

    def _edit_selected(self) -> None:
        """Edit selected actor."""
        QMessageBox.information(self, "Edit", "Edit feature coming soon...")

    def _delete_selected(self) -> None:
        """Delete selected actor from Foundry."""
        QMessageBox.information(self, "Delete", "Delete feature coming soon...")

    def _export_selected(self) -> None:
        """Export selected actor as JSON."""
        QMessageBox.information(self, "Export", "Export feature coming soon...")

    def _refresh_history(self) -> None:
        """Refresh history from Foundry."""
        QMessageBox.information(self, "Refresh", "Refresh feature coming soon...")
