"""Dialog components for the CoM Importer GUI."""

from __future__ import annotations

import json
import logging

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..character_to_foundry import convert_character_to_foundry
from ..com_schema import CharacterActor, DangerActor
from ..danger_to_foundry import convert_danger_to_foundry

logger = logging.getLogger(__name__)


class EditActorDialog(QDialog):
    """Dialog for editing parsed danger or character actors before creation."""

    def __init__(self, actor: DangerActor | CharacterActor, parent=None):
        """Initialize edit dialog."""
        super().__init__(parent)
        self.actor = actor
        self.is_character = isinstance(actor, CharacterActor)
        self.setWindowTitle("Edit Character" if self.is_character else "Edit Danger")
        self.setGeometry(100, 100, 1000, 700)
        self._create_ui()

    def _create_ui(self) -> None:
        """Create the user interface."""
        layout = QVBoxLayout(self)

        # Create tabs for different sections
        tabs = QTabWidget()

        # Basic info tab
        basic_tab = self._create_basic_tab()
        tabs.addTab(basic_tab, "Basic Info")

        # Actor-specific tab
        if self.is_character:
            spec_tab = self._create_character_tab()
            tabs.addTab(spec_tab, "Character Details")
        else:
            spec_tab = self._create_danger_tab()
            tabs.addTab(spec_tab, "Danger Details")

        # Preview tab
        preview_tab = self._create_preview_tab()
        tabs.addTab(preview_tab, "JSON Preview")

        layout.addWidget(tabs)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _create_basic_tab(self) -> QWidget:
        """Create basic information tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Name
        layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit(self.actor.name)
        layout.addWidget(self.name_input)

        # Description
        layout.addWidget(QLabel("Description:"))
        self.description_input = QPlainTextEdit(self.actor.description)
        self.description_input.setMaximumHeight(150)
        layout.addWidget(self.description_input)

        # Biography (optional)
        layout.addWidget(QLabel("Biography (optional):"))
        self.biography_input = QPlainTextEdit(self.actor.biography)
        self.biography_input.setMaximumHeight(100)
        layout.addWidget(self.biography_input)

        # GM Notes (optional)
        layout.addWidget(QLabel("GM Notes (optional):"))
        self.gmnotes_input = QPlainTextEdit(self.actor.gmnotes)
        self.gmnotes_input.setMaximumHeight(100)
        layout.addWidget(self.gmnotes_input)

        layout.addStretch()
        return widget

    def _create_danger_tab(self) -> QWidget:
        """Create danger-specific tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        danger = self.actor

        # Danger Rating
        layout.addWidget(QLabel("Danger Rating (optional):"))
        rating_layout = QHBoxLayout()
        self.rating_input = QLineEdit(danger.danger_rating or "")
        rating_layout.addWidget(self.rating_input)
        rating_layout.addStretch()
        layout.addLayout(rating_layout)

        # Mythos
        layout.addWidget(QLabel("Mythos:"))
        self.mythos_input = QPlainTextEdit(danger.mythos)
        self.mythos_input.setMaximumHeight(80)
        layout.addWidget(self.mythos_input)

        # Logos
        layout.addWidget(QLabel("Logos:"))
        self.logos_input = QPlainTextEdit(danger.logos)
        self.logos_input.setMaximumHeight(80)
        layout.addWidget(self.logos_input)

        # Spectrums table
        layout.addWidget(QLabel("Spectrums:"))
        self.spectrums_table = QTableWidget()
        self.spectrums_table.setColumnCount(3)
        self.spectrums_table.setHorizontalHeaderLabels(["Name", "Current", "Max"])
        self.spectrums_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.spectrums_table.setMaximumHeight(150)

        # Populate spectrums
        for spectrum in danger.spectrums:
            row = self.spectrums_table.rowCount()
            self.spectrums_table.insertRow(row)
            self.spectrums_table.setItem(row, 0, QTableWidgetItem(spectrum.name))
            self.spectrums_table.setItem(row, 1, QTableWidgetItem(str(spectrum.current_tier)))
            self.spectrums_table.setItem(row, 2, QTableWidgetItem(str(spectrum.max_tier)))

        layout.addWidget(self.spectrums_table)

        # GM Moves count
        layout.addWidget(QLabel(f"GM Moves: {len(danger.gm_moves)} (edit in JSON preview)"))

        layout.addStretch()
        return widget

    def _create_character_tab(self) -> QWidget:
        """Create character-specific tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        character = self.actor

        # Pronouns
        layout.addWidget(QLabel("Pronouns (optional):"))
        self.pronouns_input = QLineEdit(character.pronouns)
        layout.addWidget(self.pronouns_input)

        # Juice help
        layout.addWidget(QLabel("Juice - Help:"))
        juice_layout = QHBoxLayout()
        self.juice_help_input = QSpinBox()
        self.juice_help_input.setMaximum(9)
        self.juice_help_input.setValue(character.juice_help)
        juice_layout.addWidget(self.juice_help_input)
        juice_layout.addStretch()
        layout.addLayout(juice_layout)

        # Juice hurt
        layout.addWidget(QLabel("Juice - Hurt:"))
        juice_hurt_layout = QHBoxLayout()
        self.juice_hurt_input = QSpinBox()
        self.juice_hurt_input.setMaximum(9)
        self.juice_hurt_input.setValue(character.juice_hurt)
        juice_hurt_layout.addWidget(self.juice_hurt_input)
        juice_hurt_layout.addStretch()
        layout.addLayout(juice_hurt_layout)

        # Themes
        layout.addWidget(QLabel(f"Themes: {len(character.themes)} (edit in JSON preview)"))

        layout.addStretch()
        return widget

    def _create_preview_tab(self) -> QWidget:
        """Create JSON preview tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Foundry Actor JSON:"))
        self.preview_text = QPlainTextEdit()
        self.preview_text.setReadOnly(True)
        layout.addWidget(self.preview_text)

        # Refresh button
        refresh_btn = QPushButton("Refresh Preview")
        refresh_btn.clicked.connect(self._update_preview)
        layout.addWidget(refresh_btn)

        # Initial preview
        self._update_preview()

        return widget

    def _update_preview(self) -> None:
        """Update the JSON preview."""
        # Apply current edits to actor
        self._apply_edits()

        # Convert and display
        try:
            if self.is_character:
                actor_json = convert_character_to_foundry(self.actor)
            else:
                actor_json = convert_danger_to_foundry(self.actor)

            json_str = json.dumps(actor_json, indent=2)
            self.preview_text.setPlainText(json_str)
        except Exception as e:
            self.preview_text.setPlainText(f"Error generating JSON:\n{str(e)}")
            logger.exception("Error generating preview JSON")

    def _apply_edits(self) -> None:
        """Apply current edits from the UI back to the actor."""
        # Basic fields
        self.actor.name = self.name_input.text().strip()
        self.actor.description = self.description_input.toPlainText().strip()
        self.actor.biography = self.biography_input.toPlainText().strip()
        self.actor.gmnotes = self.gmnotes_input.toPlainText().strip()

        if self.is_character:
            self.actor.pronouns = self.pronouns_input.text().strip()
            self.actor.juice_help = self.juice_help_input.value()
            self.actor.juice_hurt = self.juice_hurt_input.value()
        else:
            # Danger-specific
            danger = self.actor
            danger.danger_rating = self.rating_input.text().strip() or None
            danger.mythos = self.mythos_input.toPlainText().strip()
            danger.logos = self.logos_input.toPlainText().strip()

            # Update spectrums from table
            danger.spectrums = []
            for row in range(self.spectrums_table.rowCount()):
                name_item = self.spectrums_table.item(row, 0)
                current_item = self.spectrums_table.item(row, 1)
                max_item = self.spectrums_table.item(row, 2)

                if name_item:
                    from ..com_schema import Spectrum

                    spectrum = Spectrum(
                        name=name_item.text().strip(),
                        current_tier=int(current_item.text() or "0"),
                        max_tier=int(max_item.text() or "4"),
                    )
                    danger.spectrums.append(spectrum)

    def _on_save(self) -> None:
        """Save changes and close dialog."""
        # Log before applying edits
        if not self.is_character:
            print("\n[EDIT] Before _apply_edits():")
            print(f"[EDIT]   - GM Moves: {len(self.actor.gm_moves)}")
            print(f"[EDIT]   - Spectrums: {len(self.actor.spectrums)}")
            print(f"[EDIT]   - Tags: {len(self.actor.tags)}")
            print(f"[EDIT]   - Statuses: {len(self.actor.statuses)}")

        self._apply_edits()

        # Log after applying edits
        if not self.is_character:
            print("[EDIT] After _apply_edits():")
            print(f"[EDIT]   - GM Moves: {len(self.actor.gm_moves)}")
            print(f"[EDIT]   - Spectrums: {len(self.actor.spectrums)}")
            print(f"[EDIT]   - Tags: {len(self.actor.tags)}")
            print(f"[EDIT]   - Statuses: {len(self.actor.statuses)}")

        # Validate
        errors = self.actor.validate()
        if errors:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "Validation Errors",
                "Please fix the following issues:\n\n" + "\n".join(errors),
            )
            return

        self.accept()

    def get_actor(self) -> DangerActor | CharacterActor:
        """Get the edited actor."""
        return self.actor


class ExportResultDialog(QDialog):
    """Dialog showing successful export and next steps for user."""

    def __init__(self, export_path: str, actor_name: str, items_count: int, parent=None):
        """
        Initialize export result dialog.

        Args:
            export_path: Path to exported JSON file
            actor_name: Name of the exported actor
            items_count: Number of items exported
        """
        super().__init__(parent)
        self.export_path = export_path
        self.actor_name = actor_name
        self.items_count = items_count
        self.setWindowTitle("Export Complete")
        self.setGeometry(150, 150, 900, 500)
        self._create_ui()

    def _create_ui(self) -> None:
        """Create the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("✓ Export Complete - REST API Limitation Workaround")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2e7d32;")
        layout.addWidget(title)

        # Explanation
        explanation = QPlainTextEdit()
        explanation.setReadOnly(True)
        explanation.setPlainText(
            f"""WHAT HAPPENED:
Your threat actor was successfully created in Foundry, but due to REST API
limitations, the items (GM moves, spectrums, tags, statuses) could not be
linked via the remote API.

SOLUTION - AUTOMATIC EXPORT:
Your complete actor JSON with all {self.items_count} items has been automatically
exported and is ready to import.

ACTOR: {self.actor_name}
ITEMS: {self.items_count} (moves, spectrums, tags)
FILE: {self.export_path}"""
        )
        explanation.setStyleSheet(
            "background-color: #f5f5f5; padding: 10px; border: 1px solid #ddd; border-radius: 4px;"
        )
        layout.addWidget(explanation)

        # Next steps
        steps_label = QLabel("IMPORT INTO FOUNDRY (3 Steps):")
        steps_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
        layout.addWidget(steps_label)

        steps = QPlainTextEdit()
        steps.setReadOnly(True)
        filename = self.export_path.split("/")[-1]
        steps.setPlainText(
            f"""1. Open your Foundry instance
2. Navigate to the Actors sidebar
3. Click "Import Actors" button
4. Select: {filename}
5. Click Import
   → All items will be created with proper relationships

Once imported, refresh your browser and check the actor sheet. You'll see:
  • All GM moves listed
  • All spectrums with correct tiers
  • All tags and statuses properly linked"""
        )
        steps.setStyleSheet(
            "background-color: #fff3e0; padding: 10px; border: 1px solid #ffb74d;"
            " border-radius: 4px;"
        )
        layout.addWidget(steps)

        # Buttons
        button_layout = QHBoxLayout()

        copy_btn = QPushButton("Copy File Path")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        button_layout.addWidget(copy_btn)

        open_btn = QPushButton("Open File Location")
        open_btn.clicked.connect(self._open_file_location)
        button_layout.addWidget(open_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _copy_to_clipboard(self) -> None:
        """Copy export path to clipboard."""
        from PyQt6.QtGui import QClipboard
        from PyQt6.QtWidgets import QApplication

        cb = QApplication.clipboard()
        cb.setText(self.export_path, QClipboard.Mode.Clipboard)

        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(
            self, "Copied", f"File path copied to clipboard:\n{self.export_path}"
        )

    def _open_file_location(self) -> None:
        """Open the file location in system file browser."""
        import subprocess
        from pathlib import Path

        file_path = Path(self.export_path)

        # Open file location in native file browser
        if file_path.exists():
            if self.parent() and hasattr(self.parent(), "show"):
                # macOS
                try:
                    subprocess.run(["open", "-R", str(file_path)], check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Windows/Linux fallback
                    try:
                        subprocess.run(["xdg-open", str(file_path.parent)], check=True)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        from PyQt6.QtWidgets import QMessageBox

                        QMessageBox.information(
                            self, "File Location", f"File saved at:\n{self.export_path}"
                        )
