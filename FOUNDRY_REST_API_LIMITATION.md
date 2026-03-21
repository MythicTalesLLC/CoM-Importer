# Foundry REST API Integration & Limitations

## Overview

This tool integrates with Foundry VTT via the REST API relay to create City of Mist dangers and characters. However, there is a known limitation with the REST API relay that affects item persistence.

Due to how Foundry's import system works (only updating actor fields, not embedded items), we've implemented a **macro-based import solution** that is fully automated and requires no manual steps beyond the initial macro setup.

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

Additionally, Foundry's "Import Data" feature only updates actor system fields—it does **not** import embedded items.

## The Solution: Macro-Based Automatic Import

When REST API items fail to persist, the tool automatically:

1. **Exports the complete threat actor as JSON** (including all items)
2. **Exports an import macro** that handles everything automatically
3. **Shows the user clear setup and import instructions**

### Setup (One-Time, 2 minutes)

1. In your Foundry instance, go to **Macros compendium**
2. Create a **new macro**
3. Copy the contents of: `IMPORT_MACRO_CityOfMist.js` (saved in Downloads alongside JSON files)
4. Save the macro
5. Done! ✓

### Import (Repeats for each threat, 30 seconds)

1. Run the macro you created
2. Select the threat JSON file (`fvtt-Actor-*.json`)
3. Done! ✓

**Result:**
- ✅ Actor created with complete system data
- ✅ All items added (GM moves, spectrums, tags, statuses) with full relationships
- ✅ No manual item creation needed
- ✅ Fully integrated actor ready to use

## How the Macro Works

The macro (`IMPORT_MACRO_CityOfMist.js`) automatically:

1. **Presents a file picker** - User selects the JSON export
2. **Creates the actor** - Full actor with name, description, mythos, logos, etc.
3. **Adds all items** - Programmatically creates each GM move, spectrum, tag, status
4. **Provides feedback** - Shows success/failure notifications with item counts
5. **Handles errors gracefully** - If an item fails, continues with others and reports status

### Example Macro Output

```
[Info] Loading [fvtt-Actor-DANGEROUS_HACKER-0579c09d.json]...
[Info] Creating actor: DANGEROUS HACKER...
[Info] Adding 16 items to DANGEROUS HACKER...
[Success] ✓ Created "DANGEROUS HACKER" with all 16 items
```

## Files You'll See

When the tool exports a threat that fails REST API item creation:

```
~/Downloads/
├── fvtt-Actor-DANGEROUS_HACKER-0579c09d.json  ← JSON export with all items
└── IMPORT_MACRO_CityOfMist.js                 ← Copy-paste into Foundry (one-time)
```

**IMPORT_MACRO_CityOfMist.js** is created **only once** - subsequent exports just create new JSON files. The macro is reusable for all threats.

## Why This Approach is Superior

✅ **Fully Automated** - No manual item creation, no clicking through menus repeatedly
✅ **100% Complete** - All items created with proper parent-child relationships
✅ **No Server Access Needed** - Uses only Foundry's built-in macro system
✅ **Works Every Time** - Macro handles the logic, user just selects file
✅ **Scalable** - Same macro works for single threats or batch imports
✅ **Reliable** - Macro runs client-side in Foundry, no network limitations

## Fallback Option: Manual Import (Legacy)

If you prefer not to use the macro, you can still manually import:

1. Create actor manually in Foundry (right-click Actors → Create Actor)
2. Go to actor sheet → "Import Data"
3. Select the JSON file
4. Actor data updates (system fields only)
5. **Note:** Items will NOT import via this method

This is why the macro is recommended - it handles the items that the import dialog cannot.

## Troubleshooting

### "Macro not found"
- Make sure you saved the macro after pasting the code
- Check that you're in the correct compendium or using the right hotkey

### "File not found"
- Verify the JSON file is in the Downloads folder
- Check the exact filename matches

### "Some items failed to import"
- The macro reports which items succeeded/failed
- Check browser console (F12) for details
- Most common cause: item schema mismatch (rare)

### "Module error when running macro"
- This means City of Mist module is not enabled
- Enable it in World Settings → Modules
- Restart world and try again

## Files

- **Export Handler**: `src/com_importer/foundry_export.py`
- **REST Client**: `src/com_importer/foundry_client.py`
- **Export Logic**: Both files handle fallback detection and export
- **Macro Script**: Generated during export as `IMPORT_MACRO_CityOfMist.js`

## References

- Foundry REST API Relay: https://github.com/ThreeHats/foundryvtt-rest-api-relay
- Foundry Macro Documentation: https://foundryvtt.com/article/macros/
- City of Mist Foundry Module: https://github.com/taragnor/city-of-mist
- City of Mist Official: https://www.cityofmistrpg.com/
