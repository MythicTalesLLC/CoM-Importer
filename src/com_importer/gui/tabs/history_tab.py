"""History and preview tab for viewing recently created actors."""

from __future__ import annotations

import json
import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...history_manager import HistoryManager

logger = logging.getLogger(__name__)


class HistoryTab(QWidget):
    """Tab for viewing and managing import history."""

    def __init__(self):
        """Initialize the history tab."""
        super().__init__()
        self.history_manager = HistoryManager()
        self.current_entry = None
        self._create_ui()
        self.refresh_history()

    def _create_ui(self) -> None:
        """Create the user interface."""
        layout = QVBoxLayout(self)

        # Statistics
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("Loading statistics...")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # History table
        layout.addWidget(QLabel("Recently Imported Actors:"))

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(
            ["Name", "Rating", "Source", "Created", "Status"]
        )
        self.history_table.setColumnWidth(0, 200)
        self.history_table.setColumnWidth(1, 80)
        self.history_table.setColumnWidth(2, 100)
        self.history_table.setColumnWidth(3, 150)
        self.history_table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.history_table)

        # JSON preview
        layout.addWidget(QLabel("JSON Preview:"))
        self.preview_text = QPlainTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(200)
        layout.addWidget(self.preview_text)

        # Action buttons
        button_layout = QHBoxLayout()

        refresh_button = QPushButton("Refresh History")
        refresh_button.clicked.connect(self.refresh_history)
        button_layout.addWidget(refresh_button)

        export_csv_button = QPushButton("Export as CSV")
        export_csv_button.clicked.connect(self._export_csv)
        button_layout.addWidget(export_csv_button)

        export_json_button = QPushButton("Export as JSON")
        export_json_button.clicked.connect(self._export_json)
        button_layout.addWidget(export_json_button)

        clear_button = QPushButton("Clear History")
        clear_button.clicked.connect(self._clear_history)
        button_layout.addStretch()
        button_layout.addWidget(clear_button)

        layout.addLayout(button_layout)

    def refresh_history(self) -> None:
        """Refresh and display history from database."""
        self.history_table.setRowCount(0)
        entries = self.history_manager.get_recent(limit=100)

        for row, entry in enumerate(entries):
            self.history_table.insertRow(row)

            # Name
            name_item = QTableWidgetItem(entry.danger_name)
            name_item.setData(Qt.ItemDataRole.UserRole, entry.actor_id)
            self.history_table.setItem(row, 0, name_item)

            # Rating
            rating = entry.danger_rating or "-"
            self.history_table.setItem(row, 1, QTableWidgetItem(rating))

            # Source
            self.history_table.setItem(row, 2, QTableWidgetItem(entry.source))

            # Created
            created_str = entry.created_at.strftime("%Y-%m-%d %H:%M")
            self.history_table.setItem(row, 3, QTableWidgetItem(created_str))

            # Status
            status_item = QTableWidgetItem(entry.status)
            if entry.status == "success":
                status_item.setBackground(Qt.GlobalColor.green)
            else:
                status_item.setBackground(Qt.GlobalColor.red)
            self.history_table.setItem(row, 4, status_item)

        # Update statistics
        self._update_statistics()

    def _update_statistics(self) -> None:
        """Update and display statistics."""
        stats = self.history_manager.get_statistics()

        stats_text = (
            f"Total: {stats['total']} | Success: {stats['success']} | " f"Failed: {stats['failed']}"
        )

        if stats["by_source"]:
            sources = ", ".join(
                f"{src}: {count}" for src, count in sorted(stats["by_source"].items())
            )
            stats_text += f" | Sources: {sources}"

        self.stats_label.setText(stats_text)

    def _on_selection_changed(self) -> None:
        """Handle table selection change."""
        selected_rows = self.history_table.selectedIndexes()
        if not selected_rows:
            self.preview_text.clear()
            self.current_entry = None
            return

        row = selected_rows[0].row()
        name_item = self.history_table.item(row, 0)
        if not name_item:
            return

        actor_id = name_item.data(Qt.ItemDataRole.UserRole)
        self.current_entry = self.history_manager.get_entry(actor_id)

        if self.current_entry:
            # Display JSON preview
            preview_json = json.dumps(self.current_entry.actor_json, indent=2)
            self.preview_text.setPlainText(preview_json)

    def _export_csv(self) -> None:
        """Export history to CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export History as CSV",
            "",
            "CSV Files (*.csv)",
        )

        if not file_path:
            return

        try:
            self.history_manager.export_csv(file_path)
            QMessageBox.information(
                self,
                "Export Successful",
                f"History exported to:\n{file_path}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Error exporting history:\n{str(e)}")

    def _export_json(self) -> None:
        """Export history to JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export History as JSON",
            "",
            "JSON Files (*.json)",
        )

        if not file_path:
            return

        try:
            self.history_manager.export_json(file_path)
            QMessageBox.information(
                self,
                "Export Successful",
                f"History exported to:\n{file_path}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Error exporting history:\n{str(e)}")

    def _clear_history(self) -> None:
        """Clear all history."""
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to delete all history?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            count = self.history_manager.clear_all()
            QMessageBox.information(self, "History Cleared", f"Deleted {count} entries.")
            self.refresh_history()

    def add_entry_from_creation(
        self, actor_id: str, danger_name: str, actor_json: dict, **kwargs
    ) -> None:
        """Add a new entry when danger is created."""
        from ...history_manager import HistoryEntry

        entry = HistoryEntry(
            actor_id=actor_id,
            danger_name=danger_name,
            actor_json=actor_json,
            **kwargs,
        )
        self.history_manager.add_entry(entry)
        self.refresh_history()
