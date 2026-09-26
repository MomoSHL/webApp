#!/usr/bin/env bash
# ============================================================================
# EA FC27 WebApp Bot - Ubuntu Server Setup Script
# ============================================================================
# Kompatibel mit Ubuntu 20.04, 22.04, 24.04 LTS
#
# Verwendung:
#   chmod +x setup_ubuntu.sh
#   ./setup_ubuntu.sh
# ============================================================================

set -e

echo "============================================================"
echo "🚀 EA FC27 WebApp Bot - Ubuntu Setup wird gestartet"
echo "============================================================"

# Prüfe ob sudo vorhanden ist (falls als root ausgeführt)
if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
elif command -v sudo &> /dev/null; then
    SUDO="sudo"
else
    echo "❌ Fehler: 'sudo' ist nicht installiert und das Skript wird nicht als root ausgeführt."
    exit 1
fi

# 1. Systempakete aktualisieren & Basis-Tools installieren
echo "📦 1/5: Installiere System-Abhängigkeiten..."
$SUDO apt update
$SUDO apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    curl \
    unzip \
    ca-certificates \
    xvfb \
    fonts-liberation \
    libnss3 \
    xdg-utils

# 2. Google Chrome installieren (falls noch nicht vorhanden)
echo "🌐 2/5: Prüfe Google Chrome Installation..."
if ! command -v google-chrome &> /dev/null; then
    echo "   → Lade Google Chrome Stable herunter..."
    cd /tmp
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    $SUDO apt install -y ./google-chrome-stable_current_amd64.deb
    rm -f google-chrome-stable_current_amd64.deb
    cd - > /dev/null
    echo "   ✓ Google Chrome erfolgreich installiert"
else
    echo "   ✓ Google Chrome ist bereits installiert: $(google-chrome --version)"
fi

# 3. Virtual Environment einrichten
echo "🐍 3/5: Richte Python Virtual Environment ein..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   ✓ Virtual Environment 'venv' erstellt"
fi

echo "   → Installiere Python-Abhängigkeiten..."
./venv/bin/pip install --upgrade pip setuptools wheel
./venv/bin/pip install -r requirements.txt
echo "   ✓ Python-Pakete erfolgreich installiert"

# 4. Verzeichnisse & Berechtigungen anlegen
echo "📁 4/5: Bereite Verzeichnisse vor..."
mkdir -p cookies services/logs

if [ -f "start_bot.sh" ]; then
    chmod +x start_bot.sh
fi

# 5. Konfiguration (.env) prüfen
echo "⚙️  5/5: Prüfe Konfiguration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "   ⚠️  '.env' wurde aus '.env.example' erstellt!"
        echo "   👉 Bitte trage deine Zugangsdaten ein: nano .env"
    else
        echo "   ⚠️  Keine '.env' Datei gefunden. Bitte erstelle eine .env Datei."
    fi
else
    echo "   ✓ '.env' Datei vorhanden"
fi

echo ""
echo "============================================================"
echo "✅ Setup erfolgreich abgeschlossen!"
echo "============================================================"
echo ""
echo "Nächste Schritte:"
echo " 1. Zugangsdaten eintragen:"
echo "    nano .env"
echo ""
echo " 2. (Empfohlen) Cookies von lokal übertragen (erspart 2FA auf dem Server):"
echo "    Kopiere deine Datei aus cookies/ in das cookies/ Verzeichnis auf dem Server"
echo ""
echo " 3. Bot manuell testen:"
echo "    ./start_bot.sh"
echo ""
echo " 4. Als Hintergrund-Dienst einrichten (24/7):"
echo "    sudo cp eafc27-bot.service /etc/systemd/system/"
echo "    sudo systemctl daemon-reload"
echo "    sudo systemctl enable --now eafc27-bot"
echo "============================================================"
