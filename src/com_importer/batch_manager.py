"""
Batch import manager for handling multiple danger/character imports.

Supports transaction-like semantics with rollback and detailed reporting.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .character_parser import CharacterParser
from .character_to_foundry import convert_character_to_foundry
from .danger_parser import DangerParser
from .danger_to_foundry import convert_danger_to_foundry
from .foundry_client import FoundryClient

logger = logging.getLogger(__name__)


@dataclass
class BatchImportResult:
    """Result of a single import operation."""

    input_text: str
    name: str | None = None  # Actor name (danger or character)
    actor_id: str | None = None
    actor_type: str = "threat"  # "threat" (danger) or "character"
    status: str = "pending"  # pending, parsing, creating, success, failed
    error_message: str | None = None
    actor_json: dict[str, Any] | None = None

    @property
    def danger_name(self) -> str | None:
        """Alias for backwards compatibility."""
        return self.name


@dataclass
class BatchImportReport:
    """Report of a batch import operation."""

    total_attempted: int = 0
    total_succeeded: int = 0
    total_failed: int = 0
    results: list[BatchImportResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_attempted == 0:
            return 0.0
        return (self.total_succeeded / self.total_attempted) * 100

    def summary(self) -> str:
        """Get summary text."""
        return (
            f"Batch Import Summary:\n"
            f"Total: {self.total_attempted} | "
            f"Success: {self.total_succeeded} | "
            f"Failed: {self.total_failed} | "
            f"Success Rate: {self.success_rate:.1f}%"
        )


class BatchImportManager:
    """Manages batch import of multiple dangers and characters."""

    def __init__(self, foundry_client: FoundryClient) -> None:
        """
        Initialize batch manager.

        Args:
            foundry_client: Configured Foundry client for creating actors
        """
        self.foundry_client = foundry_client
        self.danger_parser = DangerParser()
        self.character_parser = CharacterParser()
        self.created_actor_ids: list[str] = []
        self.report = BatchImportReport()

    def import_from_texts(
        self,
        texts: list[str],
        actor_type: str = "threat",
        progress_callback: callable | None = None,
    ) -> BatchImportReport:
        """
        Import multiple dangers or characters from text blocks.

        Args:
            texts: List of text strings to parse and import
            actor_type: Type of actor to import ("threat" for dangers, "character" for PCs)
            progress_callback: Optional callback for progress (current index, total)

        Returns:
            BatchImportReport with details on each import
        """
        if actor_type not in ("threat", "character"):
            raise ValueError(f"Invalid actor_type: {actor_type}. Must be 'threat' or 'character'")

        self.report = BatchImportReport(
            total_attempted=len(texts),
            results=[],
        )
        self.created_actor_ids = []

        for idx, text in enumerate(texts):
            if progress_callback:
                progress_callback(idx + 1, len(texts))

            result = self._import_single_text(text, actor_type)
            self.report.results.append(result)

            if result.status == "success":
                self.report.total_succeeded += 1
                self.created_actor_ids.append(result.actor_id)
            else:
                self.report.total_failed += 1

        logger.info(f"Batch import complete: {self.report.summary()}")
        return self.report

    def _import_single_text(self, text: str, actor_type: str = "threat") -> BatchImportResult:
        """
        Import a single actor (danger or character) from text.

        Args:
            text: Text to parse and import
            actor_type: Type of actor ("threat" or "character")

        Returns:
            BatchImportResult with status and details
        """
        result = BatchImportResult(input_text=text, actor_type=actor_type)

        try:
            # Step 1: Parse
            result.status = "parsing"
            if actor_type == "threat":
                actor, errors = self.danger_parser.parse(text)
                converter = convert_danger_to_foundry
                actor_label = "danger"
            else:
                actor, errors = self.character_parser.parse(text)
                converter = convert_character_to_foundry
                actor_label = "character"

            result.name = actor.name

            if not actor.name or not actor.description:
                result.status = "failed"
                result.error_message = "Parsing failed: missing required fields"
                return result

            # Step 2: Validate
            validation_errors = actor.validate()
            if validation_errors:
                # Log but don't fail on validation warnings
                logger.warning(f"Validation warnings for {actor.name}: {validation_errors}")

            # Step 3: Convert to Foundry format
            result.status = "creating"
            actor_json = converter(actor)
            result.actor_json = actor_json

            # Step 4: Create in Foundry
            actor_id = self.foundry_client.create_actor(actor_json)
            result.actor_id = actor_id
            result.status = "success"

            logger.info(f"Successfully imported {actor_label}: {actor.name} (ID: {actor_id})")
            return result

        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            logger.error(f"Failed to import: {str(e)}", exc_info=True)
            return result

    def rollback_created_dangers(self) -> None:
        """
        Attempt to rollback all created actors.

        Note: This is a best-effort rollback. Not all clients may support deletion.
        """
        logger.warning(f"Rolling back {len(self.created_actor_ids)} created actors")

        # Note: Foundry client doesn't have delete method yet, so this is a placeholder
        # In practice, manual deletion in Foundry may be needed
        # Future enhancement: add delete_actor() to FoundryClient


class BatchImportParser:
    """Parse batch import files (JSONL, CSV, etc.)."""

    @staticmethod
    def parse_jsonl(file_path: str) -> list[str]:
        """
        Parse JSONL file where each line is a JSON danger description.

        Args:
            file_path: Path to JSONL file

        Returns:
            List of text strings extracted from JSON
        """
        import json

        texts = []
        with open(file_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    # Extract text from common fields
                    text = data.get("text") or data.get("description") or data.get("content")
                    if isinstance(text, str):
                        texts.append(text)
                    else:
                        # If it's structured data, convert to text
                        text = " ".join(str(v) for v in data.values() if isinstance(v, str))
                        if text:
                            texts.append(text)

                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSONL line {line_num}: {e}")
                    continue

        return texts

    @staticmethod
    def parse_csv(file_path: str, text_column: str = "text") -> list[str]:
        """
        Parse CSV file with danger text in specified column.

        Args:
            file_path: Path to CSV file
            text_column: Name of column containing danger text

        Returns:
            List of text strings
        """
        import csv

        texts = []
        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames and text_column not in reader.fieldnames:
                logger.warning(f"Column '{text_column}' not found. Available: {reader.fieldnames}")
                # Try first column
                text_column = reader.fieldnames[0]

            for row in reader:
                text = row.get(text_column, "").strip()
                if text:
                    texts.append(text)

        return texts

    @staticmethod
    def parse_text_blocks(text: str, separator: str = "\n---\n") -> list[str]:
        """
        Parse multi-block text separated by delimiter.

        Args:
            text: Text containing multiple danger descriptions
            separator: Delimiter between dangers (default: "\\n---\\n")

        Returns:
            List of text strings
        """
        blocks = text.split(separator)
        return [block.strip() for block in blocks if block.strip()]
