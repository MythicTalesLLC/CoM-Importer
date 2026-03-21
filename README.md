# City of Mist Foundry Importer

A powerful GUI tool for converting text, images, and PDFs from City of Mist rulebooks into properly formatted actors for Foundry VTT with the [City of Mist module](https://github.com/taragnor/city-of-mist).

**Transform rulebook content into game-ready Foundry actors in minutes** — supports both player characters and dangers/threats with full OCR capabilities.

## ✨ Features

### Input Formats
- **Text Paste** — Paste danger/character descriptions directly from PDFs, documents, or rulebooks
- **Image OCR** — Scan screenshots and rulebook pages with automatic text extraction
- **PDF Extraction** — Extract specific pages from PDF rulebooks and convert to game data
- **Batch Import** — Import multiple dangers/characters at once from files (CSV, JSONL, or text blocks)

### Supported OCR Methods
- **Local Tesseract** — Fast, offline OCR (install via `brew install tesseract`)
- **Google Cloud Vision** — High-accuracy cloud-based OCR with API key
- **Automatic Fallback** — Tries local Tesseract first, falls back to Cloud Vision

### Import Types
- **Dangers/Threats** — Full support for danger rating, mythos/logos identities, spectrums, GM moves (hard/soft/custom), tags, and statuses
- **Player Characters** — Complete character support including pronouns, themes (Mythos/Logos/Mist), juice tracking (help/hurt), and custom tags

### Foundry Integration
- **Remote API Access** — Connect to remote Foundry instances via REST API
- **Local Filesystem** — Work with local Foundry installations directly
- **Actor Creation** — Automatically create properly formatted threat/character actors in Foundry
- **History Tracking** — SQLite database tracks all imports with statistics and export options

### GUI Features
- **Multi-Tab Interface** — Single import, batch import, configuration, and history tabs
- **Live JSON Preview** — See how your actor will look in Foundry format
- **Edit Dialog** — Review and modify parsed data before creation
- **Progress Tracking** — Real-time feedback for long-running operations
- **Export Options** — Save parsed data as JSON drafts or export history as CSV/JSON

## 🚀 Quick Start

### Installation

#### Option 1: Standalone Application (Recommended)
Coming soon! Phase 6 will provide:
- **macOS**: CoM-Importer.app (drag-and-drop installation)
- **Windows**: CoM-Importer.exe (installer)

These standalone binaries don't require Python installation.

#### Option 2: Development Installation

##### macOS
```bash
# Clone the repository
git clone https://github.com/MythicTalesLLC/CoM-Importer.git
cd CoM-Importer

# Install Tesseract (optional, for local OCR)
brew install tesseract

# Install Python dependencies
pip install -e .

# Run the application
python -m com_importer.gui_main
```

##### Linux/Windows
```bash
git clone https://github.com/MythicTalesLLC/CoM-Importer.git
cd CoM-Importer

# Install Tesseract
# macOS: brew install tesseract
# Ubuntu: sudo apt-get install tesseract-ocr
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki

pip install -e .
python -m com_importer.gui_main
```

### First Run Setup

1. **Launch the application**
   ```bash
   python -m com_importer.gui_main
   ```

2. **Configure Foundry Connection** (Configuration tab)
   - Choose Remote API or Local Filesystem
   - For Remote:
     - Enter API URL (e.g., `https://foundry.example.com`)
     - Provide API key and Client ID
     - Click "Test Connection"
   - For Local:
     - Browse to your Foundry Data directory
     - Select world name
     - Click "Test Connection"

3. **Configure OCR** (Configuration tab)
   - Select OCR method (Auto, Tesseract, or Cloud Vision)
   - If using Cloud Vision, provide API key
   - Test with sample image

4. **Start Importing!**
   - Go to "Single Import" tab to import one danger/character
   - Or "Batch Import" tab for multiple imports

## 📖 Usage Guide

### Single Import Workflow

1. **Select Import Type**
   - Choose "Danger (Threat)" or "Character (Player)" from dropdown

2. **Provide Source**
   - **Text Tab**: Paste danger/character description
   - **Image Tab**: Select screenshot from rulebook
   - **PDF Tab**: Select PDF file and page number

3. **Parse Input**
   - Click "Parse" to extract structured data
   - Review any warnings or errors

4. **Review & Edit**
   - Click "Edit" to review parsed data
   - Modify any fields as needed
   - Preview live JSON output in dialog

5. **Create or Save**
   - Click "Create in Foundry" to add to your world
   - Or "Save as Draft" to save JSON locally for later

### Batch Import Workflow

1. **Prepare File**
   - JSONL format: One JSON object per line with "text" or "description" field
   - CSV format: Spreadsheet with "text" column
   - Text format: Multiple blocks separated by `---`

2. **Configure**
   - Select actor type (Danger or Character)
   - Select file source
   - Review import preview

3. **Import**
   - Click "Import All"
   - Monitor progress bar
   - View results in log

4. **Track History**
   - Go to "History" tab to see all imports
   - Export as CSV or JSON for records
   - View statistics by source and status

### Text Format Examples

#### Danger Format
```
The Corrupted Guardian
Danger Rating: 3

A twisted protector of an ancient shrine, corrupted by
eldritch forces. It guards what should never be found.

Mythos: [Interdimensional Parasite]
Logos: [Corrupted Shrine Guardian]

Spectrum: Health 2/4, Sanity 1/3

Hard Move: Attack with overwhelming force
Soft Move: Create an eerie atmosphere
Custom Move: When approached, draws the investigator deeper

Tag: [Supernatural], [Strong], [Protective]
Status: Hunting, Harmed
```

#### Character Format
```
Maya Chen
She/Her

A skilled detective investigating supernatural cases.

Mythos: [Supernatural Hunter] - Connected to the mystical world
Logos: [Police Detective] - Works within the law
Mist: [The Mystery] - Always drawn to unsolved cases

Juice: Help 1/3, Hurt 0/3

Tag: [Perceptive], [Determined]
```

## 🏗️ Architecture

### Project Structure
```
com_importer/
├── Core Components
│   ├── com_schema.py          # DangerActor, CharacterActor dataclasses
│   ├── danger_parser.py       # Text → DangerActor conversion
│   ├── character_parser.py    # Text → CharacterActor conversion
│   │
├── Foundry Integration
│   ├── foundry_client.py      # REST and local filesystem clients
│   ├── danger_to_foundry.py   # DangerActor → Foundry JSON
│   ├── character_to_foundry.py # CharacterActor → Foundry JSON
│   ├── batch_manager.py       # Batch import orchestration
│   │
├── Processing
│   ├── image_parser.py        # OCR with Tesseract + Cloud Vision
│   ├── pdf_handler.py         # PDF page extraction
│   ├── history_manager.py     # SQLite-backed history tracking
│   ├── danger_transform.py    # Text normalization
│   │
├── GUI
│   ├── gui_main.py            # Application entry point
│   ├── gui/
│   │   ├── main_window.py     # Main application window
│   │   ├── tabs/
│   │   │   ├── single_import_tab.py
│   │   │   ├── batch_import_tab.py
│   │   │   ├── config_tab.py
│   │   │   └── history_tab.py
│   │   ├── dialogs.py         # Edit/preview dialogs
│   │   └── validators.py      # Form validation
│   └── styles.py              # UI styling
```

### Data Flow Pipeline
```
Input (Text/Image/PDF)
    ↓
OCR (if image/PDF) → [Tesseract | Cloud Vision]
    ↓
Parse → [DangerParser | CharacterParser]
    ↓
Schema Extraction → DangerActor | CharacterActor
    ↓
Validation → Check required fields + constraints
    ↓
Convert to Foundry → [DangerToFoundry | CharacterToFoundry]
    ↓
Foundry Output → [REST API | Local Filesystem]
    ↓
History Tracking → SQLite Database
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_character.py -v

# Run with coverage
pytest tests/ --cov=src/com_importer
```

### Test Coverage
- **51 tests** covering all major components
- Character parsing and conversion (19 tests)
- Danger parsing and conversion (11 tests)
- Batch import operations (8 tests)
- OCR and PDF handling (8 tests)
- History tracking (1 test)
- Integration pipeline (9 tests)

## 📋 Requirements

### System Requirements
- Python 3.10+
- PyQt6 for GUI
- For OCR:
  - Local: Tesseract binary (`brew install tesseract`)
  - Cloud: Google Cloud Vision API key

### Python Dependencies
See `pyproject.toml` for full list:
- PyQt6 — GUI framework
- pdf2image — PDF processing
- pytesseract — Tesseract OCR interface
- Pillow — Image processing
- requests — HTTP client for Foundry API
- google-cloud-vision — Cloud OCR (optional)

## 🔧 Configuration

### Foundry Connection

#### Remote API
```python
FoundryClientFactory.create_rest_client(
    api_url="https://foundry.example.com",
    api_key="your-api-key",
    client_id="your-client-id"
)
```

#### Local Filesystem
```python
FoundryClientFactory.create_local_client(
    foundry_data_dir="/path/to/foundry/Data",
    world_name="city-of-mist"
)
```

### OCR Configuration

```python
ImageOCRFactory.create_parser(
    method="auto",  # "auto", "tesseract", "cloud_vision"
    tesseract_path="/usr/local/bin/tesseract",  # Optional
    vision_api_key="your-cloud-vision-key"  # Optional
)
```

## 📊 Batch Import Format Examples

### JSONL Format
```jsonl
{"text": "The Shadows\nDanger Rating: 2\nDescription here...\nSpectrum: Fear 1/3"}
{"text": "Maya Chen\nShe/Her\nMythos: [Hunter]\nLogos: [Detective]"}
```

### CSV Format
```csv
name,text
Danger 1,"The Shadows\nDanger Rating: 2\n..."
Character 1,"Maya Chen\nShe/Her\n..."
```

### Text Blocks Format
```
The Shadows
Danger Rating: 2
Description here
---
Maya Chen
She/Her
Mythos: [Hunter]
```

## 🚫 Known Limitations & Future Work

### Current Status: ✅ Fully Functional with Phase 6 Packaging Underway
- ✅ Phases 1-4: All core features complete
- ✅ Phase 5: Comprehensive testing (51 tests passing)
- 🔄 Phase 6: PyInstaller packaging for standalone binaries (in progress)

### Phase 6: Building Standalone Binaries

**Build Configuration**:
- PyInstaller spec files for Mac and Windows
- Cross-platform build scripts
- GitHub Actions CI/CD workflow

**To Build Locally**:
```bash
# Install build dependencies
pip install -e ".[build]"

# Build for your platform (auto-detected)
bash scripts/build.sh

# Or build specifically
bash scripts/build_mac.sh    # Creates dist/CoM-Importer.app
bash scripts/build_windows.sh # Creates dist/com-importer.exe
```

See [PHASE6_PACKAGING.md](PHASE6_PACKAGING.md) for detailed build instructions, code signing, distribution, and CI/CD setup.

### Known Limitations
- OCR accuracy depends on image quality (try 200+ DPI for best results)
- Cloud Vision requires internet connection and active API quota
- Local Tesseract installation required for offline OCR
- Some special characters may not OCR perfectly

### Future Enhancements
- Automated build releases on GitHub Actions
- Code signing and notarization for distribution
- Support for additional Foundry modules and systems
- Template-based import for custom formats
- Collaboration features for team imports

## 🤝 Contributing

This project is open for improvements! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Run tests to ensure everything passes (`pytest tests/ -v`)
5. Commit with clear messages (`git commit -m "Add amazing feature"`)
6. Push to your fork and create a Pull Request

### Development Setup
```bash
# Clone and install in development mode
git clone https://github.com/YourUsername/CoM-Importer.git
cd CoM-Importer
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run application with debug logging
LOGLEVEL=DEBUG python -m com_importer.gui_main
```

## 📝 License

This project is licensed under the MIT License — see LICENSE file for details.

**Note**: City of Mist is a trademark of Modiphius Entertainment. This tool is a community utility for use with the City of Mist Foundry module and is not affiliated with or endorsed by Modiphius Entertainment or Foundry Games LLC.

## 🔗 Resources

- [City of Mist on Modiphius.net](https://www.modiphius.net/products/city-of-mist-roleplaying-game)
- [Foundry VTT Official Site](https://foundryvtt.com/)
- [City of Mist Foundry Module](https://github.com/taragnor/city-of-mist)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- [Google Cloud Vision API](https://cloud.google.com/vision)

## 📞 Support

- **Bug Reports**: Open an issue on GitHub with a clear description and steps to reproduce
- **Feature Requests**: Start a discussion or open an issue with the "enhancement" label
- **Development Questions**: Check test files for usage examples or open a discussion

## 🎯 Roadmap

### Recent Completions (Latest Session)
- ✅ Fixed item creation via REST API (removed auto-generated _id field issue)
- ✅ Implemented actor type auto-detection (threat vs character detection from OCR)
- ✅ Integrated auto-detection into GUI with manual override option
- ✅ Improved detection for multiple threat stat formats (FOOL/SCARE vs GET INTO TROUBLE/HURT OR SUBDUE)

### Current Work: Phase 6 - Packaging & Distribution
- PyInstaller configuration for Mac (.app) and Windows (.exe)
- Build scripts for automated compilation
- GitHub Actions CI/CD workflow for automated releases
- Documentation for code signing and distribution

### Next Steps
1. Test builds on both macOS and Windows platforms
2. Set up code signing certificates for distribution
3. Automate release workflow on GitHub Actions
4. Create distribution packages (DMG for Mac, MSI/Installer for Windows)

---

**Status**: Production-ready with phase 6 packaging infrastructure in place.

**Last Updated**: March 2026 | **Tests Passing**: 51/51 ✅
