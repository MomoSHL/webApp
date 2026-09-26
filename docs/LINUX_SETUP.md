# Linux Installation - EA FC26 WebApp Bot

## Voraussetzungen

### 1. Python 3.8+
```bash
# Prüfen ob Python installiert ist
python3 --version

# Falls nicht installiert (Ubuntu/Debian):
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### 2. Chrome/Chromium installieren
```bash
# Option A: Google Chrome (empfohlen)
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb

# Option B: Chromium
sudo apt install chromium-browser
```

### 3. Abhängigkeiten für Chrome (wichtig!)
```bash
# Notwendige Bibliotheken für Chrome Headless
sudo apt install -y \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    fonts-liberation
```

## Installation

### 1. Virtual Environment erstellen
```bash
cd /pfad/zu/webApp
python3 -m venv venv
source venv/bin/activate
```

### 2. Dependencies installieren
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Konfiguration anpassen
```bash
# config.yaml editieren
nano config.yaml

# Wichtig: 
# - username und password eintragen
# - headless: true (für Server ohne GUI)
# - headless: false (für Desktop mit GUI zum Testen)
```

## Ausführung

### Interaktiv (Testen)
```bash
# Virtual Environment aktivieren
source venv/bin/activate

# Bot starten
python3 ea_fc26_bot.py
```

### Als Systemd Service (Dauerbetrieb)

#### 1. Service-Datei erstellen
```bash
sudo nano /etc/systemd/system/ea-fc26-bot.service
```

#### 2. Service-Konfiguration
```ini
[Unit]
Description=EA FC26 WebApp Bot
After=network.target

[Service]
Type=simple
User=DEIN_USERNAME
WorkingDirectory=/pfad/zu/webApp
Environment="PATH=/pfad/zu/webApp/venv/bin"
ExecStart=/pfad/zu/webApp/venv/bin/python3 /pfad/zu/webApp/ea_fc26_bot.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

**WICHTIG:** Ersetze:
- `DEIN_USERNAME` mit deinem Linux-User
- `/pfad/zu/webApp` mit dem echten Pfad

#### 3. Service aktivieren
```bash
# Service neu laden
sudo systemctl daemon-reload

# Service aktivieren (Auto-Start beim Boot)
sudo systemctl enable ea-fc26-bot

# Service starten
sudo systemctl start ea-fc26-bot

# Status prüfen
sudo systemctl status ea-fc26-bot

# Logs anzeigen
sudo journalctl -u ea-fc26-bot -f
```

#### 4. Service-Befehle
```bash
# Starten
sudo systemctl start ea-fc26-bot

# Stoppen
sudo systemctl stop ea-fc26-bot

# Neustarten
sudo systemctl restart ea-fc26-bot

# Status
sudo systemctl status ea-fc26-bot

# Auto-Start deaktivieren
sudo systemctl disable ea-fc26-bot
```

## Troubleshooting

### Chrome startet nicht (Headless)
```bash
# GPU-Probleme? Prüfe ob --disable-gpu aktiv ist
# Der Bot setzt dies automatisch unter Linux

# Display-Variable setzen (falls nötig)
export DISPLAY=:0
```

### Permissions-Fehler
```bash
# Chrome-Binary ausführbar machen
chmod +x $(which google-chrome)

# Oder für Chromium
chmod +x $(which chromium-browser)
```

### 2FA funktioniert nicht
```bash
# Im interaktiven Modus starten (headless=false)
# Code in der Konsole eingeben
python3 ea_fc26_bot.py
```

### Cookies werden nicht gespeichert
```bash
# Prüfe Berechtigungen
ls -la cookies/

# Falls Ordner fehlt:
mkdir -p cookies
chmod 755 cookies
```

### Chrome/ChromeDriver Version-Konflikt
```bash
# Prüfe Chrome-Version
google-chrome --version

# undetected-chromedriver installiert automatisch passenden Driver
# Falls Probleme: Manuell ChromeDriver installieren
```

## Cron-Alternative (statt Systemd)

Falls du Cron bevorzugst:

```bash
# Crontab editieren
crontab -e

# Alle 30 Minuten ausführen (Beispiel)
*/30 * * * * cd /pfad/zu/webApp && /pfad/zu/webApp/venv/bin/python3 ea_fc26_bot.py >> /pfad/zu/webApp/logs/cron.log 2>&1
```

**HINWEIS:** Systemd ist besser geeignet, da:
- Automatischer Neustart bei Fehler
- Besseres Log-Management
- Einfachere Verwaltung

## Test-Modus

Für einzelne Test-Läufe:

```bash
# In config.yaml setzen:
test_mode: true

# Dann starten:
python3 ea_fc26_bot.py
```

Der Bot führt genau einen Durchlauf aus und beendet sich dann.

## Performance-Tipps für Linux Server

### Headless optimieren
```yaml
# config.yaml
headless: true  # Muss true sein für Server ohne GUI
```

### RAM-Nutzung reduzieren
```bash
# In ea_fc26_bot.py sind bereits optimale Chrome-Flags gesetzt:
# --disable-dev-shm-usage
# --no-sandbox
```

### Log-Rotation einrichten
```bash
sudo nano /etc/logrotate.d/ea-fc26-bot
```

```
/pfad/zu/webApp/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

## Sicherheit

### Firewall (optional)
```bash
# Falls der Bot nach außen verbinden soll
sudo ufw allow out 443/tcp  # HTTPS
sudo ufw allow out 80/tcp   # HTTP
```

### Automatische Updates (Ubuntu/Debian)
```bash
# System-Updates
sudo apt update && sudo apt upgrade -y

# Python-Packages aktualisieren
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## Multi-Account Setup

Der Bot unterstützt mehrere Accounts:

1. Erstelle mehrere config-Dateien:
   - `config_account1.yaml`
   - `config_account2.yaml`

2. Erstelle separate Services:
   - `/etc/systemd/system/ea-fc26-bot-account1.service`
   - `/etc/systemd/system/ea-fc26-bot-account2.service`

3. Passe `ExecStart` an:
   ```bash
   ExecStart=/pfad/zu/venv/bin/python3 /pfad/zu/ea_fc26_bot.py --config config_account1.yaml
   ```

## Support

Bei Problemen:
1. Prüfe Logs: `sudo journalctl -u ea-fc26-bot -n 100`
2. Teste im interaktiven Modus: `python3 ea_fc26_bot.py`
3. Chrome-Version prüfen: `google-chrome --version`
4. Dependencies neu installieren: `pip install -r requirements.txt --force-reinstall`
