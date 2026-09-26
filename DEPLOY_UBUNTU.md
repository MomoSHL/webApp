# 🚀 Deployment-Guide: EA FC27 Bot auf Ubuntu Server

Dieser Leitfaden führt dich Schritt für Schritt durch das Deployment des EA FC27 Bots auf einem Ubuntu-Server (20.04, 22.04 oder 24.04 LTS) über **Git**.

---

## Inhaltsverzeichnis
1. [Vorbereitung auf dem Windows-PC (Git Push)](#1-vorbereitung-auf-dem-windows-pc-git-push)
2. [Klonen auf dem Ubuntu-Server](#2-klonen-auf-dem-ubuntu-server)
3. [Automatisierte Installation](#3-automatisierte-installation)
4. [Konfiguration (.env)](#4-konfiguration-env)
5. [Cookies übertragen (2FA überspringen!)](#5-cookies-übertragen-2fa-überspringen)
6. [Testlauf](#6-testlauf)
7. [Dauerbetrieb als Systemd-Service (24/7)](#7-dauerbetrieb-als-systemd-service-247)
8. [Monitoring & Logs](#8-monitoring--logs)

---

## 1. Vorbereitung auf dem Windows-PC (Git Push)

> [!IMPORTANT]
> Die `.gitignore`-Datei schützt deine Zugangsdaten (`.env`), Cookies (`cookies/`) und Logs automatisch davor, zu Git hochgeladen zu werden.

### Git Repository lokal initialisieren & pushen:
Öffne PowerShell im Bot-Ordner:

```powershell
# 1. Git initialisieren (falls noch nicht geschehen)
git init

# 2. Alle relevanten Dateien hinzufügen (gitignore greift automatisch)
git add .

# 3. Ersten Commit erstellen
git commit -m "feat: EA FC27 WebApp Bot ready for deployment"

# 4. Mit deinem GitHub/GitLab Repository verbinden (privates Repo empfohlen!)
git remote add origin https://github.com/DEIN_USERNAME/DEIN_REPO.git
git branch -M main
git push -u origin main
```

---

## 2. Klonen auf dem Ubuntu-Server

Verbinde dich per SSH mit deinem Ubuntu-Server:

```bash
ssh benutzer@dein-server-ip
```

Klone dein Repository:

```bash
# In dein gewünschtes Verzeichnis wechseln (z. B. Home-Ordner)
cd ~

# Repository klonen
git clone https://github.com/DEIN_USERNAME/DEIN_REPO.git eafc27-bot
cd eafc27-bot
```

---

## 3. Automatisierte Installation

Führe das mitgelieferte Setup-Skript aus. Es installiert automatisch Google Chrome, Xvfb, Python-Abhängigkeiten und richtet die virtuelle Umgebung ein:

```bash
chmod +x setup_ubuntu.sh start_bot.sh
./setup_ubuntu.sh
```

---

## 4. Konfiguration (.env)

Erstelle deine Konfigurationsdatei aus der Vorlage:

```bash
# Falls noch nicht vorhanden:
cp .env.example .env

# Zugangsdaten eintragen
nano .env
```

Trage deine EA Account-Daten ein:
```env
EA_USERNAME="deine-email@example.com"
EA_PASSWORD="dein-passwort"
```
*(Speichern in `nano` mit `Strg + O`, `Enter` und Beenden mit `Strg + X`)*

In `config.yaml` kannst du das Verhalten anpassen:
- `test_mode: false` (damit der Bot im Scheduler-Modus alle ~1h läuft)
- `headless: true` (oder `false`, wenn du `start_bot.sh` mit Xvfb nutzt)

---

## 5. Cookies übertragen (2FA überspringen!)

Da auf einem Headless-Server kein interaktives Browserfenster geöffnet wird, ist die 2FA-Eingabe dort schwierig. **Lösung:** Da du dich auf Windows bereits erfolgreich eingeloggt hast, liegen deine gültigen Cookies in `cookies/`.

Kopiere die Cookie-Datei von deinem Windows-PC auf den Server:

Führe in der Windows PowerShell aus:
```powershell
# Beispiel mit scp (ersetze benutzer, ip und pfad):
scp -r ".\cookies\*" benutzer@dein-server-ip:~/eafc27-bot/cookies/
```

Sobald die Cookies auf dem Server liegen, erkennt der Bot diese automatisch und loggt sich ohne 2FA direkt ein!

---

## 6. Testlauf

Teste den Bot einmalig manuell auf dem Server:

```bash
./start_bot.sh
```

Das Skript `start_bot.sh` startet den Bot automatisch innerhalb von **Xvfb** (virtueller 1920x1080 Bildschirm). Dadurch verhält sich Chrome exakt wie auf einem Desktop-PC.

---

## 7. Dauerbetrieb als Systemd-Service (24/7)

Damit der Bot nach einem Neustart oder Absturz automatisch wieder startet:

1. Passe Pfad und Benutzer in `eafc27-bot.service` an:
   ```bash
   nano eafc27-bot.service
   ```
   Überprüfe `User` (z. B. `ubuntu`) und `WorkingDirectory` (z. B. `/home/ubuntu/eafc27-bot`).

2. Service registrieren und starten:
   ```bash
   sudo cp eafc27-bot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now eafc27-bot
   ```

3. Status prüfen:
   ```bash
   sudo systemctl status eafc27-bot
   ```

---

## 8. Monitoring & Logs

- **Live Systemd-Logs ansehen:**
  ```bash
  journalctl -u eafc27-bot -f
  ```

- **Bot-Logdateien anzeigen:**
  ```bash
  tail -f services/logs/bot_*.log
  ```

- **Bot stoppen oder neustarten:**
  ```bash
  sudo systemctl restart eafc27-bot
  sudo systemctl stop eafc27-bot
  ```

- **Updates einspielen (wenn du Code auf Git pushst):**
  ```bash
  cd ~/eafc27-bot
  git pull
  sudo systemctl restart eafc27-bot
  ```
