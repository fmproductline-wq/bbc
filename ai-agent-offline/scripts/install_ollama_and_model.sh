#!/usr/bin/env bash
# One-shot installer: installs Ollama + downloads a default model

set -e
MODEL="${1:-llama3.2:3b}"

echo ""
echo "  BestBrand AI Agent — Quick Setup"
echo "  ================================="
echo ""

# Install Ollama
if ! command -v ollama &>/dev/null; then
    echo "  Installing Ollama..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  Download from: https://ollama.com/download"
        open "https://ollama.com/download"
        exit 0
    else
        curl -fsSL https://ollama.com/install.sh | sh
    fi
else
    echo "  [✓] Ollama already installed"
fi

# Start Ollama
if ! pgrep -x "ollama" &>/dev/null; then
    echo "  Starting Ollama service..."
    ollama serve &>/dev/null &
    sleep 3
fi

# Pull model
echo ""
echo "  Downloading model: $MODEL (~2 GB for llama3.2:3b)"
echo "  This only happens once. Future launches are instant."
echo ""
ollama pull "$MODEL"

echo ""
echo "  ✓ Setup complete! You can now use BestBrand AI Agent."
echo "  Tip: Run 'ollama list' to see installed models."
echo ""
