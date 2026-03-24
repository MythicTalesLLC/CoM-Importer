"""Single import tab for parsing and creating individual dangers/characters."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...danger_parser import DangerParser, ParsingError

logger = logging.getLogger(__name__)


class DragDropImageWidget(QWidget):
    """Widget for image input with drag-and-drop and path entry support."""

    def __init__(self, parent=None):
        """Initialize the drag-drop widget."""
        super().__init__(parent)
        self.image_path = ""
        self._create_ui()

    def _create_ui(self) -> None:
        """Create the UI."""
        layout = QVBoxLayout(self)

        # Path entry
        layout.addWidget(QLabel("Image file path (or drag & drop below):"))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText(
            "Enter full path (e.g., /Users/mythic/Downloads/image.png)"
        )
        self.path_input.returnPressed.connect(self._load_from_path)
        path_layout.addWidget(self.path_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_files)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        # Drag and drop zone
        self.drop_zone = QLabel("📁 Drag image files here or click Browse")
        self.drop_zone.setStyleSheet(
            "QLabel {"
            "  border: 2px dashed #2196F3;"
            "  border-radius: 8px;"
            "  padding: 40px;"
            "  text-align: center;"
            "  background-color: #F5F5F5;"
            "  color: #666;"
            "  font-size: 14px;"
            "}"
        )
        self.drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.dragEnterEvent = self._drag_enter_event
        self.drop_zone.dropEvent = self._drop_event
        layout.addWidget(self.drop_zone, 1)

        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

    def _drag_enter_event(self, event) -> None:
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_zone.setStyleSheet(
                "QLabel {"
                "  border: 2px solid #2196F3;"
                "  border-radius: 8px;"
                "  padding: 40px;"
                "  background-color: #E3F2FD;"
                "  color: #1976D2;"
                "  font-size: 14px;"
                "  font-weight: bold;"
                "}"
            )

    def _drag_leave_event(self, event) -> None:
        """Handle drag leave event."""
        self.drop_zone.setStyleSheet(
            "QLabel {"
            "  border: 2px dashed #2196F3;"
            "  border-radius: 8px;"
            "  padding: 40px;"
            "  text-align: center;"
            "  background-color: #F5F5F5;"
            "  color: #666;"
            "  font-size: 14px;"
            "}"
        )

    def _drop_event(self, event) -> None:
        """Handle drop event."""
        self._drag_leave_event(event)
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self._load_image(file_path)

    def _browse_files(self) -> None:
        """Browse for image file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            str(Path.home() / "Downloads"),
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)",
        )
        if file_path:
            self.path_input.setText(file_path)
            self._load_image(file_path)

    def _load_from_path(self) -> None:
        """Load image from path input."""
        file_path = self.path_input.text().strip()
        if file_path:
            self._load_image(file_path)

    def _load_image(self, file_path: str) -> None:
        """Load and validate image file."""
        path = Path(file_path)

        if not path.exists():
            self.status_label.setText(f"❌ File not found: {file_path}")
            return

        if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
            self.status_label.setText(
                f"❌ Invalid file type: {path.suffix}. Use PNG, JPG, BMP, or GIF."
            )
            return

        self.image_path = file_path
        self.path_input.setText(file_path)
        self.status_label.setText(f"✓ Ready to process: {path.name}")

    def get_image_path(self) -> str:
        """Get the selected image path."""
        return self.image_path


class DragDropPDFWidget(QWidget):
    """Widget for PDF input with drag-and-drop and browse-button support."""

    def __init__(self, parent=None):
        """Initialize the drag-drop PDF widget."""
        super().__init__(parent)
        self._file_callback = None
        self._create_ui()
        self.setAcceptDrops(True)

    def _create_ui(self) -> None:
        """Create the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_row = QHBoxLayout()
        self.select_btn = QPushButton("Select PDF…")
        self.select_btn.clicked.connect(self._browse)
        btn_row.addWidget(self.select_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.drop_zone = QLabel("📄 Drag a PDF here or click Select PDF…")
        self.drop_zone.setStyleSheet(
            "QLabel {"
            "  border: 2px dashed #2196F3;"
            "  border-radius: 8px;"
            "  padding: 40px;"
            "  text-align: center;"
            "  background-color: #F5F5F5;"
            "  color: #666;"
            "  font-size: 14px;"
            "}"
        )
        self.drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.drop_zone, 1)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

    # ── drag handling ────────────────────────────────────────────────────────

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(url.toLocalFile().lower().endswith(".pdf") for url in urls):
                event.acceptProposedAction()
                self.drop_zone.setStyleSheet(
                    "QLabel {"
                    "  border: 2px solid #2196F3;"
                    "  border-radius: 8px;"
                    "  padding: 40px;"
                    "  background-color: #E3F2FD;"
                    "  color: #1976D2;"
                    "  font-size: 14px;"
                    "  font-weight: bold;"
                    "}"
                )

    def dragLeaveEvent(self, event) -> None:
        self._reset_drop_style()

    def dropEvent(self, event) -> None:
        self._reset_drop_style()
        urls = event.mimeData().urls()
        for url in urls:
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                self._emit_file(path)
                break

    def _reset_drop_style(self) -> None:
        self.drop_zone.setStyleSheet(
            "QLabel {"
            "  border: 2px dashed #2196F3;"
            "  border-radius: 8px;"
            "  padding: 40px;"
            "  text-align: center;"
            "  background-color: #F5F5F5;"
            "  color: #666;"
            "  font-size: 14px;"
            "}"
        )

    def _browse(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            self._emit_file(file_path)

    def _emit_file(self, path: str) -> None:
        self.status_label.setText(f"📄 {Path(path).name}")
        if self._file_callback:
            self._file_callback(path)

    def set_file_callback(self, callback) -> None:
        """Set the callback called with the PDF path when a file is selected."""
        self._file_callback = callback


logger = logging.getLogger(__name__)


class SingleImportTab(QWidget):
    """Tab for single threat input and creation."""

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

        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(self._edit_actor)
        button_layout.addWidget(edit_button)

        preview_button = QPushButton("Preview JSON")
        preview_button.clicked.connect(self._show_preview)
        button_layout.addWidget(preview_button)

        export_button = QPushButton("Export JSON + Macro")
        export_button.clicked.connect(self._export_json)
        button_layout.addWidget(export_button)

        layout.addLayout(button_layout)

        # "Create from scratch" button
        create_layout = QHBoxLayout()
        create_layout.addWidget(QLabel("Create from scratch:"))
        new_danger_button = QPushButton("＋ New Danger / Threat / NPC")
        new_danger_button.setToolTip("Open a blank danger actor to build from scratch")
        new_danger_button.clicked.connect(self._new_danger)
        create_layout.addWidget(new_danger_button)
        create_layout.addStretch()
        layout.addLayout(create_layout)

        # Parse status bar — single line showing parse result instead of popup dialogs
        self.parse_status_label = QLabel("")
        self.parse_status_label.setStyleSheet("padding: 4px; font-weight: bold;")
        layout.addWidget(self.parse_status_label)

    def _create_input_selector(self) -> QTabWidget:
        """Create input method selector tabs."""
        tabs = QTabWidget()

        # Text input tab
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.addWidget(QLabel("Paste threat/danger text or PDF content:"))
        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText(
            "Paste threat description here...\n\nExample:\nDanger Rating: 3\nName\nDescription..."
        )
        text_layout.addWidget(self.text_input)
        tabs.addTab(text_widget, "Text")

        # Image input tab
        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        self.image_drop_widget = DragDropImageWidget()
        image_layout.addWidget(self.image_drop_widget)
        tabs.addTab(image_widget, "Image")

        # PDF input tab
        pdf_widget = QWidget()
        pdf_layout = QVBoxLayout(pdf_widget)
        pdf_layout.addWidget(QLabel("Extract from PDF:"))
        self.pdf_drop_widget = DragDropPDFWidget()
        self.pdf_drop_widget.set_file_callback(self._on_pdf_dropped)
        pdf_layout.addWidget(self.pdf_drop_widget)
        tabs.addTab(pdf_widget, "PDF")

        return tabs

    def _on_actor_type_changed(self) -> None:
        pass  # type selector removed; always threat

    def _auto_detect_actor_type(self) -> None:
        pass  # actor detection removed; always threat

    def _set_parse_status(self, msg: str, style: str = "ok") -> None:
        """Update the parse status label. style: 'ok' | 'warn' | 'error'."""
        colors = {"ok": "#2e7d32", "warn": "#e65100", "error": "#c62828"}
        bg = {"ok": "#e8f5e9", "warn": "#fff3e0", "error": "#ffebee"}
        color = colors.get(style, "#000")
        bg_color = bg.get(style, "#fff")
        self.parse_status_label.setStyleSheet(
            f"padding: 4px; font-weight: bold; color: {color}; background-color: {bg_color};"
            " border-radius: 3px;"
        )
        self.parse_status_label.setText(msg)

    def _process_image(self, file_path: str) -> None:
        """Process image file with OCR and populate text field."""
        self._set_parse_status("⏳ Running OCR on image…", "warn")
        # Force UI repaint so the status shows before blocking OCR call
        from PyQt6.QtWidgets import QApplication

        QApplication.processEvents()

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

            # Populate text field
            self.text_input.setPlainText(text)

            self._set_parse_status(f"✓ OCR complete — {len(text)} characters extracted", "ok")

        except Exception as e:
            QMessageBox.critical(
                self,
                "OCR Error",
                f"Failed to extract text from image:\n{str(e)}\n\n"
                "Make sure Tesseract is installed (brew install tesseract on Mac) "
                "or provide a Cloud Vision API key.",
            )
            self._set_parse_status(f"❌ OCR failed: {e}", "error")
            logger.exception("Image OCR failed")

    def _on_pdf_dropped(self, file_path: str) -> None:
        """Called when a PDF is selected via drag-drop or the browse button."""
        self._process_pdf_file(file_path)

    def _select_pdf(self) -> None:
        """Open a file-picker dialog and process the selected PDF."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            self._process_pdf_file(file_path)

    def _process_pdf_file(self, file_path: str) -> None:
        """Extract OCR text from a PDF file and populate the text field."""
        try:
            from ...pdf_handler import PDFHandler

            # Get page count
            page_count = PDFHandler.get_page_count(file_path)

            # Ask user which page to extract
            page_num, ok = self._show_page_selector(page_count)
            if not ok or page_num <= 0:
                return

            self._set_parse_status(f"⏳ Extracting page {page_num} from PDF…", "warn")

            from PyQt6.QtWidgets import QApplication

            QApplication.processEvents()

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

                # Populate text field
                self.text_input.setPlainText(text)
                self.pdf_drop_widget.status_label.setText(
                    f"✓ Page {page_num} extracted from {Path(file_path).name}"
                )

                # Auto-detect removed — always threat
                self._set_parse_status(
                    f"✓ PDF OCR complete — {len(text)} characters from page {page_num}", "ok"
                )

            finally:
                import os

                os.unlink(temp_image_path)

        except Exception as e:
            self.pdf_drop_widget.status_label.setText(f"❌ Error: {str(e)}")
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
            QDialogButtonBox,
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

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return spinbox.value(), True
        return 0, False

    def _parse_input(self) -> None:
        """Parse the input text. If on Image tab, process image first."""
        # Check if we're on the image tab and have an image path
        image_path = self.image_drop_widget.get_image_path()
        if image_path and not self.text_input.toPlainText().strip():
            # Process the image (this populates text_input)
            self._process_image(image_path)
            # Don't return - continue to parse the extracted text below

        text = self.text_input.toPlainText()
        if not text.strip():
            self._set_parse_status("⚠ No input — paste text or load an image/PDF first.", "warn")
            return

        try:
            parser = DangerParser()
            actor, errors = parser.parse(text)
            actor_label = "Danger"

            if errors:
                warn_summary = "; ".join(e.message for e in errors[:3])
                suffix = f" (+{len(errors) - 3} more)" if len(errors) > 3 else ""
                self._set_parse_status(
                    f"⚠ {actor_label} parsed with warnings: {warn_summary}{suffix}", "warn"
                )
            else:
                self._set_parse_status(f"✓ {actor_label} parsed successfully!", "ok")

            # Store the parsed actor
            self.current_actor = actor
            self.current_actor_type = "threat"
        except ParsingError as e:
            self._set_parse_status(f"❌ Parse failed: {e}", "error")

    def _edit_actor(self) -> None:
        """Edit the parsed actor."""
        if not hasattr(self, "current_actor") or not self.current_actor:
            QMessageBox.warning(self, "No Import Parsed", "Please parse text first.")
            return

        from ..dialogs import EditActorDialog

        dialog = EditActorDialog(self.current_actor, self)
        if dialog.exec():
            self.current_actor = dialog.get_actor()
            self._set_parse_status("✓ Actor edits saved.", "ok")

    def _new_danger(self) -> None:
        """Create a brand-new danger/threat/NPC from scratch."""
        from ...com_schema import DangerActor
        from ..dialogs import EditActorDialog

        actor = DangerActor(name="New Danger")
        dialog = EditActorDialog(actor, self)
        if dialog.exec():
            self.current_actor = dialog.get_actor()
            self.current_actor_type = "threat"
            self._set_parse_status(
                f"✓ New danger '{self.current_actor.name}' ready — click Export to save.", "ok"
            )

    def _show_preview(self) -> None:
        """Show JSON preview of parsed actor."""
        if not hasattr(self, "current_actor") or not self.current_actor:
            QMessageBox.warning(self, "No Import Parsed", "Please parse text first.")
            return

        import json

        try:
            from ...danger_to_foundry import convert_danger_to_foundry

            actor_json = convert_danger_to_foundry(self.current_actor)

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

    def _export_json(self) -> None:
        """Export actor as JSON file with import macro."""
        if not hasattr(self, "current_actor") or not self.current_actor:
            QMessageBox.warning(self, "No Import Parsed", "Please parse text first.")
            return

        try:
            # Convert to Foundry format
            from ...danger_to_foundry import convert_danger_to_foundry

            actor_json = convert_danger_to_foundry(self.current_actor)
            actor_label = "Danger"

            # Export to file
            from ...foundry_export import FoundryJsonExporter

            export_path = FoundryJsonExporter.export_actor_to_file(actor_json, export_macro=True)

            # Show result dialog
            items_count = len(actor_json.get("items", []))

            from ..dialogs import ExportResultDialog

            export_dialog = ExportResultDialog(
                export_path=export_path,
                actor_name=self.current_actor.name,
                items_count=items_count,
                parent=self,
            )
            export_dialog.exec()

            # Notify history if callback exists
            if hasattr(self, "history_callback"):
                self.history_callback(
                    actor_id=actor_json.get("_id", "exported"),
                    danger_name=self.current_actor.name,
                    actor_json=actor_json,
                    danger_rating=getattr(self.current_actor, "danger_rating", None),
                    source="text",
                    status="exported",
                )

            # Clear and reset
            self.text_input.clear()
            self.current_actor = None
            self.current_actor_type = None

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export {actor_label.lower()}:\n{str(e)}",
            )
            logger.exception("Failed to export actor")

    def set_history_callback(self, callback):
        """Set the callback for history updates."""
        self.history_callback = callback

    def set_foundry_client(self, client) -> None:
        """Receive the Foundry client from the config tab (currently unused by this tab)."""
        self._foundry_client = client
