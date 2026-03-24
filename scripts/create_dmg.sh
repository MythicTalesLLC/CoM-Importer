#!/bin/bash
# Create a distributable DMG for CoM-Importer.
# Must be run after a successful mac build (dist/CoM-Importer.app must exist).
#
# Usage: bash scripts/create_dmg.sh [--version <ver>]
#
# Output: dist/CoM-Importer-<version>-mac.dmg

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$PROJECT_DIR/dist"
APP_NAME="CoM-Importer"
APP_PATH="$DIST_DIR/${APP_NAME}.app"

# ── helpers ────────────────────────────────────────────────────────────────────

usage() {
    echo "Usage: $0 [--version <ver>]"
    echo ""
    echo "  --version <ver>   Version string for the DMG filename (default: read from pyproject.toml)"
    echo "  --help            Show this message"
    exit 0
}

# ── argument handling ──────────────────────────────────────────────────────────

VERSION=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --version) VERSION="$2"; shift 2 ;;
        --help|-h) usage ;;
        *) echo "Unknown argument: $1"; usage ;;
    esac
done

# Fall back to pyproject.toml
if [[ -z "$VERSION" ]]; then
    if [[ -f "$PROJECT_DIR/pyproject.toml" ]]; then
        VERSION="$(grep -E '^version' "$PROJECT_DIR/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
    fi
fi
VERSION="${VERSION:-0.1.0}"

DMG_NAME="${APP_NAME}-${VERSION}-mac"
DMG_PATH="$DIST_DIR/${DMG_NAME}.dmg"
TMP_DMG_PATH="$DIST_DIR/${DMG_NAME}-tmp.dmg"
VOLUME_NAME="$APP_NAME"

# ── preflight ─────────────────────────────────────────────────────────────────

if [[ ! -d "$APP_PATH" ]]; then
    echo "ERROR: App bundle not found: $APP_PATH"
    echo "Run 'bash scripts/build.sh --mac' first."
    exit 1
fi

echo "Creating DMG: ${DMG_NAME}.dmg (version $VERSION)"

# Clean up any previous partial builds
rm -f "$TMP_DMG_PATH" "$DMG_PATH"

# ── create a writable DMG ─────────────────────────────────────────────────────

echo "  Creating writable disk image..."
hdiutil create \
    -srcfolder "$APP_PATH" \
    -volname "$VOLUME_NAME" \
    -fs HFS+ \
    -fsargs "-c c=16,a=16,b=16" \
    -format UDRW \
    -size 400m \
    "$TMP_DMG_PATH" >/dev/null

# ── mount ─────────────────────────────────────────────────────────────────────

echo "  Mounting disk image..."
MOUNT_OUTPUT="$(hdiutil attach -readwrite -noverify -noautoopen "$TMP_DMG_PATH")"
DEVICE="$(echo "$MOUNT_OUTPUT" | grep -E '^/dev/' | tail -1 | awk '{print $1}')"
MOUNT_POINT="$(echo "$MOUNT_OUTPUT" | sed -n 's|^/dev/[^[:space:]]*[[:space:]].*\(/Volumes/.*\)$|\1|p' | tail -1)"

if [[ -z "$MOUNT_POINT" ]]; then
    echo "ERROR: Could not determine mount point."
    rm -f "$TMP_DMG_PATH"
    exit 1
fi
echo "  Mounted at: $MOUNT_POINT"

# ── populate DMG ──────────────────────────────────────────────────────────────

# Create a symlink to /Applications so users can drag-install
ln -sf /Applications "$MOUNT_POINT/Applications"

# ── set window layout via AppleScript ────────────────────────────────────────

echo "  Setting Finder window layout..."
sleep 1   # give Finder time to notice the mount

osascript <<APPLESCRIPT 2>/dev/null || true
tell application "Finder"
    tell disk "$VOLUME_NAME"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {200, 120, 760, 440}
        set theViewOptions to the icon view options of container window
        set arrangement of theViewOptions to not arranged
        set icon size of theViewOptions to 128
        set position of item "${APP_NAME}.app" of container window to {155, 165}
        set position of item "Applications" of container window to {405, 165}
        close
        open
        update without registering applications
        delay 1
        close
    end tell
end tell
APPLESCRIPT

# ── finalise ──────────────────────────────────────────────────────────────────

echo "  Unmounting..."
sync
hdiutil detach "$DEVICE" -quiet

echo "  Converting to compressed read-only DMG..."
hdiutil convert "$TMP_DMG_PATH" \
    -format UDZO \
    -imagekey zlib-level=9 \
    -o "$DMG_PATH" >/dev/null

rm -f "$TMP_DMG_PATH"

DMG_SIZE="$(du -sh "$DMG_PATH" | cut -f1)"
echo ""
echo "✅  DMG created: dist/${DMG_NAME}.dmg ($DMG_SIZE)"
echo ""
echo "Distribute this file. Recipients open it, then drag CoM-Importer → Applications."
