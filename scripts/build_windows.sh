#!/bin/bash
# Build script for City of Mist Importer - Windows
# Creates standalone com-importer.exe for distribution

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
DIST_DIR="$PROJECT_DIR/dist"

echo "🔨 Building CoM Importer for Windows..."
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
python3 -m PyInstaller --clean -y com_importer_windows.spec

# Verify build
if [ -f "$DIST_DIR/com-importer.exe" ]; then
    echo "✅ Build successful!"
    echo "Executable location: $DIST_DIR/com-importer.exe"

    # Create installer with NSIS (optional - requires NSIS on Windows)
    if command -v makensis &> /dev/null; then
        echo "Creating NSIS installer..."
        # This would require a .nsi script file
        echo "ℹ️  To create MSI installer, run: makensis com_importer.nsi"
    else
        echo "ℹ️  To create MSI installer, install NSIS and create com_importer.nsi"
    fi

    # Sign executable (optional - requires code signing certificate)
    if [ ! -z "$SIGNTOOL_PATH" ] && [ ! -z "$CERT_PATH" ] && [ ! -z "$CERT_PASS" ]; then
        echo "Code signing executable..."
        "$SIGNTOOL_PATH" sign /f "$CERT_PATH" /p "$CERT_PASS" \
            /t http://timestamp.sectigo.com "$DIST_DIR/com-importer.exe"
        echo "✅ Code signing complete"
    else
        echo "ℹ️  To code sign: set SIGNTOOL_PATH, CERT_PATH, and CERT_PASS environment variables"
    fi

else
    echo "❌ Build failed - exe not found"
    exit 1
fi

echo ""
echo "Build process complete!"
echo "To run: $DIST_DIR/com-importer.exe"
