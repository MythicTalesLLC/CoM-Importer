# City of Mist Foundry Importer - Implementation Progress Report

**Date:** March 20, 2026 (Updated)
**Status:** Core Functionality Complete - History Persistence Implemented

## ✅ COMPLETED COMPONENTS

### Phase 1: Core Infrastructure (COMPLETE)

#### 1.1 Schema Definition (`com_schema.py`)
- ✅ `DangerActor` - Threat/danger actor with all fields
- ✅ `CharacterActor` - Player character actor
- ✅ `GMMove` - GM moves with types (soft, hard, custom, intrusion, etc.)
- ✅ `Spectrum` - Status spectrum with tier/pips tracking
- ✅ `Tag` - Actor tags (power, story, weakness, loadout, relationship)
- ✅ `DangerStatus` - Status conditions with categories
- ✅ Foundry JSON conversion methods for all types
- ✅ Built-in validation methods

**Key Methods:**
- `DangerActor.to_foundry_actor()` → complete Foundry actor JSON
- `DangerActor.validate()` → field validation with error messages
- All item types have `to_foundry_item()` methods

#### 1.2 Foundry API Clients (`foundry_client.py`)
- ✅ `FoundryRestClient` - Remote REST API support
  - `create_actor()`, `update_actor()`, `add_item_to_actor()`
  - Bearer token authentication
  - Error handling with user feedback
  - Connection testing with `test_connection()`

- ✅ `FoundryLocalClient` - Local filesystem support
  - Direct actor JSON file creation/updates
  - World detection and validation
  - Duplicate name prevention
  - Same interface as REST client for interchangeability

- ✅ `FoundryClientFactory` - Factory pattern for client selection

#### 1.3 Danger Parser (`danger_parser.py`)
- ✅ `DangerParser` class with `parse(text) → (DangerActor, errors)` method
- ✅ Text extraction for:
  - Name and danger rating
  - Mythos and logos descriptions
  - Spectrums (handles "Name: current/max" format)
  - GM moves (hard, soft, custom, intrusion)
  - Tags (with heuristic type inference)
  - Statuses

- ✅ Error reporting system (`ParsingError` dataclass)
- ✅ Graceful handling of partial/missing sections
- ✅ Tag extraction from [bracketed] text

#### 1.4 Text Normalization (`danger_transform.py`)
- ✅ `normalize_danger_text()` - OCR artifact removal, line break handling
- ✅ `extract_sections()` - Break text into structured sections
- ✅ `clean_field_value()` - Field-specific cleaning
- ✅ Unicode issue fixes (fancy quotes, dashes, etc.)

#### 1.5 Foundry Conversion (`danger_to_foundry.py`)
- ✅ `DangerToActorConverter` class
- ✅ Bracket syntax parsing: `[tag-name]` and `[status-3]`
- ✅ Auto-creation of tags/statuses from moves
- ✅ Duplicate prevention
- ✅ Auto-ID generation (UUID)
- ✅ HTML field sanitization
- ✅ `convert_danger_to_foundry()` convenience function

### Phase 3: GUI Components (PARTIAL)

#### 3.1 Main Window (`gui/main_window.py`)
- ✅ `ComImporterWindow` QMainWindow
- ✅ Tab-based interface with 4 tabs:
  1. Single Import
  2. Batch Import
  3. Configuration
  4. History
- ✅ Menu bar (File, Edit, Help)
- ✅ Signal/slot connections between tabs

#### 3.2 Single Import Tab (`gui/tabs/single_import_tab.py`)
- ✅ Input type selector (Text, Image, PDF)
- ✅ Text paste interface with QPlainTextEdit
- ✅ Parse button with DangerParser integration
- ✅ Live parsing with preview panel
- ✅ Structured display: name, rating, mythos, logos, move/spectrum/tag counts
- ✅ Parsing error/warning display
- ✅ "Create in Foundry" button
- ✅ "Preview JSON" button
- ✅ Draft saving placeholder
- ✅ Config change notification

#### 3.3 Configuration Tab (`gui/tabs/config_tab.py`)
- ✅ Remote API connection settings
- ✅ API URL, Key, Client ID fields
- ✅ Password masking for API key
- ✅ Test connection button with feedback
- ✅ Connection status storage
- ✅ Signal emit on config change

#### 3.4 Batch Import Tab (`gui/tabs/batch_import_tab.py`)
- ✅ Tab placeholder with UI structure

#### 3.5 History Tab (`gui/tabs/history_tab.py`)
- ✅ Complete history tracking and display
- ✅ SQLite database persistence
- ✅ Table view with sortable columns (Name, Rating, Source, Date, Status)
- ✅ JSON preview panel for selected entry
- ✅ Refresh history button
- ✅ Export to CSV and JSON functions
- ✅ Clear history with confirmation
- ✅ Statistics display (total, success, failed, by source)
- ✅ Integration with SingleImportTab

### Utilities & Configuration

#### `gui_main.py`
- ✅ Application entry point
- ✅ PyQt6 QApplication setup
- ✅ Application metadata configuration
- ✅ Window display and main loop

#### `pyproject.toml`
- ✅ Project metadata updated
- ✅ Dependencies added:
  - PyQt6 >= 6.6.0
  - requests >= 2.31.0
  - pytesseract >= 0.3.10
  - pdf2image >= 1.16.3
  - Pillow >= 10.0.0
  - numpy >= 1.24.0
- ✅ Optional dependencies:
  - pytest-qt >= 4.2.0 (dev)
  - google-cloud-vision >= 3.4.0 (vision extra)
- ✅ Script entry points:
  - `com-importer` (CLI)
  - `com-importer-gui` (GUI)

### Phase 4: History & Persistence (`history_manager.py`) (COMPLETE)

- ✅ `HistoryManager` class with SQLite backend
- ✅ `HistoryEntry` dataclass for storing danger metadata
- ✅ **Core Methods:**
  - `add_entry()` - Add new entry with auto-timestamp
  - `get_entry(actor_id)` - Retrieve single entry
  - `get_recent(limit)` - Fetch most recent N entries
  - `get_by_status(status)` - Filter by success/failed
  - `get_by_source(source)` - Filter by input type (text/image/pdf/batch)
  - `get_all()` - Retrieve complete history
  - `delete_entry()` - Remove single entry
  - `clear_all()` - Wipe all history with count return

- ✅ **Export Functions:**
  - `export_csv()` - Write history to CSV with columns: Actor ID, Name, Rating, Date, Source, Status
  - `export_json()` - Full JSON export with metadata

- ✅ **Statistics:**
  - `get_statistics()` - Total, success count, failed count, last created timestamp
  - Source type breakdown

- ✅ **Database:**
  - SQLite schema with indexed queries
  - Auto-created in `~/.com-importer/history.db`
  - Schema version tracking for migrations

- ✅ **Tab Integration:**
  - History tab displays all entries with color-coded status (green/red)
  - Callback system to auto-add entries when dangers created from SingleImportTab
  - JSON preview of selected entry
  - Refresh, export, and clear controls

### Testing (`tests/test_*.py`)
- ✅ `test_integration.py` - Full pipeline tests (parsing, conversion, JSON validity)
- ✅ `test_history.py` - History persistence tests (CRUD, export, statistics)
- ✅ `test_ocr.py` - OCR and PDF extraction tests

### Phase 2: OCR & Image Processing (COMPLETE)

#### 2.1 Image Parser Abstraction (`image_parser.py`)
- ✅ `TesseractImageParser` - Local OCR using Tesseract
  - Image preprocessing (grayscale, contrast enhancement, deskew, upscaling)
  - Auto-detection of Tesseract installation
  - Both pytesseract and subprocess fallback support
- ✅ `CloudVisionImageParser` - Google Cloud Vision API support
  - API key authentication
  - High-accuracy OCR for complex text
- ✅ `ImageOCRFactory` - Factory pattern with fallback strategy
  - "auto" mode: tries Tesseract first, falls back to Cloud Vision
  - Support for method selection and configuration

#### 2.2 PDF Support (`pdf_handler.py`)
- ✅ `PDFHandler` class with static methods
  - `get_page_count()` - Get total pages in PDF
  - `extract_page_as_image()` - Extract single page as PIL Image
  - `extract_page_as_file()` - Save extracted page to file
  - `extract_all_pages_as_images()` - Get all pages as images
  - Configurable DPI for quality/speed tradeoff

#### 2.3 GUI Integration (in `single_import_tab.py`)
- ✅ Image tab with file browser
  - Auto-OCR when image selected
  - Progress indication during OCR
  - Error handling with user-friendly messages
  - Text populates automatically in text field
- ✅ PDF tab with page selector
  - Choose which page to extract
  - Auto-OCR extracted page
  - Same text population as image input
- ✅ OCR configuration from ConfigTab
  - Method selection (Tesseract/Cloud Vision/Auto)
  - API key management
  - Tesseract path detection

## 🔄 IN PROGRESS

None currently - all high-priority features implemented!

---

## 📋 TODO (Priority Order)
1. **Batch Import Manager** (`batch_manager.py`)
   - Multiple danger creation with transaction semantics
   - Success/failure tracking per danger
   - Rollback capability
   - Report generation

2. **Edit Dialog** (`dialogs.py`)
   - Edit form for parsed danger data
   - Field validation
   - Tag/move/spectrum management UI

### MEDIUM PRIORITY

#### Phase 5: Testing
- OCR accuracy tests with sample rulebook images
- Batch operation tests
- Local Foundry filesystem tests
- Stress tests with complex dangers

#### Additional Parsing
- **Character Parser** (`character_parser.py`)
  - Player character text parsing
  - Theme extraction
  - Tag/move parsing for characters

### LOW PRIORITY

#### Phase 6: Packaging
- PyInstaller configuration for Mac (.app)
- PyInstaller configuration for Windows (.exe)
- Installer generation (DMG for Mac, NSIS for Windows)
- Code signing (Mac)
- PyPI package preparation

---

## 📊 Implementation Summary

| Phase | Component | Status | Priority |
|-------|-----------|--------|----------|
| 1 | Schema Definition | ✅ Complete | - |
| 1 | API Clients | ✅ Complete | - |
| 1 | Danger Parser | ✅ Complete | - |
| 1 | Text Transform | ✅ Complete | - |
| 2 | OCR Support | 🔄 TODO | HIGH |
| 2 | PDF Extraction | 🔄 TODO | HIGH |
| 3 | Main Window | ✅ Complete | - |
| 3 | Single Import UI | ✅ Complete | - |
| 3 | Config UI | ✅ Complete | - |
| 3 | Batch UI | 🟨 Partial | MEDIUM |
| 3 | History UI | 🟨 Partial | MEDIUM |
| 4 | Foundry Converter | ✅ Complete | - |
| 4 | Batch Manager | 🔄 TODO | MEDIUM |
| 5 | Tests | ✅ Partial | HIGH |
| 6 | Packaging | 🔄 TODO | LOW |

---

## 📊 Feature Implementation Summary

| Feature | Status | Description |
|---------|--------|-------------|
| Text parsing | ✅ | Parse dangers from pasted text with error handling |
| Foundry API | ✅ | Create/update dangers via REST API or local filesystem |
| GUI interface | ✅ | PyQt6-based tabbed application |
| Single import | ✅ | Parse and create individual dangers interactively |
| Configuration | ✅ | Manage Foundry connection settings, OCR options |
| History tracking | ✅ | SQLite persistence of all created dangers |
| History export | ✅ | Export to CSV and JSON formats |
| History UI | ✅ | View, search, and manage history entries |
| Batch import | 🔄 | Multiple dangers at once (partial) |
| OCR (Tesseract) | 🔄 | Local image/PDF parsing (ready to integrate) |
| OCR (Cloud Vision) | 🔄 | Cloud-based high-accuracy OCR (ready to integrate) |
| Character parser | ⏳ | Player character import (planned) |
| Packaging | ⏳ | .app/.exe binary distribution (planned) |

---

## 🎯 Next Steps by Priority

### Immediate (Most Impactful)
1. **OCR Integration** - Enable image/PDF input
2. **Batch Import** - Create multiple dangers at once
3. **Edit Dialog** - Modify parsed dangers before creation

### Short-term
4. **Character Parser** - Support player characters
5. **Dialog Enhancements** - Settings, about, help dialogs
6. **Test Coverage** - Comprehensive test suite

### Long-term
7. **Packaging** - PyInstaller binary distribution
8. **UI Polish** - Better error messages, progress indication
9. **Advanced Features** - Undo/redo, bulk operations, templates

### Running the GUI
```bash
python3 -m com_importer.gui_main
# or: com-importer-gui
```

### Testing Core Pipeline
```bash
cd /Users/mythic/Documents/Projects/CoM_Importer
python3 -m pytest tests/test_integration.py -v
```

### Example Usage (Python)
```python
from com_importer.danger_parser import DangerParser
from com_importer.danger_to_foundry import convert_danger_to_foundry
from com_importer.foundry_client import FoundryClientFactory

# Parse text
parser = DangerParser()
danger, errors = parser.parse("Zeus - Danger Rating 3\n...")

# Convert to Foundry format
actor_json = convert_danger_to_foundry(danger)

# Create in Foundry (remote API)
client = FoundryClientFactory.create_rest_client(
    api_url="https://foundryvtt-rest-api-relay.fly.dev",
    api_key="...",
    client_id="...",
    world_name="city-of-mist-ii"
)
actor_id = client.create_actor(actor_json)
```

---

## 🎯 Next Steps

1. **Immediate (Next Session):**
   - Test GUI with PyQt6 environment
   - Implement image/PDF OCR integration
   - Complete batch import functionality
   - Add history persistence

2. **Short-term:**
   - Enhanced parsing for edge cases
   - Character parser implementation
   - Comprehensive test coverage
   - Error handling improvements

3. **Long-term:**
   - Packaging and distribution
   - User documentation
   - Feature polish and UX refinement

---

## 📝 Notes

- All Foundry schema follows City of Mist module v3.0.0 compatibility
- Code follows Python 3.10+ with type hints and linting
- GUI uses PyQt6 for cross-platform support (Mac/Windows)
- Bracket syntax `[tag-name]` in moves auto-creates tags/statuses
- Both remote API and local filesystem clients share same interface

---

## 🔗 Resources

- **City of Mist II Foundry System:** https://github.com/MythicTalesLLC/city-of-mist-custom
- **Foundry REST API:** https://foundryvtt-rest-api-relay.fly.dev
- **Rulebooks:** MC Toolkit, Player's Guide (in Gaming Share folder)
