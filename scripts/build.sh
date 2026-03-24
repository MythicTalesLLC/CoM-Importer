#!/bin/bash
# Cross-platform build script for City of Mist Importer.
# Defaults to host OS, with optional explicit target selection.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OS="$(uname -s)"
TARGET="auto"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--auto|--mac|--windows|--dmg|--help]

Options:
  --auto     Detect target from host OS (default)
  --mac      Force macOS build script
  --windows  Force Windows build script
  --dmg      Build macOS app, then package it into a distributable DMG
  --help     Show this help message
EOF
}

run_builder() {
    local builder_name="$1"
    local builder_path="$SCRIPT_DIR/$builder_name"

    if [[ ! -f "$builder_path" ]]; then
        echo "ERROR: Missing builder script: $builder_path"
        exit 1
    fi

    cd "$PROJECT_DIR"
    bash "$builder_path"
}

if [[ $# -gt 1 ]]; then
    usage
    exit 2
fi

if [[ $# -eq 1 ]]; then
    case "$1" in
        --auto)
            TARGET="auto"
            ;;
        --mac)
            TARGET="mac"
            ;;
        --windows)
            TARGET="windows"
            ;;
        --dmg)
            TARGET="dmg"
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            usage
            exit 2
            ;;
    esac
fi

echo "City of Mist Importer - Build System"
echo "Project directory: $PROJECT_DIR"
echo "Host OS: $OS"
echo ""

if [[ "$TARGET" == "auto" ]]; then
    case "$OS" in
        Darwin)
            TARGET="mac"
            ;;
        # (no auto for dmg — must be specified explicitly)
        MINGW*|MSYS*|CYGWIN*)
            TARGET="windows"
            ;;
        Linux)
            echo "ERROR: Linux host auto-detection has no native builder target yet."
            echo "Run with --mac or --windows only if your environment supports that toolchain."
            exit 1
            ;;
        *)
            echo "ERROR: Unknown host OS: $OS"
            exit 1
            ;;
    esac
fi

case "$TARGET" in
    mac)
        echo "Building for macOS..."
        run_builder "build_mac.sh"
        ;;
    windows)
        echo "Building for Windows..."
        run_builder "build_windows.sh"
        ;;
    dmg)
        echo "Building for macOS + packaging DMG..."
        run_builder "build_mac.sh"
        echo ""
        echo "Packaging DMG..."
        bash "$SCRIPT_DIR/create_dmg.sh"
        ;;
    *)
        echo "ERROR: Invalid build target: $TARGET"
        exit 2
        ;;
esac
