#!/usr/bin/env bash
set -e

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║        BestBrand AI Agent — USB          ║"
echo "  ║     Offline AI · No Internet Needed      ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check Ollama
if ! command -v ollama &>/dev/null; then
    echo "  [!] Ollama not installed. Installing..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Start Ollama if not running
if ! pgrep -x "ollama" &>/dev/null; then
    echo "  [*] Starting Ollama..."
    ollama serve &>/dev/null &
    sleep 2
fi

# Find and launch AppImage
APPIMAGE=$(find "$SCRIPT_DIR/.." -name "*.AppImage" 2>/dev/null | head -1)

if [ -z "$APPIMAGE" ]; then
    echo "  [!] No AppImage found in USB directory."
    exit 1
fi

chmod +x "$APPIMAGE"
echo "  [*] Launching $APPIMAGE..."
"$APPIMAGE" &
echo "  [✓] BestBrand AI Agent launched!"
