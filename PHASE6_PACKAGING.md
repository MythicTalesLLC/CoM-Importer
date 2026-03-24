# Phase 6: Packaging & Distribution

## Overview

This directory contains all build configuration and scripts for creating standalone .app (macOS) and .exe (Windows) binaries of the City of Mist Importer.

## Files

- **com_importer_mac.spec** - PyInstaller specification for macOS .app bundle
- **com_importer_windows.spec** - PyInstaller specification for Windows .exe
- **build_mac.sh** - Build script for macOS (creates CoM-Importer.app)
- **build_windows.sh** - Build script for Windows (creates com-importer.exe)
- **build.sh** - Cross-platform wrapper with explicit targets (`--auto`, `--mac`, `--windows`)

## Prerequisites

### All Platforms
```bash
# Python 3.10 or higher
python3 --version

# Install project dependencies
pip install -e ".[dev,build]"
```

### macOS
- Xcode Command Line Tools (for code signing)
- Optional: `create-dmg` for DMG creation
```bash
npm install -g create-dmg
```

### Windows
- Visual Studio Build Tools or MinGW (for some dependencies)
- Optional: NSIS (for MSI installer creation)
- Optional: Signtool (for code signing executables)

## Building

### macOS
```bash
# Build is auto-detected on macOS
bash scripts/build.sh

# Force explicit target
bash scripts/build.sh --mac

# Or manually:
bash scripts/build_mac.sh

# With code signing (optional):
export CODESIGN_IDENTITY="Developer ID Application: Your Name (XXXXX)"
bash scripts/build_mac.sh
```

Output: `dist/CoM-Importer.app`

### Windows
```bash
# Build is auto-detected on Windows
bash scripts/build.sh

# Force explicit target
bash scripts/build.sh --windows

# Or manually:
bash scripts/build_windows.sh

# With code signing (optional):
export SIGNTOOL_PATH="C:\Program Files (x86)\Windows Kits\10\bin\...\signtool.exe"
export CERT_PATH="/path/to/certificate.pfx"
export CERT_PASS="certificate_password"
bash scripts/build_windows.sh
```

Output: `dist/com-importer.exe`

### Build Script Options
```bash
bash scripts/build.sh --help

# Common usage
bash scripts/build.sh --auto
bash scripts/build.sh --mac
bash scripts/build.sh --windows
```

### Python Interpreter Selection
- `build_mac.sh` and `build_windows.sh` prefer `./.venv/bin/python` when present
- Otherwise they use `$VIRTUAL_ENV/bin/python` (if active)
- Fallback is `python3` from `PATH`
- You can override explicitly with `PYTHON_BIN=/path/to/python`

## Distribution

### macOS

**DMG Installer** (requires create-dmg):
```bash
# Build script auto-creates DMG if create-dmg is installed
bash scripts/build_mac.sh

# Creates: dist/CoM-Importer.dmg
```

**Code Signing for App Store/Gatekeeper**:
```bash
export CODESIGN_IDENTITY="Developer ID Application: Your Name (XXXXX)"
bash scripts/build_mac.sh

# Verify signature:
codesign --verify --verbose "dist/CoM-Importer.app"
spctl --assess --verbose "dist/CoM-Importer.app"
```

**Notarization** (for distribution outside App Store):
```bash
# After code signing
xcrun notarytool submit dist/CoM-Importer.dmg \
    --apple-id your-email@example.com \
    --password app-specific-password \
    --team-id XXXXX

# Check status
xcrun notarytool info REQUEST_UUID \
    --apple-id your-email@example.com \
    --password app-specific-password
```

### Windows

**NSIS Installer**:
Create `com_importer.nsi` with:
```nsis
; Example NSIS installer script
; Customize with your branding
Name "CoM Importer"
OutFile "dist\CoM-Importer-Setup.exe"
InstallDir "$PROGRAMFILES\CoM Importer"

Section "Install"
    SetOutPath "$INSTDIR"
    File /r "dist\com-importer.exe"
SectionEnd
```

Then build:
```bash
makensis com_importer.nsi
# Creates: dist/CoM-Importer-Setup.exe
```

## Testing the Build

### macOS
```bash
# Run the app directly
open dist/CoM-Importer.app

# Or from command line
dist/CoM-Importer.app/Contents/MacOS/com-importer
```

### Windows
```bash
# Run the exe
dist\com-importer.exe
```

## Troubleshooting

### "PyInstaller not found"
```bash
pip install pyinstaller
```

### Missing hidden imports
Edit the `.spec` file and add to `hiddenimports` list, then rebuild.

### "No module named 'com_importer.gui'"
Ensure the build is run from the project root directory.

### Application won't start
Check error by running from terminal:
- macOS: `dist/CoM-Importer.app/Contents/MacOS/com-importer`
- Windows: `dist\com-importer.exe`

## Optimization

### Reducing Build Size

**Exclude unnecessary packages in .spec file:**
```python
excludedimports=[
    'matplotlib',
    'scipy',
    'pandas',
    'numpy',  # Only if not needed
]
```

**Use UPX compression:**
```bash
# Install UPX
brew install upx  # macOS
# or download from https://upx.github.io/

# UPX is already enabled in spec files
```

### Performance

The built application will have similar performance to pip-installed version since PyInstaller uses the same Python bytecode (.pyc) format.

## CI/CD Integration

For automated builds on GitHub Actions:

```yaml
- name: Build macOS
  if: runner.os == 'macOS'
  run: bash scripts/build_mac.sh

- name: Build Windows
  if: runner.os == 'windows'
  run: bash scripts/build_windows.sh

- name: Upload artifacts
  uses: actions/upload-artifact@v2
  with:
    name: CoM-Importer-${{ matrix.os }}
    path: dist/
```

## Notes

- First build will take longer (extracting dependencies)
- Subsequent builds are faster
- .spec files can be customized for your needs
- PyInstaller caches builds in `build/` directory
- Distribution binaries don't require Python installation on end user's machine

## Next Steps

1. Test builds locally on both macOS and Windows
2. Add automated CI/CD builds on GitHub Actions
3. Create release workflow for GitHub Releases
4. Add build version management to pyproject.toml
5. Consider cross-compilation setup if building for multiple targets from one machine
