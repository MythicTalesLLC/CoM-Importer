#!/bin/bash
# Build script for City of Mist Importer - macOS
# Creates standalone CoM-Importer.app bundle for distribution

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
DIST_DIR="$PROJECT_DIR/dist"
SPEC_FILE="$PROJECT_DIR/com_importer_mac.spec"
PYTHON_BIN="${PYTHON_BIN:-}"

require_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: Required command not found: $cmd"
        exit 1
    fi
}

ensure_pyinstaller() {
    if "$PYTHON_BIN" -m PyInstaller --version >/dev/null 2>&1; then
        return
    fi

    echo "PyInstaller not found in current Python environment. Installing..."
    "$PYTHON_BIN" -m pip install pyinstaller

    if ! "$PYTHON_BIN" -m PyInstaller --version >/dev/null 2>&1; then
        echo "ERROR: PyInstaller install failed in current environment."
        echo "Try: $PYTHON_BIN -m pip install -e '.[build]'"
        exit 1
    fi
}

echo "🔨 Building CoM Importer for macOS..."
echo "Project directory: $PROJECT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "⚠️  Non-macOS host detected. This script targets macOS bundles and may fail."
fi

if [[ -z "$PYTHON_BIN" ]]; then
    if [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
        PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
    elif [[ -n "${VIRTUAL_ENV:-}" ]] && [[ -x "$VIRTUAL_ENV/bin/python" ]]; then
        PYTHON_BIN="$VIRTUAL_ENV/bin/python"
    elif command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="$(command -v python3)"
    else
        echo "ERROR: No usable Python interpreter found."
        exit 1
    fi
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "ERROR: PYTHON_BIN is not executable: $PYTHON_BIN"
    exit 1
fi

require_cmd rm

if [[ ! -f "$SPEC_FILE" ]]; then
    echo "ERROR: Spec file not found: $SPEC_FILE"
    exit 1
fi

ensure_pyinstaller
echo "Using Python: $PYTHON_BIN"

# Clean previous builds
if [ -d "$BUILD_DIR" ]; then
    echo "Cleaning previous build..."
    rm -rf "$BUILD_DIR"
fi

if [ -d "$DIST_DIR" ]; then
    echo "Cleaning previous dist..."
    rm -rf "$DIST_DIR"
fi

# Build using PyInstaller
echo "Running PyInstaller..."
cd "$PROJECT_DIR"
"$PYTHON_BIN" -m PyInstaller --clean -y "$SPEC_FILE"

# Verify build
if [ -d "$DIST_DIR/CoM-Importer.app" ]; then
    echo "✅ Build successful!"
    echo "App location: $DIST_DIR/CoM-Importer.app"

    # Create DMG for distribution (optional)
    if command -v create-dmg >/dev/null 2>&1; then
        echo "Creating DMG installer..."
        create-dmg \
            --volname "CoM Importer" \
            --window-pos 200 120 \
            --window-size 600 400 \
            --icon-size 100 \
            --icon "CoM-Importer.app" 150 190 \
            "$DIST_DIR/CoM-Importer.dmg" \
            "$DIST_DIR/CoM-Importer.app"
        echo "✅ DMG created: $DIST_DIR/CoM-Importer.dmg"
    else
        echo "ℹ️  To create DMG, install: npm install -g create-dmg"
    fi

    # Code signing for distribution (optional)
    if [[ -n "${CODESIGN_IDENTITY:-}" ]]; then
        require_cmd codesign
        echo "Code signing with identity: $CODESIGN_IDENTITY"
        codesign --deep --force --verify --verbose \
            --sign "$CODESIGN_IDENTITY" \
            "$DIST_DIR/CoM-Importer.app"
        echo "✅ Code signing complete"
    else
        echo "ℹ️  To code sign: export CODESIGN_IDENTITY='Developer ID Application: ...'"
    fi

else
    echo "❌ Build failed - app not found"
    exit 1
fi

echo ""
echo "Build process complete!"
echo "To run: open $DIST_DIR/CoM-Importer.app"
