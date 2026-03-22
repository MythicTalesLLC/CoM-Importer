"""Dialog components for the CoM Importer GUI."""

from __future__ import annotations

import json
import logging

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
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
from ..com_schema import (
    CharacterActor,
    DangerActor,
    DangerStatus,
    GMMove,
    MoveType,
    Spectrum,
    Tag,
)
from ..danger_to_foundry import convert_danger_to_foundry

logger = logging.getLogger(__name__)


class EditActorDialog(QDialog):
    """Dialog for reviewing and editing parsed danger or character actors before creation."""

    _MOVE_TYPES = ["soft", "hard", "custom"]

    def __init__(self, actor: DangerActor | CharacterActor, parent=None):
        """Initialize edit dialog."""
        super().__init__(parent)
        self.actor = actor
        self.is_character = isinstance(actor, CharacterActor)
        self.setWindowTitle("Edit Character" if self.is_character else "Edit Danger")
        self.resize(1020, 720)
        self._create_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _create_ui(self) -> None:
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._create_basic_tab(), "Basic Info")

        if self.is_character:
            tabs.addTab(self._create_character_tab(), "Character Details")
        else:
            tabs.addTab(self._create_danger_details_tab(), "Danger Details")
            tabs.addTab(self._create_spectrums_tab(), "Spectrums")
            tabs.addTab(self._create_moves_tab(), "GM Moves")
            tabs.addTab(self._create_tags_statuses_tab(), "Tags & Statuses")

        tabs.addTab(self._create_preview_tab(), "JSON Preview")
        layout.addWidget(tabs)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _create_basic_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit(self.actor.name)
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Description:"))
        self.description_input = QPlainTextEdit(self.actor.description)
        self.description_input.setMaximumHeight(150)
        self._bump_font(self.description_input)
        layout.addWidget(self.description_input)

        layout.addWidget(QLabel("Biography (optional):"))
        self.biography_input = QPlainTextEdit(self.actor.biography)
        self.biography_input.setMaximumHeight(100)
        self._bump_font(self.biography_input)
        layout.addWidget(self.biography_input)

        layout.addWidget(QLabel("GM Notes (optional):"))
        self.gmnotes_input = QPlainTextEdit(self.actor.gmnotes)
        self.gmnotes_input.setMaximumHeight(100)
        self._bump_font(self.gmnotes_input)
        layout.addWidget(self.gmnotes_input)

        layout.addStretch()
        return widget

    def _create_danger_details_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        danger: DangerActor = self.actor  # type: ignore[assignment]

        layout.addWidget(QLabel("Danger Rating (e.g. 3, or +2 for Mythos Power Set):"))
        row = QHBoxLayout()
        self.rating_input = QLineEdit(danger.danger_rating or "")
        row.addWidget(self.rating_input)
        row.addStretch()
        layout.addLayout(row)

        layout.addWidget(QLabel("Mythos identity:"))
        self.mythos_input = QPlainTextEdit(danger.mythos)
        self.mythos_input.setMaximumHeight(70)
        layout.addWidget(self.mythos_input)

        layout.addWidget(QLabel("Logos identity:"))
        self.logos_input = QPlainTextEdit(danger.logos)
        self.logos_input.setMaximumHeight(70)
        layout.addWidget(self.logos_input)

        layout.addWidget(QLabel("Collective / Vehicle / Team note:"))
        self.collective_note_input = QLineEdit(danger.collective_note)
        layout.addWidget(self.collective_note_input)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Collective size factor (0 = not a collective):"))
        self.collective_size_input = QSpinBox()
        self.collective_size_input.setRange(0, 99)
        self.collective_size_input.setValue(danger.collective_size)
        row2.addWidget(self.collective_size_input)
        row2.addStretch()
        layout.addLayout(row2)

        self.mythos_power_set_check = QCheckBox(
            "Mythos Power Set (+★ additive rating, no spectrum)"
        )
        self.mythos_power_set_check.setChecked(danger.is_mythos_power_set)
        layout.addWidget(self.mythos_power_set_check)

        layout.addStretch()
        return widget

    def _create_spectrums_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        danger: DangerActor = self.actor  # type: ignore[assignment]

        layout.addWidget(
            QLabel('Spectrums (Max Tier: enter a number, or "-" for immune/unlimited):')
        )

        self.spectrums_table = QTableWidget()
        self.spectrums_table.setColumnCount(2)
        self.spectrums_table.setHorizontalHeaderLabels(["Name", "Max Tier"])
        self.spectrums_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.spectrums_table.setColumnWidth(1, 90)

        for sp in danger.spectrums:
            self._append_spectrum_row(sp.name, str(sp.max_tier) if sp.max_tier is not None else "-")

        layout.addWidget(self.spectrums_table)
        layout.addLayout(self._row_buttons(self.spectrums_table, self._add_spectrum_row))
        layout.addStretch()
        return widget

    def _create_moves_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        danger: DangerActor = self.actor  # type: ignore[assignment]

        layout.addWidget(QLabel("GM Moves (Type: soft / hard / custom):"))

        self.moves_table = QTableWidget()
        self.moves_table.setColumnCount(3)
        self.moves_table.setHorizontalHeaderLabels(["Name", "Type", "Description"])
        self.moves_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.moves_table.setColumnWidth(0, 160)
        self.moves_table.setColumnWidth(1, 80)

        for move in danger.gm_moves:
            self._append_move_row(move.name, move.move_type.value, move.description)

        layout.addWidget(self.moves_table)
        layout.addLayout(self._row_buttons(self.moves_table, self._add_move_row))
        layout.addStretch()
        return widget

    def _create_tags_statuses_tab(self) -> QWidget:
        widget = QWidget()
        outer = QHBoxLayout(widget)

        # Tags side
        tags_widget = QWidget()
        tags_layout = QVBoxLayout(tags_widget)
        danger: DangerActor = self.actor  # type: ignore[assignment]

        tags_layout.addWidget(QLabel("Story / Power Tags:"))
        self.tags_table = QTableWidget()
        self.tags_table.setColumnCount(2)
        self.tags_table.setHorizontalHeaderLabels(["Name", "Type"])
        self.tags_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tags_table.setColumnWidth(1, 80)
        for tag in danger.tags:
            self._append_tag_row(tag.name, tag.tag_type.value)
        tags_layout.addWidget(self.tags_table)
        tags_layout.addLayout(self._row_buttons(self.tags_table, self._add_tag_row))
        outer.addWidget(tags_widget)

        # Statuses side
        statuses_widget = QWidget()
        statuses_layout = QVBoxLayout(statuses_widget)
        statuses_layout.addWidget(QLabel("Statuses (e.g. fried-3, legal-trouble-2):"))
        self.statuses_table = QTableWidget()
        self.statuses_table.setColumnCount(2)
        self.statuses_table.setHorizontalHeaderLabels(["Name", "Tier"])
        self.statuses_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.statuses_table.setColumnWidth(1, 50)
        for status in danger.statuses:
            self._append_status_row(status.name, str(status.tier))
        statuses_layout.addWidget(self.statuses_table)
        statuses_layout.addLayout(self._row_buttons(self.statuses_table, self._add_status_row))
        outer.addWidget(statuses_widget)

        return widget

    def _create_character_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        character: CharacterActor = self.actor  # type: ignore[assignment]

        layout.addWidget(QLabel("Pronouns (optional):"))
        self.pronouns_input = QLineEdit(character.pronouns)
        layout.addWidget(self.pronouns_input)

        row = QHBoxLayout()
        row.addWidget(QLabel("Juice – Help:"))
        self.juice_help_input = QSpinBox()
        self.juice_help_input.setRange(0, 9)
        self.juice_help_input.setValue(character.juice_help)
        row.addWidget(self.juice_help_input)
        row.addSpacing(20)
        row.addWidget(QLabel("Juice – Hurt:"))
        self.juice_hurt_input = QSpinBox()
        self.juice_hurt_input.setRange(0, 9)
        self.juice_hurt_input.setValue(character.juice_hurt)
        row.addWidget(self.juice_hurt_input)
        row.addStretch()
        layout.addLayout(row)

        layout.addWidget(QLabel(f"Themes: {len(character.themes)} (edit in JSON Preview tab)"))
        layout.addStretch()
        return widget

    def _create_preview_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Foundry Actor JSON (read-only — click Refresh to update):"))
        self.preview_text = QPlainTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(self._mono_font())
        layout.addWidget(self.preview_text)
        refresh_btn = QPushButton("↻  Refresh Preview")
        refresh_btn.clicked.connect(self._update_preview)
        layout.addWidget(refresh_btn)
        self._update_preview()
        return widget

    # ------------------------------------------------------------------
    # Table helpers
    # ------------------------------------------------------------------

    def _row_buttons(self, table: QTableWidget, add_fn) -> QHBoxLayout:
        """Return a row of Add / Remove / Move-Up / Move-Down buttons bound to *table*."""
        row = QHBoxLayout()

        add_btn = QPushButton("+ Add Row")
        add_btn.clicked.connect(add_fn)
        row.addWidget(add_btn)

        remove_btn = QPushButton("− Remove Selected")

        def _remove():
            selected = table.selectedItems()
            rows = sorted({item.row() for item in selected}, reverse=True)
            for r in rows:
                table.removeRow(r)
            if not rows and table.rowCount() > 0:
                table.removeRow(table.rowCount() - 1)

        remove_btn.clicked.connect(_remove)
        row.addWidget(remove_btn)

        row.addSpacing(12)

        up_btn = QPushButton("↑ Move Up")
        up_btn.setToolTip("Move selected row up")

        def _move_up():
            selected = table.selectedItems()
            if not selected:
                return
            r = selected[0].row()
            if r > 0:
                self._swap_row_content(table, r, r - 1)
                table.selectRow(r - 1)

        up_btn.clicked.connect(_move_up)
        row.addWidget(up_btn)

        down_btn = QPushButton("↓ Move Down")
        down_btn.setToolTip("Move selected row down")

        def _move_down():
            selected = table.selectedItems()
            if not selected:
                return
            r = selected[0].row()
            if r < table.rowCount() - 1:
                self._swap_row_content(table, r, r + 1)
                table.selectRow(r + 1)

        down_btn.clicked.connect(_move_down)
        row.addWidget(down_btn)

        row.addStretch()
        return row

    @staticmethod
    def _swap_row_content(table: QTableWidget, row_a: int, row_b: int) -> None:
        """Swap the visible content of two rows in *table*.

        Handles both plain QTableWidgetItem cells and embedded cell widgets
        (e.g. the QComboBox in the moves table).  For widgets only the
        *current-index / selected-text* is swapped so the widgets themselves
        stay in place (Qt does not support moving live cell widgets).
        """
        for col in range(table.columnCount()):
            widget_a = table.cellWidget(row_a, col)
            widget_b = table.cellWidget(row_b, col)

            if isinstance(widget_a, QComboBox) and isinstance(widget_b, QComboBox):
                # Swap combo selections by index
                idx_a = widget_a.currentIndex()
                widget_a.setCurrentIndex(widget_b.currentIndex())
                widget_b.setCurrentIndex(idx_a)
            elif widget_a is None and widget_b is None:
                # Plain text items — swap text
                item_a = table.item(row_a, col)
                item_b = table.item(row_b, col)
                text_a = item_a.text() if item_a else ""
                text_b = item_b.text() if item_b else ""
                table.setItem(row_a, col, QTableWidgetItem(text_b))
                table.setItem(row_b, col, QTableWidgetItem(text_a))
            # Mixed (one widget, one item): leave as-is to avoid corruption

    def _append_spectrum_row(self, name: str = "", max_tier: str = "4") -> None:
        row = self.spectrums_table.rowCount()
        self.spectrums_table.insertRow(row)
        self.spectrums_table.setItem(row, 0, QTableWidgetItem(name))
        self.spectrums_table.setItem(row, 1, QTableWidgetItem(max_tier))

    def _add_spectrum_row(self) -> None:
        self._append_spectrum_row()

    def _append_move_row(self, name: str = "", move_type: str = "soft", desc: str = "") -> None:
        row = self.moves_table.rowCount()
        self.moves_table.insertRow(row)
        self.moves_table.setItem(row, 0, QTableWidgetItem(name))
        combo = QComboBox()
        combo.addItems(self._MOVE_TYPES)
        idx = self._MOVE_TYPES.index(move_type) if move_type in self._MOVE_TYPES else 0
        combo.setCurrentIndex(idx)
        self.moves_table.setCellWidget(row, 1, combo)
        self.moves_table.setItem(row, 2, QTableWidgetItem(desc))

    def _add_move_row(self) -> None:
        self._append_move_row()

    def _append_tag_row(self, name: str = "", tag_type: str = "story") -> None:
        row = self.tags_table.rowCount()
        self.tags_table.insertRow(row)
        self.tags_table.setItem(row, 0, QTableWidgetItem(name))
        self.tags_table.setItem(row, 1, QTableWidgetItem(tag_type))

    def _add_tag_row(self) -> None:
        self._append_tag_row()

    def _append_status_row(self, name: str = "", tier: str = "0") -> None:
        row = self.statuses_table.rowCount()
        self.statuses_table.insertRow(row)
        self.statuses_table.setItem(row, 0, QTableWidgetItem(name))
        self.statuses_table.setItem(row, 1, QTableWidgetItem(tier))

    def _add_status_row(self) -> None:
        self._append_status_row()

    # ------------------------------------------------------------------
    # Apply / preview / save
    # ------------------------------------------------------------------

    def _update_preview(self) -> None:
        self._apply_edits()
        try:
            if self.is_character:
                actor_json = convert_character_to_foundry(self.actor)
            else:
                actor_json = convert_danger_to_foundry(self.actor)
            self.preview_text.setPlainText(json.dumps(actor_json, indent=2))
        except Exception as e:
            self.preview_text.setPlainText(f"Error generating JSON:\n{e}")
            logger.exception("Error generating preview JSON")

    def _apply_edits(self) -> None:
        """Write all UI values back into self.actor."""
        self.actor.name = self.name_input.text().strip()
        self.actor.description = self.description_input.toPlainText().strip()
        self.actor.biography = self.biography_input.toPlainText().strip()
        self.actor.gmnotes = self.gmnotes_input.toPlainText().strip()

        if self.is_character:
            ch: CharacterActor = self.actor  # type: ignore[assignment]
            ch.pronouns = self.pronouns_input.text().strip()
            ch.juice_help = self.juice_help_input.value()
            ch.juice_hurt = self.juice_hurt_input.value()
        else:
            d: DangerActor = self.actor  # type: ignore[assignment]
            d.danger_rating = self.rating_input.text().strip() or None
            d.mythos = self.mythos_input.toPlainText().strip()
            d.logos = self.logos_input.toPlainText().strip()
            d.collective_note = self.collective_note_input.text().strip()
            d.collective_size = self.collective_size_input.value()
            d.is_mythos_power_set = self.mythos_power_set_check.isChecked()

            # Spectrums
            d.spectrums = []
            for row in range(self.spectrums_table.rowCount()):
                name_item = self.spectrums_table.item(row, 0)
                max_item = self.spectrums_table.item(row, 1)
                if name_item and name_item.text().strip():
                    raw_max = max_item.text().strip() if max_item else "4"
                    max_tier: int | None = None if raw_max == "-" else int(raw_max or "4")
                    d.spectrums.append(Spectrum(name=name_item.text().strip(), max_tier=max_tier))

            # GM Moves
            d.gm_moves = []
            for row in range(self.moves_table.rowCount()):
                name_item = self.moves_table.item(row, 0)
                type_widget = self.moves_table.cellWidget(row, 1)
                desc_item = self.moves_table.item(row, 2)
                if name_item and name_item.text().strip():
                    move_type_str = type_widget.currentText() if type_widget else "soft"
                    move_type = MoveType(move_type_str)
                    desc = desc_item.text().strip() if desc_item else ""
                    d.gm_moves.append(
                        GMMove(
                            name=name_item.text().strip(),
                            description=desc,
                            move_type=move_type,
                        )
                    )

            # Tags
            d.tags = []
            for row in range(self.tags_table.rowCount()):
                name_item = self.tags_table.item(row, 0)
                type_item = self.tags_table.item(row, 1)
                if name_item and name_item.text().strip():
                    from ..com_schema import TagType

                    tag_type_str = type_item.text().strip() if type_item else "story"
                    try:
                        tag_type = TagType(tag_type_str)
                    except ValueError:
                        tag_type = TagType.STORY
                    d.tags.append(Tag(name=name_item.text().strip(), tag_type=tag_type))

            # Statuses
            d.statuses = []
            for row in range(self.statuses_table.rowCount()):
                name_item = self.statuses_table.item(row, 0)
                tier_item = self.statuses_table.item(row, 1)
                if name_item and name_item.text().strip():
                    tier = int(tier_item.text().strip() or "0") if tier_item else 0
                    d.statuses.append(DangerStatus(name=name_item.text().strip(), tier=tier))

    def _on_save(self) -> None:
        self._apply_edits()
        errors = self.actor.validate()
        if errors:
            QMessageBox.warning(
                self,
                "Validation Errors",
                "Please fix the following issues:\n\n" + "\n".join(errors),
            )
            return
        self.accept()

    def get_actor(self) -> DangerActor | CharacterActor:
        """Return the (possibly edited) actor."""
        return self.actor

    @staticmethod
    def _mono_font():
        from PyQt6.QtGui import QFont

        font = QFont("Menlo")
        if not font.exactMatch():
            font = QFont("Courier New")
        font.setPointSize(10)
        return font

    @staticmethod
    def _bump_font(widget, delta: int = 2) -> None:
        """Increase widget font size by delta points above the application default."""
        from PyQt6.QtWidgets import QApplication

        font = widget.font()
        base = QApplication.font().pointSize()
        base = base if base > 0 else 13
        font.setPointSize(base + delta)
        widget.setFont(font)


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
        title = QLabel("✓ Export Complete - Ready for Foundry Import")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2e7d32;")
        layout.addWidget(title)

        # Explanation
        explanation = QPlainTextEdit()
        explanation.setReadOnly(True)
        explanation.setPlainText(
            f"""EXPORT COMPLETE:
Your actor has been successfully processed and exported with all items.

ACTOR: {self.actor_name}
ITEMS: {self.items_count} (moves, spectrums, tags)
FILE: {self.export_path}

NEXT: Use the macro to import into Foundry (see instructions below)."""
        )
        explanation.setStyleSheet(
            "background-color: #f5f5f5; padding: 10px; border: 1px solid #ddd; border-radius: 4px;"
        )
        layout.addWidget(explanation)

        # Next steps
        steps_label = QLabel("IMPORT INTO FOUNDRY (2 Steps via Macro):")
        steps_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
        layout.addWidget(steps_label)

        steps = QPlainTextEdit()
        steps.setReadOnly(True)
        filename = self.export_path.split("/")[-1]
        steps.setPlainText(
            f"""STEP 1: Set up the Import Macro (one-time)
  • Open your Foundry instance
  • Go to Macros → New Macro
  • Paste the contents of: IMPORT_MACRO_CityOfMist.js (in Downloads)
  • Save the macro (name: "Import City of Mist Actor")
  • Close the macro editor

STEP 2: Import Your Threat Actor (repeat for each)
  • Run the macro you just created
  • The macro will open a text box
  • Copy the contents of: {filename}
  • Paste into the dialog box
  • Click "Import Actor"
  • Done! ✓

Result:
  ✓ Actor created
  ✓ All {self.items_count} items added (moves, spectrums, tags)
  ✓ Full relationships intact"""
        )
        steps.setStyleSheet(
            "background-color: #e3f2fd; padding: 10px; border: 1px solid #2196f3;"
            " border-radius: 4px;"
        )
        layout.addWidget(steps)

        # Buttons
        button_layout = QHBoxLayout()

        copy_json_btn = QPushButton("Copy JSON Content")
        copy_json_btn.clicked.connect(self._copy_json_to_clipboard)
        button_layout.addWidget(copy_json_btn)

        open_btn = QPushButton("Open File Location")
        open_btn.clicked.connect(self._open_file_location)
        button_layout.addWidget(open_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _copy_json_to_clipboard(self) -> None:
        """Copy JSON content to clipboard for pasting into Foundry macro."""
        from PyQt6.QtGui import QClipboard
        from PyQt6.QtWidgets import QApplication

        try:
            with open(self.export_path) as f:
                json_content = f.read()

            cb = QApplication.clipboard()
            cb.setText(json_content, QClipboard.Mode.Clipboard)

            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                "Copied",
                "JSON content copied to clipboard!\n\n"
                "Now paste it into the macro dialog in Foundry.",
            )
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Error", f"Failed to copy JSON content:\n{str(e)}")

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
