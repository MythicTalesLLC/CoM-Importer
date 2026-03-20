"""Batch import tab for importing multiple dangers/characters at once."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...batch_manager import BatchImportManager, BatchImportParser

logger = logging.getLogger(__name__)


class BatchImportWorker(QThread):
    """Worker thread for batch import operations."""

    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(object)  # result report
    error = pyqtSignal(str)

    def __init__(
        self,
        batch_manager: BatchImportManager,
        texts: list[str],
        actor_type: str = "threat",
    ):
        """Initialize worker."""
        super().__init__()
        self.batch_manager = batch_manager
        self.texts = texts
        self.actor_type = actor_type

    def run(self):
        """Run batch import."""
        try:
            report = self.batch_manager.import_from_texts(
                self.texts,
                actor_type=self.actor_type,
                progress_callback=lambda curr, total: self.progress.emit(curr, total),
            )
            self.finished.emit(report)
        except Exception as e:
            self.error.emit(str(e))
            logger.exception("Batch import worker error")


class BatchImportTab(QWidget):
    """Tab for batch importing multiple actors."""

    def __init__(self):
        """Initialize the batch import tab."""
        super().__init__()
        self.foundry_client = None
        self.current_texts: list[str] = []
        self.current_report = None
        self.actor_type = "threat"  # Default to danger
        self._create_ui()

    def _create_ui(self) -> None:
        """Create the user interface."""
        layout = QVBoxLayout(self)

        # Actor type selector
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Import Type:"))
        self.actor_type_combo = QComboBox()
        self.actor_type_combo.addItems(["Danger (Threat)", "Character (Player)"])
        self.actor_type_combo.currentIndexChanged.connect(self._on_actor_type_changed)
        type_layout.addWidget(self.actor_type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        # Input selection
        layout.addWidget(QLabel("Input Method:"))
        input_layout = QHBoxLayout()

        file_button = QPushButton("Load from File...")
        file_button.clicked.connect(self._select_file)
        input_layout.addWidget(file_button)

        paste_button = QPushButton("Paste Text Blocks")
        paste_button.clicked.connect(self._show_paste_dialog)
        input_layout.addWidget(paste_button)

        input_layout.addStretch()
        layout.addLayout(input_layout)

        # File/input info
        self.input_label = QLabel("No input loaded")
        layout.addWidget(self.input_label)

        # Preview
        layout.addWidget(QLabel("Loaded Dangers Preview:"))
        self.preview_text = QPlainTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(100)
        layout.addWidget(self.preview_text)

        # Results table
        layout.addWidget(QLabel("Import Results:"))
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["#", "Name", "Status", "Actor ID", "Error"])
        self.results_table.setColumnWidth(0, 40)
        self.results_table.setColumnWidth(1, 150)
        self.results_table.setColumnWidth(2, 80)
        self.results_table.setColumnWidth(3, 100)
        self.results_table.setColumnWidth(4, 300)
        layout.addWidget(self.results_table)

        # Progress
        layout.addWidget(QLabel("Progress:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        # Action buttons
        button_layout = QHBoxLayout()

        self.import_button = QPushButton("Import All")
        self.import_button.clicked.connect(self._import_all)
        self.import_button.setEnabled(False)
        button_layout.addWidget(self.import_button)

        export_failed_button = QPushButton("Export Failed")
        export_failed_button.clicked.connect(self._export_failed)
        button_layout.addWidget(export_failed_button)

        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(self._clear_all)
        button_layout.addWidget(clear_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _on_actor_type_changed(self) -> None:
        """Handle actor type selection change."""
        if self.actor_type_combo.currentIndex() == 0:
            self.actor_type = "threat"
        else:
            self.actor_type = "character"
        logger.debug(f"Actor type changed to: {self.actor_type}")

    def _select_file(self) -> None:
        """Select a file to import."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Import File",
            "",
            "All Files (*);;JSONL Files (*.jsonl);;CSV Files (*.csv)",
        )
        if not file_path:
            return

        try:
            file_path = Path(file_path)

            # Parse based on file extension
            if file_path.suffix.lower() == ".jsonl":
                texts = BatchImportParser.parse_jsonl(str(file_path))
            elif file_path.suffix.lower() == ".csv":
                texts = BatchImportParser.parse_csv(str(file_path))
            else:
                # Try to detect format
                with open(file_path) as f:
                    content = f.read()
                    if content.strip().startswith("{"):
                        texts = BatchImportParser.parse_jsonl(str(file_path))
                    elif "," in content:
                        texts = BatchImportParser.parse_csv(str(file_path))
                    else:
                        # Treat as text blocks
                        texts = BatchImportParser.parse_text_blocks(content)

            self._load_texts(texts, f"Loaded from: {file_path.name}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading File",
                f"Failed to load file:\n{str(e)}",
            )
            logger.exception("Error loading file")

    def _show_paste_dialog(self) -> None:
        """Show dialog to paste text blocks."""
        dialog = QWidget()
        dialog.setWindowTitle("Paste Danger Text")
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Paste danger text blocks (separated by ---):"))
        text_edit = QPlainTextEdit()
        text_edit.setPlaceholderText(
            "Paste multiple dangers separated by\\n---\\n\\nExample:\\n"
            "Danger 1 text...\\n---\\n Danger 2 text..."
        )
        layout.addWidget(text_edit)

        button_layout = QHBoxLayout()
        load_button = QPushButton("Load")

        def load_pasted():
            content = text_edit.toPlainText()
            if not content.strip():
                QMessageBox.warning(dialog, "No Input", "Please paste some text.")
                return

            texts = BatchImportParser.parse_text_blocks(content)
            if texts:
                self._load_texts(texts, f"Pasted {len(texts)} danger blocks")
                dialog.close()
            else:
                QMessageBox.warning(dialog, "No Input", "Could not parse any danger blocks.")

        load_button.clicked.connect(load_pasted)
        button_layout.addWidget(load_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        dialog.resize(600, 400)
        dialog.show()

    def _load_texts(self, texts: list[str], source: str) -> None:
        """Load danger texts for import."""
        self.current_texts = texts
        self.current_report = None

        # Update UI
        self.input_label.setText(f"{source} - {len(texts)} danger(s) loaded")

        # Show preview
        preview = "\n---\n".join(
            text[:100] + "..." if len(text) > 100 else text for text in texts[:5]
        )
        if len(texts) > 5:
            preview += f"\n... and {len(texts) - 5} more"

        self.preview_text.setPlainText(preview)

        # Enable import
        self.import_button.setEnabled(True)
        self.status_label.setText(f"Ready to import {len(texts)} dangers")

    def _import_all(self) -> None:
        """Import all loaded dangers to Foundry."""
        if not self.current_texts:
            QMessageBox.warning(self, "No Input", "Load dangers first.")
            return

        if not self.foundry_client:
            QMessageBox.warning(
                self,
                "Not Configured",
                "Configure Foundry connection first.",
            )
            return

        # Create batch manager
        batch_manager = BatchImportManager(self.foundry_client)

        # Start import worker
        self.worker = BatchImportWorker(batch_manager, self.current_texts, self.actor_type)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_import_complete)
        self.worker.error.connect(self._on_import_error)

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.import_button.setEnabled(False)
        self.status_label.setText("Importing...")

        self.worker.start()

    def _on_progress(self, current: int, total: int) -> None:
        """Update progress bar."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Importing: {current}/{total}")

    def _on_import_complete(self, report) -> None:
        """Handle import completion."""
        self.current_report = report
        self.progress_bar.setVisible(False)
        self.import_button.setEnabled(True)

        # Display results
        self._display_results(report)

        # Show summary
        self.status_label.setText(report.summary())
        QMessageBox.information(
            self,
            "Batch Import Complete",
            report.summary(),
        )

    def _on_import_error(self, error: str) -> None:
        """Handle import error."""
        self.progress_bar.setVisible(False)
        self.import_button.setEnabled(True)
        self.status_label.setText("Error during import")
        QMessageBox.critical(
            self,
            "Import Error",
            f"Batch import failed:\n{error}",
        )

    def _display_results(self, report) -> None:
        """Display import results in table."""
        self.results_table.setRowCount(0)

        for idx, result in enumerate(report.results):
            self.results_table.insertRow(idx)

            # Index
            self.results_table.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))

            # Name
            name = result.danger_name or "(parsing failed)"
            self.results_table.setItem(idx, 1, QTableWidgetItem(name))

            # Status
            status_item = QTableWidgetItem(result.status.upper())
            if result.status == "success":
                status_item.setBackground(Qt.GlobalColor.green)
            elif result.status == "failed":
                status_item.setBackground(Qt.GlobalColor.red)
            self.results_table.setItem(idx, 2, status_item)

            # Actor ID
            actor_id = result.actor_id or ""
            self.results_table.setItem(idx, 3, QTableWidgetItem(actor_id))

            # Error
            error = result.error_message or ""
            self.results_table.setItem(idx, 4, QTableWidgetItem(error))

    def _export_failed(self) -> None:
        """Export failed entries for retry."""
        if not self.current_report:
            QMessageBox.warning(self, "No Results", "Run import first.")
            return

        failed = [r for r in self.current_report.results if r.status == "failed"]
        if not failed:
            QMessageBox.information(self, "No Failures", "All imports succeeded!")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Failed Dangers",
            "failed_dangers.jsonl",
            "JSONL Files (*.jsonl)",
        )

        if not file_path:
            return

        import json

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for result in failed:
                    entry = {
                        "text": result.input_text,
                        "error": result.error_message,
                    }
                    f.write(json.dumps(entry) + "\n")

            QMessageBox.information(
                self,
                "Export Successful",
                f"Exported {len(failed)} failed dangers to:\n{file_path}",
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to save file:\n{str(e)}",
            )

    def _clear_all(self) -> None:
        """Clear all data."""
        self.current_texts = []
        self.current_report = None
        self.input_label.setText("No input loaded")
        self.preview_text.clear()
        self.results_table.setRowCount(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.import_button.setEnabled(False)
        self.status_label.setText("Ready")

    def set_foundry_client(self, client) -> None:
        """Set the Foundry client."""
        self.foundry_client = client
