#!/usr/bin/env bash
# ============================================================================
# EA FC27 WebApp Bot - Starter Script (Ubuntu / Linux)
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "❌ Virtual Environment nicht gefunden! Bitte zuerst ausführen: ./setup_ubuntu.sh"
    exit 1
fi

# Prüfe ob Xvfb verfügbar ist und kein X-Server läuft
if [ -z "$DISPLAY" ] && command -v xvfb-run &> /dev/null; then
    echo "🖥️  Starte Bot im virtuellen Framebuffer (Xvfb 1920x1080)..."
    xvfb-run -a -s "-screen 0 1920x1080x24" ./venv/bin/python bot.py "$@"
else
    ./venv/bin/python bot.py "$@"
fi
