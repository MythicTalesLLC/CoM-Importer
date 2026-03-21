# Foundry REST API Integration & Limitations

## Overview

This tool integrates with Foundry VTT via the REST API relay to create City of Mist dangers and characters. However, there is a known limitation with the REST API relay that affects item persistence.

## The REST API Limitation

### What Works ✓
- **Actor Creation**: Actors (threats, characters) are successfully created via the REST API
- **Actor Properties**: Common fields like name, description, biography, mythos, logos are properly persisted
- **Connection Testing**: The API relay correctly tests and validates connections

### What Doesn't Work ✗
- **Item Persistence**: Items (GM moves, spectrums, tags, statuses) are created with valid UUIDs but **do not persist to the Foundry database**
- **Item Parent Linking**: Items created with a `"parent": actor_id` relationship are silently orphaned
- **Batch Item Operations**: Creating multiple items in sequence shows the same non-persistence issue

### Why This Happens

The Foundry REST API relay (`foundryvtt-rest-api-relay`) is designed as a lightweight proxy for use cases like dice rolling and messaging. It does not maintain the full database transaction semantics needed to properly associate items with their parent actors in Foundry.

When you create an item with `"parent": actor_id`, the relay:
1. Accepts the request ✓ (HTTP 200)
2. Returns a valid UUID ✓
3. **Does NOT persist the item to Foundry** ✗

This is confirmed from Foundry's own documentation that hosted Foundry servers (like those on foundryserver.com) have limitations on programmatic modification of database content.

## Workarounds

This tool implements automatic fallback mechanisms to handle this limitation.

### Option 1: Manual JSON Import (DEFAULT)

When items fail to persist via the REST API, the tool automatically exports the complete actor JSON to your Downloads folder.

**Steps:**
1. Tool detects REST API item creation failure
2. Exports properly formatted JSON file: `fvtt-Actor-<Name>-<ID>.json`
3. In your Foundry instance, use the **built-in Import** feature:
   - Go to **Sidebar → Actors** (or whichever actor type)
   - Click the **Import Actors** button
   - Select the exported JSON file
   - All items will be imported with proper parent-child relationships

**Files are saved to:**
- macOS: `~/Downloads/fvtt-Actor-*.json`
- Windows: `C:\Users\<YourUsername>\Downloads\fvtt-Actor-*.json`

### Option 2: Macro-Based Import (Advanced)

You can create a Foundry macro to automate JSON import from a file:

1. In your Foundry instance, go to **Compendiums → Macros**
2. Create a new macro with this code:

```javascript
// JSON Import Helper Macro
// 1. Place a JSON file in Foundry's file system
// 2. Run this macro
// 3. Actor will be created with all items properly linked

async function importActorFromJson() {
    const files = await FilePicker.browse("data", "", {
        extensions: [".json"]
    });

    if (!files.target) {
        ui.notifications.error("No file selected");
        return;
    }

    try {
        const response = await fetch(files.target);
        const actorData = await response.json();
        const items = actorData.items || [];

        // Create actor without items
        const actorDataForCreation = { ...actorData };
        delete actorDataForCreation.items;
        delete actorDataForCreation._id;

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

        ui.notifications.info(`Created "${createdActor.name}" with ${items.length} items`);

    } catch (error) {
        console.error(error);
        ui.notifications.error(`Import failed: ${error.message}`);
    }
}

await importActorFromJson();
```

3. Execute the macro and select your exported JSON file

### Option 3: Local Foundry Installation

If you have a local Foundry installation, the tool can write directly to your world data:

1. In the tool configuration, select **"Local Foundry"** instead of **"Remote API"**
2. Specify your Foundry data directory (typically `~/.foundry/data`)
3. Select your world name
4. Actors with **all items properly linked** will be created directly

This approach completely bypasses the REST API limitation.

## Recommended Solutions

### For Remote Foundry (foundryserver.com)
**Use Option 1 (Automatic JSON Export)** - It's the simplest:
- Tool automatically exports when items fail
- Files appear in Downloads
- Import using Foundry's native import feature
- All items created with proper relationships

### For Local Foundry
**Use the Local Foundry Client** - The tool will:
- Write directly to your world data
- Properly link all items to their parent actors
- No manual import needed

## Troubleshooting

### "Actor created but no items appeared"
- This is the REST API limitation (expected)
- Check your Downloads folder for the exported JSON file
- Use Foundry's **Import** feature to import the full actor with items

### "Export file not found in Downloads"
- Export fallback may be disabled in configuration
- Check the tool's logs for error messages
- You can manually export via the tool's menu: **File → Export Actor as JSON**

### "JSON import shows wrong schema"
- Some City of Mist module versions expect different field names
- Check the module version in your Foundry instance
- Adjust the exported JSON if needed (export path is printed to console)

## Technical Details

### JSON Format
The exported JSON follows Foundry's standard actor format:
```json
{
  "_id": "unique-uuid",
  "name": "Threat Name",
  "type": "threat",
  "img": "icon-path",
  "system": {
    "description": "...",
    "mythos": "[tag-reference]",
    "logos": "[tag-reference]",
    ...
  },
  "items": [
    {
      "_id": "item-uuid",
      "name": "GM Move Name",
      "type": "gmmove",
      "system": {...}
    },
    ...
  ]
}
```

### REST API Endpoints Used
- **Create (Actor)**: `POST /create?clientId={id}`
- **Create (Item)**: `POST /create?clientId={id}` (items don't persist)
- **Test Connection**: `GET /clients`

## Future Solutions

- Monitor Foundry REST API relay updates for item persistence support
- Investigate Socket.io-based real-time updates (if Foundry supports authenticated sockets)
- Consider alternative APIs or approaches as they become available

## Files

- **Export Handler**: `src/com_importer/foundry_export.py`
- **REST Client**: `src/com_importer/foundry_client.py`
- **Fallback Logic**: `src/com_importer/foundry_client.py` (FoundryRestClient.create_actor)

## References

- Foundry REST API Relay: https://github.com/ThreeHats/foundryvtt-rest-api-relay
- Foundry Hosted Server Support: https://www.foundryserver.com/support
- City of Mist Foundry Module: https://github.com/taragnor/city-of-mist
