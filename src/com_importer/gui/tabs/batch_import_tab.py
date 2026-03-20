"""Batch import tab for importing multiple dangers/characters at once."""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class BatchImportTab(QWidget):
    """Tab for batch importing multiple actors."""

    def __init__(self):
        """Initialize the batch import tab."""
        super().__init__()
        self._create_ui()

    def _create_ui(self) -> None:
        """Create the user interface."""
        layout = QVBoxLayout(self)

        # File selection
        layout.addWidget(QLabel("Select JSONL or CSV file with dangers/characters:"))

        file_layout = QVBoxLayout()
        select_button = QPushButton("Select File...")
        select_button.clicked.connect(self._select_file)
        file_layout.addWidget(select_button)

        self.file_label = QLabel("No file selected")
        file_layout.addWidget(self.file_label)
        layout.addLayout(file_layout)

        # Results table
        layout.addWidget(QLabel("Import Results:"))
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Name", "Type", "Status", "Notes"])
        layout.addWidget(self.results_table)

        # Action buttons
        button_layout = QVBoxLayout()

        parse_button = QPushButton("Parse All")
        parse_button.clicked.connect(self._parse_all)
        button_layout.addWidget(parse_button)

        import_button = QPushButton("Import All")
        import_button.clicked.connect(self._import_all)
        button_layout.addWidget(import_button)

        export_button = QPushButton("Export Failed")
        export_button.clicked.connect(self._export_failed)
        button_layout.addWidget(export_button)

        layout.addLayout(button_layout)

    def _select_file(self) -> None:
        """Select a file to import."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Import File",
            "",
            "JSONL Files (*.jsonl);;CSV Files (*.csv);;All Files (*)",
        )
        if file_path:
            self.file_label.setText(f"Selected: {file_path}")
            # TODO: Load and preview file

    def _parse_all(self) -> None:
        """Parse all entries in the file."""
        QMessageBox.information(self, "Parse All", "Parse all feature coming soon...")

    def _import_all(self) -> None:
        """Import all entries to Foundry."""
        QMessageBox.information(self, "Import All", "Batch import feature coming soon...")

    def _export_failed(self) -> None:
        """Export failed entries for retry."""
        QMessageBox.information(self, "Export Failed", "Export feature coming soon...")
