#!/bin/bash
# Build script for City of Mist Importer - Windows
# Creates standalone com-importer.exe for distribution

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
DIST_DIR="$PROJECT_DIR/dist"
SPEC_FILE="$PROJECT_DIR/com_importer_windows.spec"
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

echo "🔨 Building CoM Importer for Windows..."
echo "Project directory: $PROJECT_DIR"

case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
        ;;
    *)
        echo "⚠️  Non-Windows host detected. This script targets Windows executable output and may fail."
        ;;
esac

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
if [ -f "$DIST_DIR/com-importer.exe" ]; then
    echo "✅ Build successful!"
    echo "Executable location: $DIST_DIR/com-importer.exe"

    # Create installer with NSIS
    if command -v makensis >/dev/null 2>&1; then
        echo "Creating NSIS installer..."
        cd "$PROJECT_DIR"
        makensis com_importer.nsi
        if [ -f "$DIST_DIR/CoM-Importer-"*"-windows.exe" ]; then
            INSTALLER="$(ls "$DIST_DIR/CoM-Importer-"*"-windows.exe" | head -1)"
            echo "✅ Installer created: $INSTALLER"
        fi
    else
        echo "ℹ️  NSIS not found. To create installer:"
        echo "     1. Install NSIS: https://nsis.sourceforge.io/"
        echo "     2. Run: makensis com_importer.nsi"
    fi

    # Sign executable (optional - requires code signing certificate)
    if [[ -n "${SIGNTOOL_PATH:-}" ]] && [[ -n "${CERT_PATH:-}" ]] && [[ -n "${CERT_PASS:-}" ]]; then
        if [[ ! -x "$SIGNTOOL_PATH" ]]; then
            echo "ERROR: SIGNTOOL_PATH is not executable: $SIGNTOOL_PATH"
            exit 1
        fi
        if [[ ! -f "$CERT_PATH" ]]; then
            echo "ERROR: CERT_PATH file not found: $CERT_PATH"
            exit 1
        fi
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
