#!/bin/bash
# Build script for City of Mist Importer - macOS
# Creates standalone CoM-Importer.app bundle for distribution

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
DIST_DIR="$PROJECT_DIR/dist"

echo "🔨 Building CoM Importer for macOS..."
echo "Project directory: $PROJECT_DIR"

# Clean previous builds
if [ -d "$BUILD_DIR" ]; then
    echo "Cleaning previous build..."
    rm -rf "$BUILD_DIR"
fi

if [ -d "$DIST_DIR" ]; then
    echo "Cleaning previous dist..."
    rm -rf "$DIST_DIR"
fi

# Install build dependencies if needed
echo "Checking dependencies..."
python3 -m pip install -q pyinstaller 2>/dev/null || true

# Build using PyInstaller
echo "Running PyInstaller..."
cd "$PROJECT_DIR"
python3 -m PyInstaller --clean -y com_importer_mac.spec

# Verify build
if [ -d "$DIST_DIR/CoM-Importer.app" ]; then
    echo "✅ Build successful!"
    echo "App location: $DIST_DIR/CoM-Importer.app"

    # Create DMG for distribution (optional)
    if command -v create-dmg &> /dev/null; then
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
    if [ ! -z "$CODESIGN_IDENTITY" ]; then
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
