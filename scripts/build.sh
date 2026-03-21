#!/bin/bash
# Cross-platform build script for City of Mist Importer
# Detects OS and builds appropriate binary

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS="$(uname -s)"

echo "🔨 City of Mist Importer - Build System"
echo "Detected OS: $OS"
echo ""

case "$OS" in
    Darwin)
        echo "Building for macOS..."
        "$SCRIPT_DIR/build_mac.sh"
        ;;
    Linux)
        echo "❌ Linux builds not yet supported"
        echo "Please use build_windows.sh or build_mac.sh manually"
        exit 1
        ;;
    MINGW*|MSYS*|CYGWIN*)
        echo "Building for Windows..."
        "$SCRIPT_DIR/build_windows.sh"
        ;;
    *)
        echo "❌ Unknown OS: $OS"
        exit 1
        ;;
esac
