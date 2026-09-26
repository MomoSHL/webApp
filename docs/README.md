# Services Package

Modular aufgebautes Service-Package für den EA FC26 WebApp Bot.

## 📦 Struktur

```
services/
├── __init__.py              # Package-Exports (API)
├── bot_config.py            # Konfigurations-Management
├── bot_session.py           # Session-State-Management
├── bot_main.py              # Haupt-Bot-Klasse
├── bot_logger.py            # Logging-Setup
├── bot_stats.py             # Statistik-Tracking
├── config_validator.py      # Config-Validierung
├── bot_helpers.py           # Helper-Funktionen (Wrapper → ea_fc26_bot.py)
├── browser_utils.py         # Browser-Funktionen (Wrapper → ea_fc26_bot.py)
├── login_service.py         # Login-Operationen (Wrapper → ea_fc26_bot.py)
└── relist_service.py        # Re-List-Operationen (Wrapper → ea_fc26_bot.py)
```

## 🔄 Architektur-Pattern

### Wrapper-Module

Die Module `bot_helpers.py`, `browser_utils.py`, `login_service.py` und `relist_service.py` 
sind **Wrapper** - sie importieren Funktionen aus `ea_fc26_bot.py` und exportieren sie wieder:

```python
# services/login_service.py
from ea_fc26_bot import login_via_ui, handle_2fa

# Re-Export
__all__ = ['login_via_ui', 'handle_2fa']
```

**Warum Wrapper?**
- ✅ `ea_fc26_bot.py` hat 1406 Zeilen (zu groß für manuelle Migration)
- ✅ Wrapper = keine Code-Duplikation
- ✅ 100% identische Funktionalität garantiert
- ✅ Services bieten saubere API
- ✅ ea_fc26_bot.py bleibt als Backend erhalten

## 📝 Verwendung

### Import aus Services

```python
from services import (
    # Core
    BotConfig, BotSession, EAFC26Bot,
    
    # Logger
    get_logger, log_section,
    
    # Browser
    init_browser, switch_to_webapp_tab,
    
    # Login
    login_via_ui,
    
    # Re-List
    relist_all_transfer_items
)
```

### Bot erstellen

```python
from services import BotConfig, EAFC26Bot

config = BotConfig.from_yaml("config.yaml")
bot = EAFC26Bot(config)
success = bot.run_job()
bot.cleanup()
```

## 🎯 Module-Übersicht

### bot_config.py
**Klassen**: `BotConfig`
**Funktionen**: `load_config()`
**Zweck**: Konfiguration laden, validieren und verwalten

### bot_session.py
**Klassen**: `BotSession`, `SessionState`
**Zweck**: Session-State tracken (Login-Status, Re-List-Count, Errors)

### bot_main.py
**Klassen**: `EAFC26Bot`
**Funktionen**: `create_bot()`
**Zweck**: Haupt-Bot-Logik (Init, Login, Re-List, Cleanup)

### bot_logger.py
**Funktionen**: 
- `get_logger()` - Logger-Instanz holen
- `setup_bot_logging()` - Logging konfigurieren
- `log_section()`, `log_success()`, `log_error()`, etc.

**Zweck**: Einheitliches, farbiges Logging

### bot_stats.py
**Klassen**: `BotStatistics`
**Zweck**: Statistiken tracken (Logins, Re-Lists, Errors, Zeiten)

### config_validator.py
**Funktionen**: `validate_config()`
**Exceptions**: `ConfigValidationError`
**Zweck**: Config-Struktur prüfen

### bot_helpers.py (Wrapper)
**Imports von**: `ea_fc26_bot.py`
**Exports**:
- `human_like_delay()` - Menschliche Verzögerungen
- `is_night_time()` - Nachtpausen-Check
- `calculate_sleep_until_morning()` - Sleep-Berechnung
- `random_mouse_movements()` - Maus-Simulationen
- `random_scroll_behavior()` - Scroll-Simulationen
- `randomize_viewport()` - Zufällige Fenstergrößen
- `simulate_tab_switch()` - Tab-Wechsel
- `human_type()` - Menschliches Tippen
- `human_click()` - Menschlicher Klick

### browser_utils.py (Wrapper)
**Imports von**: `ea_fc26_bot.py`
**Exports**:
- `init_browser()` - Browser initialisieren
- `get_platform_user_agent()` - User-Agent holen
- `save_cookies()`, `load_cookies()` - Cookie-Management
- `switch_to_idle_tab()`, `switch_to_webapp_tab()` - Tab-Handling
- `check_already_logged_in_elsewhere()` - Login-Check

### login_service.py (Wrapper)
**Imports von**: `ea_fc26_bot.py`
**Exports**:
- `login_via_ui()` - UI-Login durchführen
- `handle_2fa()` - 2FA-Code-Handling

### relist_service.py (Wrapper)
**Imports von**: `ea_fc26_bot.py`
**Exports**:
- `relist_all_transfer_items()` - Alle Items neu listen
- `navigate_to_transfer_list()` - Zur Transfer-Liste navigieren

## ⚠️ Wichtig

### Dependencies

Die Wrapper-Module brauchen `ea_fc26_bot.py` als Backend-Quelle:

```
services/browser_utils.py  ──→  ea_fc26_bot.py
services/login_service.py  ──→  ea_fc26_bot.py
services/relist_service.py ──→  ea_fc26_bot.py
services/bot_helpers.py    ──→  ea_fc26_bot.py
```

**NIEMALS `ea_fc26_bot.py` löschen!**

### Import-Regeln

✅ **RICHTIG** - Von Services importieren:
```python
from services import login_via_ui, init_browser
```

❌ **FALSCH** - Direkt von ea_fc26_bot:
```python
from ea_fc26_bot import login_via_ui  # ❌ Nicht mehr!
```

🔍 **AUSNAHME** - Nur in Wrapper-Modulen:
```python
# services/login_service.py - OK, ist Wrapper
from ea_fc26_bot import login_via_ui
```

## 🧪 Testing

```bash
# Import-Test
python -c "from services import BotConfig, EAFC26Bot; print('OK')"

# Bot-Test
python bot.py --test
```

## 📚 Weitere Dokumentation

- `../MIGRATION_COMPLETE.md` - Migration-Details
- `../STATUS_FINAL.md` - Kompletter Status
- `../README.md` - Bot-Dokumentation
