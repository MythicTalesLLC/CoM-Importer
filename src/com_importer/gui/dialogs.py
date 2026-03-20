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
        self._apply_edits()

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
