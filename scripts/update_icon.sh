#!/bin/bash
# Update app icons from a source image.
# Usage: ./scripts/update_icon.sh <path-to-image>
#
# Generates:
#   assets/icons/source_com.<ext>    — copy of the source file
#   assets/icons/com_importer_icon_base.png — 1024x1024 base PNG
#   assets/icons/com_importer.icns   — macOS icon (requires iconutil)
#   assets/icons/com_importer.ico    — Windows multi-size icon
#   assets/icons/icon.iconset/       — intermediate iconset directory

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ICONS_DIR="$PROJECT_DIR/assets/icons"

# ── helpers ────────────────────────────────────────────────────────────────────

usage() {
    echo "Usage: $0 <source-image>"
    echo ""
    echo "  source-image  Path to a PNG, JPEG, or other PIL-readable image."
    echo "                Should be at least 1024×1024 for best results."
    echo ""
    echo "Example:"
    echo "  $0 ~/Downloads/my_icon.jpg"
    exit 0
}

require_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: Required command not found: $cmd"
        exit 1
    fi
}

# ── argument handling ──────────────────────────────────────────────────────────

if [[ $# -eq 0 || "$1" == "--help" || "$1" == "-h" ]]; then
    usage
fi

SOURCE_IMAGE="$1"

if [[ ! -f "$SOURCE_IMAGE" ]]; then
    echo "ERROR: File not found: $SOURCE_IMAGE"
    exit 1
fi

# ── preflight checks ──────────────────────────────────────────────────────────

require_cmd iconutil
require_cmd sips

# Resolve Python binary (prefer project venv)
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
    if [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
        PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
    elif [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
        PYTHON_BIN="$VIRTUAL_ENV/bin/python"
    elif command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="python3"
    else
        echo "ERROR: No Python interpreter found."
        exit 1
    fi
fi

echo "Using Python: $PYTHON_BIN"

# Verify Pillow is available
if ! "$PYTHON_BIN" -c "from PIL import Image" 2>/dev/null; then
    echo "ERROR: Pillow not found. Install with: pip install Pillow"
    exit 1
fi

# ── prepare output directory ───────────────────────────────────────────────────

mkdir -p "$ICONS_DIR"

# Derive extension from source file
EXT="${SOURCE_IMAGE##*.}"
EXT_LOWER="$(echo "$EXT" | tr '[:upper:]' '[:lower:]')"
DEST_SOURCE="$ICONS_DIR/source_com.$EXT_LOWER"
if [[ "$(realpath "$SOURCE_IMAGE")" != "$(realpath "$DEST_SOURCE" 2>/dev/null || echo '')" ]]; then
    cp -f "$SOURCE_IMAGE" "$DEST_SOURCE"
    echo "Copied source image → $DEST_SOURCE"
else
    echo "Source image already in place → $DEST_SOURCE"
fi

# ── generate base PNG and Windows ICO via Pillow ──────────────────────────────

echo "Generating base PNG and Windows ICO..."

ICONS_DIR="$ICONS_DIR" DEST_SOURCE="$DEST_SOURCE" \
"$PYTHON_BIN" - <<'PYEOF'
import sys, os
from PIL import Image

icons_dir = os.environ["ICONS_DIR"]
dest_source = os.environ["DEST_SOURCE"]

img = Image.open(dest_source).convert("RGBA")
w, h = img.size
side = min(w, h)
left   = (w - side) // 2
top    = (h - side) // 2
img    = img.crop((left, top, left + side, top + side))
img    = img.resize((1024, 1024), Image.Resampling.LANCZOS)

base_png = os.path.join(icons_dir, "com_importer_icon_base.png")
img.save(base_png, "PNG")
print(f"  Base PNG → {base_png}")

ico_path = os.path.join(icons_dir, "com_importer.ico")
ico_sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
ico_images = [img.resize(s, Image.Resampling.LANCZOS) for s in ico_sizes]
ico_images[0].save(ico_path, format="ICO", sizes=ico_sizes,
                   append_images=ico_images[1:])
print(f"  Windows ICO → {ico_path}")
PYEOF

# ── generate iconset via sips ──────────────────────────────────────────────────

echo "Generating macOS iconset..."

ICONSET_DIR="$ICONS_DIR/icon.iconset"
rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"
BASE_PNG="$ICONS_DIR/com_importer_icon_base.png"

declare -a ICONSET_ENTRIES=(
    "icon_16x16.png:16"
    "icon_16x16@2x.png:32"
    "icon_32x32.png:32"
    "icon_32x32@2x.png:64"
    "icon_128x128.png:128"
    "icon_128x128@2x.png:256"
    "icon_256x256.png:256"
    "icon_256x256@2x.png:512"
    "icon_512x512.png:512"
    "icon_512x512@2x.png:1024"
)

for ENTRY in "${ICONSET_ENTRIES[@]}"; do
    FILENAME="${ENTRY%%:*}"
    SIZE="${ENTRY##*:}"
    sips -z "$SIZE" "$SIZE" "$BASE_PNG" --out "$ICONSET_DIR/$FILENAME" >/dev/null
done
echo "  Iconset → $ICONSET_DIR (${#ICONSET_ENTRIES[@]} sizes)"

# ── compile icns ──────────────────────────────────────────────────────────────

ICNS_PATH="$ICONS_DIR/com_importer.icns"
iconutil -c icns "$ICONSET_DIR" -o "$ICNS_PATH"
ICNS_SIZE=$(du -sh "$ICNS_PATH" | cut -f1)
echo "  macOS ICNS → $ICNS_PATH ($ICNS_SIZE)"

# ── summary ───────────────────────────────────────────────────────────────────

echo ""
echo "✅  Icon assets updated successfully."
echo ""
echo "   macOS: $ICNS_PATH"
echo "   Windows: $ICONS_DIR/com_importer.ico"
echo ""
echo "Rebuild the app to pick up the new icon:"
echo "   bash scripts/build.sh --mac      (or --windows)"
