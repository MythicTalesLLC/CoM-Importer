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
        export_macro: bool = True,
    ) -> str:
        """
        Export actor JSON to a file for manual import.

        This is a workaround for REST API relay limitations that prevent
        proper item persistence. When the macro is exported alongside the JSON,
        users can run the macro to automatically import the complete actor with
        all items.

        Args:
            actor_data: Foundry actor JSON object
            export_dir: Directory to save JSON file (defaults to ~/Downloads)
            export_macro: If True, also export the import macro script

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

        # Write actor JSON file
        with open(filepath, "w") as f:
            json.dump(actor_data, f, indent=2, default=str)

        logger.info(f"Exported actor to {filepath}")

        # Optionally export macro script
        if export_macro:
            macro_code = FoundryJsonExporter.create_import_script()
            macro_filename = "IMPORT_MACRO_CityOfMist.js"
            macro_filepath = export_dir / macro_filename

            with open(macro_filepath, "w") as f:
                f.write(macro_code)

            logger.info(f"Exported import macro to {macro_filepath}")

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
        Generate a production-ready Foundry Macro for importing threat actors with items.

        This macro:
        1. Lets users select a JSON export file
        2. Creates the actor with all system data (description, mythos, logos, etc)
        3. Automatically adds all items (moves, spectrums, tags, statuses)
        4. Provides clear success/error feedback

        Returns:
            Foundry macro code as a string
        """
        macro_code = """
// ============================================================================
// City of Mist Threat Actor Import Macro
// ============================================================================
// This macro automatically imports threat actors with all items from JSON files
// exported by the CoM Importer tool.
//
// Usage:
// 1. Save this as a new Macro in Foundry (Macros compendium)
// 2. Run this macro
// 3. Select the fvtt-Actor-*.json file from your Downloads folder
// 4. Done! Actor created with all items
// ============================================================================

async function importActorFromJson() {
    try {
        // Step 1: Let user select file
        ui.notifications.info("Select the threat JSON file to import...");
        const files = await FilePicker.browse("data", "", {
            extensions: [".json"],
            wildcard: false
        });

        if (!files.target) {
            ui.notifications.warn("Import cancelled - no file selected");
            return;
        }

        const fileName = files.target.split('/').pop();
        ui.notifications.info(`Loading [${fileName}]...`);

        // Step 2: Read and parse JSON file
        const response = await fetch(files.target);
        if (!response.ok) {
            throw new Error(`Failed to read file: ${response.statusText}`);
        }

        const actorData = await response.json();
        const actorName = actorData.name || "Unknown Threat";
        const items = actorData.items || [];

        // Validate required fields
        if (!actorData.name || !actorData.type) {
            throw new Error("Invalid actor data: missing name or type field");
        }

        // Step 3: Prepare actor data (remove embedded items and ID for fresh creation)
        const actorDataForCreation = { ...actorData };
        delete actorDataForCreation.items;
        delete actorDataForCreation._id;

        ui.notifications.info(`Creating actor: ${actorName}...`);

        // Step 4: Create the actor
        const createdActor = await Actor.create(actorDataForCreation);

        if (!createdActor) {
            throw new Error("Failed to create actor in Foundry");
        }

        ui.notifications.info(`Adding ${items.length} items to ${actorName}...`);

        // Step 5: Add items to the actor
        let itemCount = 0;
        for (const item of items) {
            try {
                const itemData = { ...item };
                delete itemData._id; // Let Foundry generate new IDs
                await createdActor.createEmbeddedDocuments("Item", [itemData]);
                itemCount++;
            } catch (itemError) {
                console.warn(`Failed to add item "${item.name}":`, itemError);
                // Continue with other items even if one fails
            }
        }

        // Step 6: Success notification
        let message;
        if (itemCount === items.length) {
            message = `✓ Created "${actorName}" with all ${items.length} items`;
        } else {
            const failedCount = items.length - itemCount;
            message = `⚠ Created "${actorName}" with ${itemCount}/${items.length} items`
                + ` (${failedCount} failed)`;
        }

        ui.notifications.info(message);
        console.log(`[CoM Import] ${message}`);

    } catch (error) {
        console.error("[CoM Import Error]", error);
        ui.notifications.error(`Import failed: ${error.message}`);
    }
}

// Execute the import
await importActorFromJson();
"""
        return macro_code.strip()
