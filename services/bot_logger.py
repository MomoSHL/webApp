"""
🔍 Logging-Konfiguration für EA FC27 WebApp Bot
================================================
Implementiert strukturiertes Logging mit:
- Console Output (farbig, mit Emojis)
- File Output (rotating logs)
- Verschiedene Log-Level
- Thread-safe

Usage:
    from bot_logger import get_logger
    logger = get_logger(__name__)
    logger.info("✅ Operation successful")
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional


# Log-Verzeichnis
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class EmojiFormatter(logging.Formatter):
    """Custom Formatter der Emojis beibehält und farbig formatiert."""
    
    # ANSI Color Codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        """Formatiert Log-Record mit Farben (nur für Console)."""
        # Füge Farbe hinzu wenn Terminal (nicht File)
        if hasattr(self, 'use_colors') and self.use_colors:
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True
) -> logging.Logger:
    """
    Erstellt oder gibt existierenden Logger zurück.
    
    Args:
        name: Logger-Name (meist __name__)
        level: Log-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Logs in Datei schreiben
        log_to_console: Logs in Console ausgeben
    
    Returns:
        Konfigurierter Logger
    """
    logger = logging.getLogger(name)
    
    # Verhindere doppelte Handler bei wiederholtem Aufruf
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    logger.propagate = False  # Verhindere Propagation zu root logger
    
    # Format-Strings
    console_format = '%(message)s'  # Nur Message (mit Emojis)
    file_format = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    
    # Console Handler (mit Farben)
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = EmojiFormatter(console_format)
        console_formatter.use_colors = True
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File Handler (mit Rotation)
    if log_to_file:
        log_file = LOG_DIR / f"bot_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_formatter = EmojiFormatter(file_format)
        file_formatter.use_colors = False
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def setup_bot_logging(verbose: bool = False) -> logging.Logger:
    """
    Richtet Haupt-Bot-Logger ein.
    
    Args:
        verbose: True = DEBUG-Level, False = INFO-Level
    
    Returns:
        Konfigurierter Bot-Logger
    """
    level = logging.DEBUG if verbose else logging.INFO
    return get_logger('ea_fc27_bot', level=level)


# Convenience-Funktionen für formatierte Logs
def log_section(logger: logging.Logger, title: str, width: int = 60):
    """Logged einen formatierten Section-Header."""
    logger.info("\n" + "="*width)
    logger.info(title)
    logger.info("="*width + "\n")


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


# Beispiel-Usage
if __name__ == '__main__':
    # Test Logging
    logger = setup_bot_logging(verbose=True)
    
    log_section(logger, "🧪 LOGGING TEST")
    
    logger.debug("🔍 Debug message - nur für Entwicklung")
    logger.info("ℹ️ Info message - normale Operation")
    logger.warning("⚠️ Warning message - potentielles Problem")
    logger.error("❌ Error message - Fehler aufgetreten")
    logger.critical("💥 Critical message - schwerer Fehler!")
    
    log_success(logger, "Operation erfolgreich!")
    log_error(logger, "Operation fehlgeschlagen!")
    log_warning(logger, "Cookies veraltet")
    log_info(logger, "Browser initialisiert")
    log_debug(logger, "XPath: //button[contains(text(), 'Login')]")
    
    print(f"\n✓ Logs gespeichert in: {LOG_DIR}")
