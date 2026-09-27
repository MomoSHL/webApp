"""
🔍 Logging-Konfiguration für EA FC27 WebApp Bot
================================================
Implementiert strukturiertes, dateibasiertes Logging mit:
- bot.log: Sauberes Haupt-Log (INFO, WARNING, ERROR, CRITICAL) für 'tail -f logs/bot.log'
- debug.log: Detailliertes Debug-Log (DEBUG, INFO, etc. inkl. Zeilennummern) für 'tail -f logs/debug.log'
- Keine Terminal-Ausgabe im Normalbetrieb
- Automatische Log-Rotation (10MB / 20MB)

Usage:
    from services.bot_logger import get_logger
    logger = get_logger(__name__)
    logger.info("✅ Operation successful")
    logger.debug("🔍 Detaillierte Debug-Information")
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

# Log-Verzeichnis (im Projekt-Root)
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

BOT_LOG_PATH = LOG_DIR / "bot.log"
DEBUG_LOG_PATH = LOG_DIR / "debug.log"

# Globale Shared Handler (verhindert mehrfache File-Locks bei vielen Modulen)
_MAIN_FILE_HANDLER: Optional[RotatingFileHandler] = None
_DEBUG_FILE_HANDLER: Optional[RotatingFileHandler] = None
_CONSOLE_HANDLER: Optional[logging.Handler] = None


def _get_main_file_handler() -> RotatingFileHandler:
    global _MAIN_FILE_HANDLER
    if _MAIN_FILE_HANDLER is None:
        _MAIN_FILE_HANDLER = RotatingFileHandler(
            BOT_LOG_PATH,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        _MAIN_FILE_HANDLER.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        _MAIN_FILE_HANDLER.setFormatter(formatter)
    return _MAIN_FILE_HANDLER


def _get_debug_file_handler() -> RotatingFileHandler:
    global _DEBUG_FILE_HANDLER
    if _DEBUG_FILE_HANDLER is None:
        _DEBUG_FILE_HANDLER = RotatingFileHandler(
            DEBUG_LOG_PATH,
            maxBytes=20 * 1024 * 1024,  # 20 MB
            backupCount=5,
            encoding='utf-8'
        )
        _DEBUG_FILE_HANDLER.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        _DEBUG_FILE_HANDLER.setFormatter(formatter)
    return _DEBUG_FILE_HANDLER


def get_logger(
    name: str,
    level: int = logging.DEBUG,
    log_to_file: bool = True,
    log_to_console: bool = False
) -> logging.Logger:
    """
    Erstellt oder gibt existierenden Logger zurück.
    
    Standardmäßig:
    - log_to_console: False (stumm im Terminal)
    - bot.log: Schreibt INFO, WARNING, ERROR, CRITICAL
    - debug.log: Schreibt alle DEBUG- und Fehler-Meldungen
    
    Args:
        name: Logger-Name (meist __name__)
        level: Log-Level (Standard: DEBUG für volle Protokollierung in debug.log)
        log_to_file: In bot.log und debug.log schreiben
        log_to_console: In stdout schreiben (Standard: False)
        
    Returns:
        Konfigurierter Logger
    """
    logger = logging.getLogger(name)
    
    # Verhindere doppelte Handler bei wiederholtem Aufruf
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    logger.propagate = False
    
    # File-Handler hinzufügen
    if log_to_file:
        logger.addHandler(_get_main_file_handler())
        logger.addHandler(_get_debug_file_handler())
    
    # Console-Handler nur hinzufügen wenn explizit gewünscht
    if log_to_console:
        global _CONSOLE_HANDLER
        if _CONSOLE_HANDLER is None:
            _CONSOLE_HANDLER = logging.StreamHandler(sys.stdout)
            _CONSOLE_HANDLER.setLevel(logging.INFO)
            _CONSOLE_HANDLER.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(_CONSOLE_HANDLER)
    
    return logger


def setup_bot_logging(verbose: bool = False, console: bool = False) -> logging.Logger:
    """
    Richtet Haupt-Bot-Logger ein.
    """
    level = logging.DEBUG
    return get_logger('ea_fc27_bot', level=level, log_to_console=console)


# Convenience-Funktionen für formatierte Logs
def log_section(logger: logging.Logger, title: str, width: int = 60):
    """Logged einen formatierten Section-Header."""
    logger.info("\n" + "=" * width)
    logger.info(title)
    logger.info("=" * width + "\n")


def log_success(logger: logging.Logger, message: str):
    """Logged Erfolgs-Message mit ✅ Emoji."""
    logger.info(f"✅ {message}")


def log_error(logger: logging.Logger, message: str, exc_info: bool = False):
    """Logged Fehler-Message mit ❌ Emoji."""
    logger.error(f"❌ {message}", exc_info=exc_info)


def log_warning(logger: logging.Logger, message: str):
    """Logged Warnung mit ⚠️ Emoji."""
    logger.warning(f"⚠️ {message}")


def log_info(logger: logging.Logger, message: str):
    """Logged Info mit ℹ️ Emoji."""
    logger.info(f"ℹ️ {message}")


def log_debug(logger: logging.Logger, message: str):
    """Logged Debug mit 🔍 Emoji."""
    logger.debug(f"🔍 {message}")


_DISCORD_HANDLER: Optional[logging.Handler] = None


def setup_discord_logging(webhook_url: Optional[str]):
    """
    Richtet Discord-Webhook-Handler für Bot-Logs ein (für INFO, WARNING, ERROR).
    """
    global _DISCORD_HANDLER
    if not webhook_url or not webhook_url.startswith("http"):
        return
        
    if _DISCORD_HANDLER is None:
        from .discord_service import DiscordWebhookHandler
        _DISCORD_HANDLER = DiscordWebhookHandler(webhook_url, level=logging.INFO)
        
        # Füge Handler zu allen aktiven und zukünftigen Loggern hinzu
        logging.getLogger().addHandler(_DISCORD_HANDLER)
        for name in list(logging.root.manager.loggerDict.keys()):
            l = logging.getLogger(name)
            if _DISCORD_HANDLER not in l.handlers:
                l.addHandler(_DISCORD_HANDLER)
                
        get_logger(__name__).info("🎮 Discord Webhook-Benachrichtigungen aktiviert")

