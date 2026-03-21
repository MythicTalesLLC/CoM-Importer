"""
JSON export mechanism for manual Foundry import as a workaround for REST API limitations.

The REST API relay has limitations with item persistence. This module provides
a fallback export mechanism that generates properly formatted JSON files that
users can manually import into their Foundry instance.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FoundryJsonExporter:
    """Exports Foundry actor JSON for manual import as a workaround."""

    @staticmethod
    def export_actor_to_file(
        actor_data: dict[str, Any],
        export_dir: Path | str | None = None,
    ) -> str:
        """
        Export actor JSON to a file for manual import.

        This is a workaround for REST API relay limitations that prevent
        proper item persistence. Users can download this file and import
        it manually into their Foundry instance.

        Args:
            actor_data: Foundry actor JSON object
            export_dir: Directory to save JSON file (defaults to ~/Downloads)

        Returns:
            Path to the exported JSON file
        """
        if export_dir is None:
            export_dir = Path.home() / "Downloads"
        else:
            export_dir = Path(export_dir)

        export_dir.mkdir(parents=True, exist_ok=True)

        # Create filename from actor name and ID
        actor_name = actor_data.get("name", "Actor").replace(" ", "_")
        actor_id = actor_data.get("_id", "unknown")[:8]
        filename = f"fvtt-Actor-{actor_name}-{actor_id}.json"
        filepath = export_dir / filename

        # Write JSON file
        with open(filepath, "w") as f:
            json.dump(actor_data, f, indent=2, default=str)

        logger.info(f"Exported actor to {filepath}")
        return str(filepath)

    @staticmethod
    def export_batch_to_jsonl(
        actors_data: list[dict[str, Any]],
        export_dir: Path | str | None = None,
    ) -> str:
        """
        Export multiple actors to JSONL format for batch import.

        Args:
            actors_data: List of Foundry actor JSON objects
            export_dir: Directory to save JSONL file (defaults to ~/Downloads)

        Returns:
            Path to the exported JSONL file
        """
        if export_dir is None:
            export_dir = Path.home() / "Downloads"
        else:
            export_dir = Path(export_dir)

        export_dir.mkdir(parents=True, exist_ok=True)

        filename = "foundry_actors_batch.jsonl"
        filepath = export_dir / filename

        # Write JSONL (one JSON object per line)
        with open(filepath, "w") as f:
            for actor in actors_data:
                f.write(json.dumps(actor, default=str) + "\n")

        logger.info(f"Exported {len(actors_data)} actors to {filepath}")
        return str(filepath)

    @staticmethod
    def create_import_script() -> str:
        """
        Generate a Macro script that users can run in Foundry to import JSON files.

        Returns:
            Foundry macro code as a string
        """
        macro_code = """
// JSON Import Helper Macro
// 1. Place a JSON file in your Downloads folder (e.g., fvtt-Actor-MyThreat-abc123.json)
// 2. Run this macro
// 3. Select the JSON file when prompted
// 4. Actor will be created with all items properly linked

async function importActorFromJson() {
    // Use native Foundry file picker
    const files = await FilePicker.browse("data", "", {
        extensions: [".json"]
    });

    if (!files.target) {
        ui.notifications.error("No file selected");
        return;
    }

    try {
        // Read the JSON file
        const response = await fetch(files.target);
        const actorData = await response.json();

        // Extract items before creating actor
        const items = actorData.items || [];
        const actorDataForCreation = { ...actorData };
        delete actorDataForCreation.items;
        delete actorDataForCreation._id;

        // Create the actor
        const createdActor = await Actor.create(actorDataForCreation);

        if (!createdActor) {
            ui.notifications.error("Failed to create actor");
            return;
        }

        // Add items to the actor
        for (const item of items) {
            const itemData = { ...item };
            delete itemData._id;
            await createdActor.createEmbeddedDocuments("Item", [itemData]);
        }

        ui.notifications.info(`Created actor "${createdActor.name}" with ${items.length} items`);

    } catch (error) {
        console.error(error);
        ui.notifications.error(`Import failed: ${error.message}`);
    }
}

await importActorFromJson();
"""
        return macro_code.strip()
