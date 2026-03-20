"""Single import tab for parsing and creating individual dangers/characters."""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...danger_parser import DangerParser, ParsingError

logger = logging.getLogger(__name__)


class SingleImportTab(QWidget):
    """Tab for single danger/character input and creation."""

    def __init__(self):
        """Initialize the single import tab."""
        super().__init__()
        self._create_ui()

    def _create_ui(self) -> None:
        """Create the user interface."""
        layout = QVBoxLayout(self)

        # Input type selector
        input_selector = self._create_input_selector()
        layout.addWidget(input_selector)

        # Main content area (will be updated by input selector)
        self.content_layout = QVBoxLayout()
        layout.addLayout(self.content_layout)

        # Action buttons
        button_layout = QHBoxLayout()
        parse_button = QPushButton("Parse")
        parse_button.clicked.connect(self._parse_input)
        button_layout.addWidget(parse_button)

        preview_button = QPushButton("Preview JSON")
        preview_button.clicked.connect(self._show_preview)
        button_layout.addWidget(preview_button)

        create_button = QPushButton("Create in Foundry")
        create_button.clicked.connect(self._create_actor)
        button_layout.addWidget(create_button)

        save_button = QPushButton("Save as Draft")
        save_button.clicked.connect(self._save_draft)
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

    def _create_input_selector(self) -> QTabWidget:
        """Create input method selector tabs."""
        tabs = QTabWidget()

        # Text input tab
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.addWidget(QLabel("Paste danger/character text or PDF content:"))
        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText(
            "Paste danger description here...\n\nExample:\nDanger Rating: 3\nName\nDescription..."
        )
        text_layout.addWidget(self.text_input)
        tabs.addTab(text_widget, "Text")

        # Image input tab
        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        image_layout.addWidget(QLabel("Select image or PDF page:"))
        image_button_layout = QHBoxLayout()
        select_image_btn = QPushButton("Select Image...")
        select_image_btn.clicked.connect(self._select_image)
        image_button_layout.addWidget(select_image_btn)
        self.image_label = QLabel("No image selected")
        image_button_layout.addWidget(self.image_label)
        image_layout.addLayout(image_button_layout)
        image_layout.addStretch()
        tabs.addTab(image_widget, "Image")

        # PDF input tab
        pdf_widget = QWidget()
        pdf_layout = QVBoxLayout(pdf_widget)
        pdf_layout.addWidget(QLabel("Extract from PDF:"))
        pdf_button_layout = QHBoxLayout()
        select_pdf_btn = QPushButton("Select PDF...")
        select_pdf_btn.clicked.connect(self._select_pdf)
        pdf_button_layout.addWidget(select_pdf_btn)
        self.pdf_label = QLabel("No PDF selected")
        pdf_button_layout.addWidget(self.pdf_label)
        pdf_layout.addLayout(pdf_button_layout)
        pdf_layout.addStretch()
        tabs.addTab(pdf_widget, "PDF")

        return tabs

    def _select_image(self) -> None:
        """Select an image file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if file_path:
            self.image_label.setText(f"Selected: {file_path}")
            # TODO: Implement OCR

    def _select_pdf(self) -> None:
        """Select a PDF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            self.pdf_label.setText(f"Selected: {file_path}")
            # TODO: Implement PDF extraction

    def _parse_input(self) -> None:
        """Parse the input text."""
        text = self.text_input.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "No Input", "Please enter or paste some text first.")
            return

        try:
            parser = DangerParser()
            danger, errors = parser.parse(text)

            if errors:
                error_msg = "\n".join(f"- {e.message}" for e in errors)
                QMessageBox.information(
                    self,
                    "Parsing Complete (with warnings)",
                    f"Successfully parsed!\n\nWarnings:\n{error_msg}",
                )
            else:
                QMessageBox.information(self, "Parsing Complete", "Text parsed successfully!")

            self.current_danger = danger
        except ParsingError as e:
            QMessageBox.critical(self, "Parsing Error", f"Failed to parse: {e}")

    def _show_preview(self) -> None:
        """Show JSON preview of parsed danger."""
        if not hasattr(self, "current_danger"):
            QMessageBox.warning(self, "No Danger Parsed", "Please parse text first.")
            return

        # TODO: Implement JSON preview dialog
        QMessageBox.information(self, "Preview", "JSON preview feature coming soon...")

    def _create_actor(self) -> None:
        """Create actor in Foundry."""
        if not hasattr(self, "current_danger"):
            QMessageBox.warning(self, "No Danger Parsed", "Please parse text first.")
            return

        # TODO: Implement Foundry creation
        QMessageBox.information(self, "Creation", "Foundry creation feature coming soon...")

    def _save_draft(self) -> None:
        """Save parsed danger as draft JSON file."""
        if not hasattr(self, "current_danger"):
            QMessageBox.warning(self, "No Danger Parsed", "Please parse text first.")
            return

        # TODO: Implement draft saving
        QMessageBox.information(self, "Save Draft", "Draft save feature coming soon...")
