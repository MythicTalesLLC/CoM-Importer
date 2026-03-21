"""Single import tab for parsing and creating individual dangers/characters."""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QComboBox,
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

from ...actor_detector import ActorTypeDetector
from ...character_parser import CharacterParser
from ...danger_parser import DangerParser, ParsingError

logger = logging.getLogger(__name__)


class SingleImportTab(QWidget):
    """Tab for single danger/character input and creation."""

    def __init__(self):
        """Initialize the single import tab."""
        super().__init__()
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

        # Auto-detect button
        auto_detect_btn = QPushButton("Auto-Detect")
        auto_detect_btn.setMaximumWidth(100)
        auto_detect_btn.clicked.connect(self._auto_detect_actor_type)
        type_layout.addWidget(auto_detect_btn)

        type_layout.addStretch()
        layout.addLayout(type_layout)

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

        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(self._edit_actor)
        button_layout.addWidget(edit_button)

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

    def _on_actor_type_changed(self) -> None:
        """Handle actor type selection change."""
        if self.actor_type_combo.currentIndex() == 0:
            self.actor_type = "threat"
        else:
            self.actor_type = "character"
        logger.debug(f"Actor type changed to: {self.actor_type}")

    def _auto_detect_actor_type(self) -> None:
        """Auto-detect actor type based on pasted text and update dropdown."""
        text = self.text_input.toPlainText()
        if not text.strip():
            return

        detected_type = ActorTypeDetector.detect(text)
        confidence = ActorTypeDetector.confidence(text)

        # Update dropdown to match detected type
        if detected_type == "danger":
            self.actor_type_combo.setCurrentIndex(0)
        else:
            self.actor_type_combo.setCurrentIndex(1)

        # Log detection with confidence
        threat_conf = confidence["danger"]
        char_conf = confidence["character"]
        logger.debug(
            f"Auto-detected: {detected_type} "
            f"(danger: {threat_conf:.0%}, character: {char_conf:.0%})"
        )

    def _select_image(self) -> None:
        """Select an image file and OCR it."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if not file_path:
            return

        self.image_label.setText(f"Selected: {file_path}\nExtracting text...")

        # Show progress dialog
        progress = QMessageBox(self)
        progress.setWindowTitle("Processing...")
        progress.setText("Running OCR on image...\nThis may take a moment.")
        progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
        progress.show()

        try:
            from ...image_parser import ImageOCRFactory

            # Get OCR method from config (default to auto)
            ocr_method = getattr(self, "_ocr_method", "auto")
            tesseract_path = getattr(self, "_tesseract_path", None)
            vision_key = getattr(self, "_vision_api_key", None)

            # Create parser
            parser = ImageOCRFactory.create_parser(
                method=ocr_method,
                tesseract_path=tesseract_path,
                vision_api_key=vision_key,
            )

            # Extract text
            text = parser.parse_image(file_path)

            progress.close()

            # Populate text field
            self.text_input.setPlainText(text)
            self.image_label.setText(f"✓ Extracted from: {file_path}")

            # Auto-detect actor type from extracted text
            self._auto_detect_actor_type()

            QMessageBox.information(
                self,
                "OCR Complete",
                f"Extracted {len(text)} characters from image.",
            )

        except Exception as e:
            progress.close()
            self.image_label.setText(f"❌ Error: {str(e)}")
            QMessageBox.critical(
                self,
                "OCR Error",
                f"Failed to extract text from image:\n{str(e)}\n\n"
                "Make sure Tesseract is installed (brew install tesseract on Mac) "
                "or provide a Cloud Vision API key.",
            )
            logger.exception("Image OCR failed")

    def _select_pdf(self) -> None:
        """Select a PDF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if not file_path:
            return

        try:
            from ...pdf_handler import PDFHandler

            # Get page count
            page_count = PDFHandler.get_page_count(file_path)

            # Ask user which page to extract
            page_num, ok = self._show_page_selector(page_count)
            if not ok or page_num <= 0:
                return

            self.pdf_label.setText(f"Extracting page {page_num}...")

            # Show progress
            progress = QMessageBox(self)
            progress.setWindowTitle("Processing...")
            progress.setText(f"Extracting page {page_num} from PDF...\nRunning OCR...")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress.show()

            # Extract page as image and OCR it
            image = PDFHandler.extract_page_as_image(file_path, page_num, dpi=200)

            # Save to temp file for OCR
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                image.save(f.name)
                temp_image_path = f.name

            try:
                from ...image_parser import ImageOCRFactory

                # Get OCR method
                ocr_method = getattr(self, "_ocr_method", "auto")
                tesseract_path = getattr(self, "_tesseract_path", None)
                vision_key = getattr(self, "_vision_api_key", None)

                # Create parser and extract text
                parser = ImageOCRFactory.create_parser(
                    method=ocr_method,
                    tesseract_path=tesseract_path,
                    vision_api_key=vision_key,
                )
                text = parser.parse_image(temp_image_path)

                progress.close()

                # Populate text field
                self.text_input.setPlainText(text)
                self.pdf_label.setText(f"✓ Extracted page {page_num} from PDF")

                # Auto-detect actor type from extracted text
                self._auto_detect_actor_type()

                QMessageBox.information(
                    self,
                    "PDF OCR Complete",
                    f"Extracted {len(text)} characters from PDF page {page_num}.",
                )

            finally:
                import os

                os.unlink(temp_image_path)

        except Exception as e:
            self.pdf_label.setText(f"❌ Error: {str(e)}")
            QMessageBox.critical(
                self,
                "PDF Error",
                f"Failed to process PDF:\n{str(e)}",
            )
            logger.exception("PDF processing failed")

    def _show_page_selector(self, total_pages: int) -> tuple[int, bool]:
        """Show dialog to select PDF page."""
        from PyQt6.QtWidgets import (
            QDialog,
            QFormLayout,
            QSpinBox,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Select PDF Page")
        layout = QFormLayout()

        spinbox = QSpinBox()
        spinbox.setMinimum(1)
        spinbox.setMaximum(total_pages)
        spinbox.setValue(1)
        layout.addRow(f"Page (1-{total_pages}):", spinbox)

        dialog.setLayout(layout)

        buttons = QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        dialog.setStandardButtons(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return spinbox.value(), True
        return 0, False

    def _parse_input(self) -> None:
        """Parse the input text."""
        text = self.text_input.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "No Input", "Please enter or paste some text first.")
            return

        try:
            if self.actor_type == "threat":
                parser = DangerParser()
                actor, errors = parser.parse(text)
                actor_label = "Danger"
            else:
                parser = CharacterParser()
                actor, errors = parser.parse(text)
                actor_label = "Character"

            if errors:
                error_msg = "\n".join(f"- {e.message}" for e in errors)
                QMessageBox.information(
                    self,
                    "Parsing Complete (with warnings)",
                    f"Successfully parsed {actor_label}!\n\nWarnings:\n{error_msg}",
                )
            else:
                QMessageBox.information(
                    self, "Parsing Complete", f"{actor_label} parsed successfully!"
                )

            # Store the parsed actor
            self.current_actor = actor
            self.current_actor_type = self.actor_type
        except ParsingError as e:
            QMessageBox.critical(self, "Parsing Error", f"Failed to parse: {e}")

    def _edit_actor(self) -> None:
        """Edit the parsed actor."""
        if not hasattr(self, "current_actor") or not self.current_actor:
            QMessageBox.warning(self, "No Import Parsed", "Please parse text first.")
            return

        from ..dialogs import EditActorDialog

        dialog = EditActorDialog(self.current_actor, self)
        if dialog.exec():
            self.current_actor = dialog.get_actor()
            QMessageBox.information(self, "Changes Saved", "Actor updated successfully!")

    def _show_preview(self) -> None:
        """Show JSON preview of parsed actor."""
        if not hasattr(self, "current_actor") or not self.current_actor:
            QMessageBox.warning(self, "No Import Parsed", "Please parse text first.")
            return

        import json

        try:
            if self.current_actor_type == "threat":
                from ...danger_to_foundry import convert_danger_to_foundry

                actor_json = convert_danger_to_foundry(self.current_actor)
            else:
                from ...character_to_foundry import convert_character_to_foundry

                actor_json = convert_character_to_foundry(self.current_actor)

            json_str = json.dumps(actor_json, indent=2)

            # Show in a dialog
            preview_dialog = QMessageBox(self)
            preview_dialog.setWindowTitle("JSON Preview")
            preview_dialog.setText("Foundry Actor JSON:")
            preview_dialog.setDetailedText(json_str)
            preview_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
            preview_dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate preview:\n{str(e)}")

    def _create_actor(self) -> None:
        """Create actor in Foundry."""
        if not hasattr(self, "current_actor") or not self.current_actor:
            QMessageBox.warning(self, "No Import Parsed", "Please parse text first.")
            return

        if not hasattr(self, "foundry_client") or not self.foundry_client:
            QMessageBox.warning(
                self,
                "Not Configured",
                "Please configure Foundry connection in the Configuration tab first.",
            )
            return

        try:
            # Show progress
            progress = QMessageBox(self)
            progress.setWindowTitle("Creating...")
            actor_label = "Danger" if self.current_actor_type == "threat" else "Character"
            progress.setText(f"Creating {actor_label} in Foundry...")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress.show()

            # Convert to Foundry format
            if self.current_actor_type == "threat":
                from ...danger_to_foundry import convert_danger_to_foundry

                actor_json = convert_danger_to_foundry(self.current_actor)
            else:
                from ...character_to_foundry import convert_character_to_foundry

                actor_json = convert_character_to_foundry(self.current_actor)

            # Create in Foundry
            actor_id = self.foundry_client.create_actor(actor_json)

            progress.close()

            # Notify history to add entry
            if hasattr(self, "history_callback"):
                self.history_callback(
                    actor_id=actor_id,
                    danger_name=self.current_actor.name,
                    actor_json=actor_json,
                    danger_rating=getattr(self.current_actor, "danger_rating", None),
                    source="text",
                    status="success",
                )

            QMessageBox.information(
                self,
                "Success",
                f"{actor_label} created in Foundry!\n\nActor ID: {actor_id}",
            )

            # Clear and reset
            self.text_input.clear()
            self.current_actor = None
            self.current_actor_type = None

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create {actor_label.lower()} in Foundry:\n{str(e)}",
            )
            logger.exception("Failed to create actor")

    def _save_draft(self) -> None:
        """Save parsed actor as draft JSON file."""
        if not hasattr(self, "current_actor") or not self.current_actor:
            QMessageBox.warning(self, "No Import Parsed", "Please parse text first.")
            return

        import json

        actor_label = "Danger" if self.current_actor_type == "threat" else "Character"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Save {actor_label} as JSON",
            f"{self.current_actor.name.replace(' ', '_')}_draft.json",
            "JSON Files (*.json)",
        )

        if not file_path:
            return

        try:
            if self.current_actor_type == "threat":
                from ...danger_to_foundry import convert_danger_to_foundry

                actor_json = convert_danger_to_foundry(self.current_actor)
            else:
                from ...character_to_foundry import convert_character_to_foundry

                actor_json = convert_character_to_foundry(self.current_actor)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(actor_json, f, indent=2, ensure_ascii=False)
            QMessageBox.information(
                self,
                "Draft Saved",
                f"{actor_label} saved to:\n{file_path}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save draft:\n{str(e)}")

    def set_foundry_client(self, client):
        """Set the Foundry client."""
        self.foundry_client = client

    def set_history_callback(self, callback):
        """Set the callback for history updates."""
        self.history_callback = callback
