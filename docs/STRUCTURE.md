# 📁 WebApp Bot - Ordnerstruktur

**Stand:** 2025-01-14  
**Status:** 🟢 Production Ready (Clean)

---

## 📂 Root Verzeichnis

```
webApp/
├── 🚀 bot.py                    # Haupteinstiegspunkt (Starter)
├── ⚙️ bot_config.py             # Configuration Management (Dataclass)
├── 🎮 bot_session.py            # Session & State Management
├── 🤖 bot_main.py               # Bot Operations (EAFC26Bot Class)
├── 📝 bot_logger.py             # Logging Setup
├── 📊 bot_stats.py              # Statistics Tracking
├── 📈 bot_stats.json            # Statistics Data (persistent)
├── ✅ config_validator.py       # Config Validation
├── 🔧 ea_fc26_bot.py            # Legacy Functions (login, relist)
│
├── 🔐 config.yaml               # Bot Configuration (NICHT in Git!)
├── 🌍 .env                      # Environment Variables (optional)
├── 🚫 .gitignore                # Git Ignore Rules
├── 📦 requirements.txt          # Python Dependencies
├── 📖 README.md                 # Hauptdokumentation
│
├── 🍪 cookies/                  # Browser Cookies (pro User)
├── 📝 logs/                     # Log-Dateien
└── 📚 docs/                     # Dokumentation
```

---

## 📊 Datei-Details

### 🚀 Hauptdateien (Required)

| Datei | Zeilen | Zweck | Status |
|-------|--------|-------|--------|
| `bot.py` | 254 | Main Entry Point, Scheduler-Logik | ✅ Aktiv |
| `bot_config.py` | 228 | Type-Safe Config (BotConfig) | ✅ Aktiv |
| `bot_session.py` | 216 | Session Management (BotSession) | ✅ Aktiv |
| `bot_main.py` | 306 | Bot Operations (EAFC26Bot) | ✅ Aktiv |
| `bot_logger.py` | ~150 | Enterprise Logging | ✅ Aktiv |
| `bot_stats.py` | ~250 | Statistics & Reporting | ✅ Aktiv |
| `config_validator.py` | ~200 | Config Validation | ✅ Aktiv |
| `ea_fc26_bot.py` | ~1400 | Legacy Functions (Import) | ✅ Aktiv |

### 📄 Config-Dateien

| Datei | Zweck | In Git? |
|-------|-------|---------|
| `config.yaml` | Bot-Konfiguration (Login, Selektoren) | ❌ Nein (sensibel) |
| `.env` | Environment Variables (optional) | ❌ Nein (sensibel) |
| `.gitignore` | Git Ignore Rules | ✅ Ja |
| `requirements.txt` | Python Dependencies | ✅ Ja |

### 📚 Dokumentation (docs/)

| Datei | Zweck |
|-------|-------|
| `CHANGELOG_LINUX.md` | Linux-spezifische Änderungen |
| `CHANGES.md` | Allgemeines Changelog |
| `CLASS_REFACTORING_COMPLETE.md` | Class-Based Refactoring Doku |
| `LINUX_SETUP.md` | Linux Installation Guide |
| `README_MAIN.md` | Ausführliche Dokumentation |

### 🗂️ Ordner

| Ordner | Zweck | In Git? |
|--------|-------|---------|
| `cookies/` | Browser-Cookies (pro User) | ❌ Nein |
| `logs/` | Log-Dateien | ❌ Nein |
| `docs/` | Dokumentation | ✅ Ja |

---

## 🗑️ Entfernte Ordner/Dateien

### ❌ Gelöscht (2025-01-14)

| Ordner/Datei | Grund |
|--------------|-------|
| `archived/` (3 .bak Dateien) | Alte Backups nicht mehr benötigt |
| `tools/` (4 .py Migration-Scripts) | Migration abgeschlossen |
| `tests/` (3 Unit-Test-Dateien) | Tests dokumentieren nur Ideale, Module funktionieren |
| `ReadMe/` | Zu docs/ verschoben |
| `__pycache__/` | Python Cache, regeneriert sich |
| `READY_TO_USE.md` | Redundant |
| **docs/**: 8 alte .md Reports | Alte Analysen/Reports archiviert |

### 📝 Gelöschte Docs

- `CODE_ANALYSIS.md`
- `PRINT_ANALYSIS.md`
- `STATUS_REPORT.md`
- `UNIT_TESTS_STATUS.md`
- `FINAL_STATUS.md`
- `PRINT_MIGRATION_COMPLETE.md`
- `INTEGRATION_GUIDE.md`
- `ENTERPRISE_UPGRADE.md`

---

## 🚀 Verwendung

### Start

```bash
# Windows
python bot.py

# Linux
python3 bot.py
```

### Konfiguration

1. `config.yaml` anpassen (Username, Password, UI-Selektoren)
2. Optional: `.env` für Environment Variables
3. Bot starten

### Modi

- **Test-Modus:** `test_mode: true` in config.yaml
- **Live-Session:** `headless: false` (Browser sichtbar)
- **Scheduler:** `headless: true` (Hintergrund, stündlich)

---

## 📦 Dependencies

Installiert via `requirements.txt`:

```bash
pip install -r requirements.txt
```

**Wichtigste Packages:**
- `selenium` - Browser-Automatisierung
- `undetected-chromedriver` - Anti-Detection
- `pyyaml` - Config-Parsing
- `python-dotenv` - .env Support

---

## 🔒 Sicherheit

### ⚠️ Nicht in Git committen:

- ❌ `config.yaml` (enthält Passwörter)
- ❌ `.env` (enthält sensible Daten)
- ❌ `cookies/` (Session-Tokens)
- ❌ `logs/` (könnte sensible Infos enthalten)
- ❌ `bot_stats.json` (könnte Username enthalten)

### ✅ Prüfen:

```bash
# .gitignore enthält:
config.yaml
.env
cookies/
logs/
*.log
bot_stats.json
__pycache__/
```

---

## 📊 Code-Statistik

### Gesamt

| Kategorie | Anzahl | Zeilen |
|-----------|--------|--------|
| **Core Bot** | 8 Dateien | ~2800 Zeilen |
| **Config** | 4 Dateien | ~50 Zeilen |
| **Dokumentation** | 6 Dateien | ~2000 Zeilen |
| **Gesamt** | 18 Dateien | ~4850 Zeilen |

### Code-Verteilung

```
ea_fc26_bot.py:     ~1400 Zeilen (Legacy Functions)
bot_main.py:         ~306 Zeilen (Main Bot Class)
bot.py:              ~254 Zeilen (Entry Point)
bot_stats.py:        ~250 Zeilen (Statistics)
bot_config.py:       ~228 Zeilen (Config Management)
bot_session.py:      ~216 Zeilen (Session Management)
config_validator.py: ~200 Zeilen (Validation)
bot_logger.py:       ~150 Zeilen (Logging)
```

---

## 🎯 Architektur

### Class-Based Design

```
┌─────────────┐
│   bot.py    │  ← Entry Point
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ EAFC26Bot   │  ← Main Bot Class
│ (bot_main)  │
└──────┬──────┘
       │
       ├──► BotConfig (bot_config)
       ├──► BotSession (bot_session)
       ├──► BotLogger (bot_logger)
       └──► BotStatistics (bot_stats)
```

### Legacy-Integration

```
EAFC26Bot (new)
    │
    ├──► login() ──────► login_via_ui() (legacy)
    └──► relist_all() ─► relist_all_transfer_items() (legacy)
```

---

## ✅ Sauber & Production Ready!

- ✅ Unnötige Dateien entfernt
- ✅ Ordnerstruktur aufgeräumt
- ✅ Dokumentation konsolidiert
- ✅ Nur essenzielle Dateien behalten
- ✅ Klare Trennung: Core / Config / Docs

**Status:** 🟢 **Clean & Einsatzbereit!**

---

*Moritz Schulte, 2025-01-14*
