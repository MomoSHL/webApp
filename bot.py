#!/usr/bin/env python3
"""
🤖 EA FC27 WebApp Bot v2.0.0 - Class-Based Architecture
========================================================
Haupteinstiegspunkt mit BotConfig, BotSession und EAFC27Bot.

Author: Momo
Date: 2026-09-27
"""

import sys
import time
import random
from pathlib import Path
from datetime import datetime, timedelta

# Service-Module importieren
from services.bot_config import BotConfig
from services.bot_session import BotSession
from services.bot_main import EAFC27Bot, EAFC26Bot

# Import aus Services (ersetzt Legacy-Imports)
from services import (
    get_logger,
    is_night_time,
    calculate_sleep_until_morning,
    switch_to_idle_tab,
    switch_to_webapp_tab
)

logger = get_logger(__name__)


def run_test_mode(config: BotConfig):
    """
    🧪 Test-Modus: Einmalige Ausführung.
    
    Args:
        config: Bot-Konfiguration
    """
    logger.info("🧪 TEST-MODUS: Einmalige Ausführung\n")
    
    # Bot erstellen
    bot = EAFC27Bot(config)
    
    # Job ausführen
    success, status = bot.run_job()
    
    # Bei Non-Headless: Auf Enter warten
    if not config.headless and bot.session and bot.session.driver:
        input("\nDrücke Enter zum Beenden...")
    
    # Cleanup
    bot.cleanup()
    
    return 0 if success else 1


def run_live_session_mode(config: BotConfig):
    """
    🔄 Live-Session Modus: Browser bleibt offen zwischen Jobs.
    
    Args:
        config: Bot-Konfiguration
    """
    logger.info("🔄 LIVE-SESSION MODUS")
    logger.info("   Browser bleibt zwischen Jobs offen")
    logger.info("   Drücke Ctrl+C zum Beenden\n")
    
    # Bot erstellen
    bot = EAFC27Bot(config)
    
    retry_delay = 15 * 60  # 15 Minuten
    MAX_RETRIES = 3
    retry_count = 0
    
    try:
        while True:
            # Prüfe Nachtpause (1:00 - 6:00 Uhr)
            if is_night_time(start_hour=1, end_hour=6):
                sleep_seconds, wake_time = calculate_sleep_until_morning(wake_hour=6)
                sleep_hours = sleep_seconds / 3600
                logger.debug(f"\n😴 NACHTPAUSE (1:00 - 6:00 Uhr)")
                logger.debug(f"   Schlafe für {sleep_hours:.1f} Stunden")
                logger.debug(f"   Aufwachen um: {wake_time.strftime('%H:%M:%S')}")
                
                # Wechsle zu Idle-Tab während Nachtpause
                if bot.session and bot.session.driver:
                    switch_to_idle_tab(bot.session.driver)
                
                time.sleep(sleep_seconds)
                logger.debug("\n☀️ Guten Morgen! Bot startet wieder...\n")
                continue
            
            # Wechsle zurück zur WebApp vor Job
            if bot.session and bot.session.driver:
                logger.debug("\n🔄 Starte Job...")
                if not switch_to_webapp_tab(bot.session.driver, config.login_url):
                    logger.error("❌ Konnte nicht zur WebApp wechseln")
                    time.sleep(2)
                    continue
                time.sleep(1)
            
            # Job ausführen
            try:
                success, status = bot.run_job()
                retry_count = 0  # Reset bei Erfolg
                
                # Bei 'already_logged_in': 15 Minuten warten
                if bot.session and bot.session.state.last_status == 'already_logged_in':
                    logger.debug(f"⏳ Warte {retry_delay // 60} Minuten bis zum nächsten Versuch...")
                    
                    if bot.session.driver:
                        switch_to_idle_tab(bot.session.driver)
                    
                    time.sleep(retry_delay)
                    continue
                
            except Exception as e:
                retry_count += 1
                logger.error(f"❌ Job-Fehler (Versuch {retry_count}/{MAX_RETRIES}): {e}", exc_info=True)
                
                # Browser neu starten bei Crash
                if retry_count < MAX_RETRIES:
                    logger.info(f"🔄 Neustart in 10 Sekunden...")
                    bot.cleanup()
                    time.sleep(10)
                    
                    # Neuen Bot erstellen
                    try:
                        bot = EAFC27Bot(config)
                        logger.info("✅ Bot neu gestartet")
                        time.sleep(2)
                        continue
                    except Exception as restart_error:
                        logger.error(f"❌ Bot-Neustart fehlgeschlagen: {restart_error}")
                        time.sleep(retry_delay)
                        continue
                else:
                    logger.critical(f"💥 Maximale Retry-Versuche ({MAX_RETRIES}) erreicht!")
                    raise
            
            # Normale Wartezeit: 1h 1min bis 1h 20min (zufällig)
            base_seconds = 3600  # 1 Stunde
            random_extra = random.randint(60, 1200)  # 1-20 Minuten
            wait_seconds = base_seconds + random_extra
            
            wait_minutes = wait_seconds // 60
            next_run = datetime.now() + timedelta(seconds=wait_seconds)
            logger.info(f"⏳ Job erfolgreich! Nächster Durchlauf in {wait_minutes} Minuten (geplant um {next_run.strftime('%H:%M:%S')} Uhr)")
            
            # Wechsle zu Idle-Tab während Wartezeit
            if bot.session and bot.session.driver:
                switch_to_idle_tab(bot.session.driver)
            
            # Countdown-Schleife
            remaining = wait_seconds
            while remaining > 0:
                chunk = min(remaining, 60)
                time.sleep(chunk)
                remaining -= chunk
                
                # Alle 15 Minuten Countdown loggen
                if remaining > 0 and remaining % 900 == 0:
                    rem_min = remaining // 60
                    logger.info(f"⏳ Countdown: Noch {rem_min} Minuten bis zum nächsten Durchlauf (um {next_run.strftime('%H:%M:%S')} Uhr)")
    
    except KeyboardInterrupt:
        logger.info("\n✓ Bot gestoppt")
        bot.cleanup()


def run_scheduler_mode(config: BotConfig):
    """
    ⏰ Scheduler-Modus: Headless mit stündlichen Jobs.
    
    Args:
        config: Bot-Konfiguration
    """
    logger.info("⏰ SCHEDULER-MODUS (Headless)")
    logger.info("   Alle ~1 Stunde (1h 1min bis 1h 20min zufällig)")
    logger.info("   Nachtpause: 1:00 - 6:00 Uhr")
    logger.info("   Drücke Ctrl+C zum Beenden\n")
    
    retry_delay = 15 * 60  # 15 Minuten
    
    try:
        while True:
            # Prüfe Nachtpause (1:00 - 6:00 Uhr)
            if is_night_time(start_hour=1, end_hour=6):
                sleep_seconds, wake_time = calculate_sleep_until_morning(wake_hour=4)
                sleep_hours = sleep_seconds / 3600
                logger.info(f"😴 NACHTPAUSE (1:00 - 6:00 Uhr) - Schlafe für {sleep_hours:.1f} Stunden bis {wake_time.strftime('%H:%M:%S')}")
                time.sleep(sleep_seconds)
                logger.info("☀️ Guten Morgen! Bot startet wieder...")
                continue
            
            # Bot erstellen (neuer Browser pro Job im Headless-Modus)
            bot = EAFC27Bot(config)
            
            # Job ausführen
            success, status = bot.run_job()
            
            # Cleanup
            bot.cleanup()
            
            # Prüfe ob Session existiert bevor auf state zugegriffen wird
            if bot.session and hasattr(bot.session, 'state') and bot.session.state:
                # Bei 'already_logged_in': 15 Minuten warten
                if bot.session.state.last_status == 'already_logged_in':
                    logger.info(f"⏳ Auf anderem Gerät aktiv: Warte {retry_delay // 60} Minuten...")
                    time.sleep(retry_delay)
                    continue
            
            # Zufällige Wartezeit: 1h 1min bis 1h 20min
            base_seconds = 3600  # 1 Stunde
            random_extra = random.randint(60, 1200)  # 1-20 Minuten
            wait_seconds = base_seconds + random_extra
            
            wait_minutes = wait_seconds // 60
            next_run = datetime.now() + timedelta(seconds=wait_seconds)
            logger.info(f"⏳ Job abgeschlossen! Nächster Durchlauf in {wait_minutes} Minuten (geplant um {next_run.strftime('%H:%M:%S')} Uhr)")
            
            # Countdown-Schleife
            remaining = wait_seconds
            while remaining > 0:
                chunk = min(remaining, 60)
                time.sleep(chunk)
                remaining -= chunk
                
                # Alle 15 Minuten Countdown loggen
                if remaining > 0 and remaining % 900 == 0:
                    rem_min = remaining // 60
                    logger.info(f"⏳ Countdown: Noch {rem_min} Minuten bis zum nächsten Durchlauf (um {next_run.strftime('%H:%M:%S')} Uhr)")
    
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n✓ Scheduler gestoppt")


def main():
    """
    🚀 Haupteinstiegspunkt des Bots.
    
    Lädt Konfiguration und startet den Bot im entsprechenden Modus:
    - Test-Modus (test_mode=true): Einmalige Ausführung
    - Live-Session (headless=false): Browser bleibt offen
    - Scheduler (headless=true): Stündliche Jobs
    """
    config_path = Path(__file__).parent / "config.yaml"
    
    # Konfiguration laden
    try:
        config = BotConfig.from_yaml(config_path)
        config.validate()
        
        # Discord Webhook Logging aktivieren (falls konfiguriert)
        if config.discord_webhook:
            from services.bot_logger import setup_discord_logging
            setup_discord_logging(config.discord_webhook)
            
        logger.info("✅ Konfiguration geladen und validiert")
        logger.info(f"   Modus: {config.mode} (Dauerbetrieb: {'Nein (Test-Modus)' if config.test_mode else 'Ja (24/7)'})")
    except Exception as e:
        logger.critical(f"💥 Config-Validierung fehlgeschlagen: {e}", exc_info=True)
        return 1
    
    # Modus auswählen
    if config.test_mode:
        return run_test_mode(config)
    elif not config.headless:
        run_live_session_mode(config)
        return 0
    else:
        run_scheduler_mode(config)
        return 0


if __name__ == '__main__':
    sys.exit(main())
