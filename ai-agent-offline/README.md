# BestBrand AI Agent — Offline

A fully offline AI chat agent. No internet. No subscriptions. No data leaves the device.

## Features
- 💬 Chat with local AI models (Llama 3, Mistral, Phi-3, Gemma, etc.)
- 🔒 100% private — all processing on-device
- 🖥️ Works on Windows, Mac, Linux
- 💾 USB portable mode — run from a USB stick with no installation
- 📦 Installer available (.exe, .dmg, .AppImage, .deb)
- 🌙 Streaming responses with markdown rendering
- 🗂️ Conversation history saved locally

## Quick Start (Dev)

```bash
cd ai-agent-offline
npm install
npm start          # launches Electron app
```

### Prerequisites
1. Install [Ollama](https://ollama.com/download)
2. Pull a model: `ollama pull llama3.2:3b`
3. `npm install && npm start`

## Build

```bash
# Windows installer + portable
npm run build:win

# macOS dmg
npm run build:mac

# Linux AppImage + deb
npm run build:linux

# All platforms
npm run build:all
```

Output goes to `dist-electron/`.

## USB Usage

1. Build the portable exe: `npm run portable:win`
2. Copy `BestBrand-AI-Agent-Portable.exe` + `scripts/USB_LAUNCH_WINDOWS.bat` to USB
3. Plug USB into any Windows PC with Ollama installed
4. Double-click `USB_LAUNCH_WINDOWS.bat`

## Architecture

```
Electron (main process)
  └── Express server (port auto-assigned)
        └── Proxies to Ollama (port 11434)
React UI (renderer)
  └── Talks to Ollama directly (http://127.0.0.1:11434)
```

## Tech Stack
- **Electron** — desktop shell, frameless window
- **React + Vite + Tailwind** — UI
- **Ollama** — local LLM engine (free, open source)
- **electron-store** — persistent settings/conversations
- **electron-builder** — cross-platform builds
