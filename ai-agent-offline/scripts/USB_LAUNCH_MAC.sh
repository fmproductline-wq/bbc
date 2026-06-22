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
if ! command -v ollama &>/dev/null && ! [ -f "/usr/local/bin/ollama" ]; then
    echo "  [!] Ollama not found. Please install it from:"
    echo "      https://ollama.com/download"
    echo ""
    open "https://ollama.com/download" 2>/dev/null || true
    exit 1
fi

# Start Ollama if not running
if ! pgrep -x "ollama" &>/dev/null; then
    echo "  [*] Starting Ollama..."
    ollama serve &>/dev/null &
    sleep 2
fi

# Launch app
APP="$SCRIPT_DIR/../BestBrand AI Agent.app"
APPIMAGE="$SCRIPT_DIR/../BestBrand-AI-Agent.AppImage"

if [ -d "$APP" ]; then
    echo "  [*] Launching app..."
    open "$APP"
elif [ -f "$APPIMAGE" ]; then
    echo "  [*] Launching AppImage..."
    "$APPIMAGE" &
else
    echo "  [!] App not found. Expected: BestBrand AI Agent.app"
    exit 1
fi

echo "  [✓] BestBrand AI Agent launched!"
