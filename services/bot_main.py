"""
🤖 Main Bot Class
==================
Hauptklasse für EA FC27 WebApp Bot mit allen Operations.
"""

from typing import Optional, Tuple
import time
from datetime import datetime, timedelta

from selenium import webdriver
import undetected_chromedriver as uc

from .bot_config import BotConfig
from .bot_session import BotSession
from .bot_logger import get_logger
from .bot_stats import BotStatistics

logger = get_logger(__name__)


class EAFC27Bot:
    """
    Haupt-Bot-Klasse für EA FC27 WebApp Automation.
    
    Features:
    - Login mit Cookie-Management
    - 2FA-Unterstützung
    - Transfer List Re-Listing
    - Anti-Detection
    - Error-Recovery
    - Statistics-Tracking
    """
    
    def __init__(self, config: BotConfig):
        """
        Initialisiert Bot.
        
        Args:
            config: Bot-Konfiguration
        """
        self.config = config
        self.session: Optional[BotSession] = None
        self.stats = BotStatistics()
        
        logger.info(f"🤖 Bot initialisiert: {config.mode} mode")
    
    def init_browser(self, headless: bool = True) -> webdriver.Chrome:
        """
        Initialisiert Browser mit Anti-Detection.
        
        Args:
            headless: Browser im Headless-Modus
            
        Returns:
            Chrome WebDriver
        """
        logger.info("🌐 Initialisiere Browser...")
        
        options = uc.ChromeOptions()
        
        if headless:
            options.add_argument('--headless=new')
        
        # Anti-Detection Features
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-gpu-blocklist')
        options.add_argument('--enable-webgl')
        options.add_argument('--enable-accelerated-2d-canvas')
        
        # User Agent (immer Windows für EA Kompatibilität)
        from .browser_utils import get_platform_user_agent, apply_stealth_overrides
        ua = get_platform_user_agent()
        options.add_argument(f'--user-agent={ua}')
        options.add_argument('--lang=de-DE')
        
        # NEU: Chrome Binary aus Config (falls gesetzt)
        if self.config.chrome_binary:
            import os
            chrome_binary = os.path.expanduser(self.config.chrome_binary)
            if os.path.exists(chrome_binary):
                options.binary_location = chrome_binary
                logger.info(f"🔧 Using custom Chrome: {chrome_binary}")
            else:
                logger.warning(f"⚠️ Chrome binary not found: {chrome_binary}")
        
        # Erstelle Driver
        try:
            driver = uc.Chrome(options=options, version_main=None)
            
            # Stealth & Windows-Spoofing Overrides via CDP
            apply_stealth_overrides(driver, ua)
            
            # Kleine Pause damit Browser richtig startet
            import time
            time.sleep(1)
            
            # Viewport randomisieren (nur wenn Browser-Fenster existiert)
            try:
                import random
                width = random.randint(1600, 1920)
                height = random.randint(900, 1080)
                driver.set_window_size(width, height)
                logger.info(f"✅ Browser initialisiert ({width}x{height})")
            except Exception as e:
                # In headless oder bei Problemen: Ignoriere window size Fehler
                logger.debug(f"   ℹ️  Window size nicht gesetzt: {e}")
                logger.info(f"✅ Browser initialisiert (headless={headless})")
            
            return driver
            
        except Exception as e:
            logger.error(f"❌ Browser-Init fehlgeschlagen: {e}")
            raise
    
    def start_session(self) -> BotSession:
        """
        Startet neue Bot-Session.
        
        Returns:
            BotSession Instanz
        """
        if self.session and self.session.is_active:
            logger.warning("⚠️ Session bereits aktiv")
            return self.session
        
        self.session = BotSession(self.config)
        self.session.driver = self.init_browser(headless=self.config.headless)
        
        logger.info("✅ Session gestartet")
        return self.session
    
    def login(self) -> bool:
        """
        Führt Login durch (mit Cookie-Management).
        
        Returns:
            True wenn erfolgreich
        """
        if not self.session or not self.session.driver:
            logger.error("❌ Keine aktive Session")
            return False
        
        logger.info("🔐 Starte Login...")
        start_time = time.time()
        
        try:
            # Importiere Login-Funktion aus Services
            from .login_service import login_via_ui
            
            # Konvertiere Config zu Dict für Legacy-Funktion
            config_dict = self.config.to_dict()
            
            result = login_via_ui(self.session.driver, config_dict)
            duration = time.time() - start_time
            
            # Update State
            self.session.state.login_attempts += 1
            self.session.state.is_logged_in = (result is True)
            
            # Track Statistics
            self.stats.record_login(
                success=(result is True),
                duration=duration,
                error=None if result else "Login fehlgeschlagen"
            )
            
            if result is True:
                logger.info(f"✅ Login erfolgreich ({duration:.1f}s)")
                return True
            elif result is None:
                self.session.state.last_status = "already_logged_in"
                logger.warning(f"⚠️ WebApp nicht verfügbar: Bereits auf anderem Gerät angemeldet ({duration:.1f}s)")
                return None
            else:
                self.session.state.last_status = "login_failed"
                logger.error(f"❌ Login fehlgeschlagen ({duration:.1f}s)")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Login-Fehler: {e}", exc_info=True)
            
            self.stats.record_login(
                success=False,
                duration=duration,
                error=str(e)
            )
            
            return False
    
    def relist_all(self) -> int:
        """
        Listet alle Transfer-Spieler neu an.
        
        Returns:
            Anzahl neu gelisteter Spieler
        """
        if not self.session or not self.session.driver:
            logger.error("❌ Keine aktive Session")
            return -1
        
        logger.info("🔄 Starte Re-List...")
        start_time = time.time()
        
        try:
            # Importiere Re-List Funktion aus Services
            from .relist_service import relist_all_transfer_items
            
            # Konvertiere Config zu Dict für Legacy-Funktion
            config_dict = self.config.to_dict()
            
            count = relist_all_transfer_items(self.session.driver, config_dict)
            duration = time.time() - start_time
            
            # Update State
            self.session.state.relist_count += count if count > 0 else 0
            
            # Track Statistics
            self.stats.record_relist(
                success=(count >= 0),
                players=count if count > 0 else 0,
                duration=duration,
                error=None if count >= 0 else "Re-List fehlgeschlagen"
            )
            
            if count > 0:
                logger.info(f"✅ {count} Spieler neu gelistet ({duration:.1f}s)")
            elif count == 0:
                logger.info(f"ℹ️ Keine abgelaufenen Spieler ({duration:.1f}s)")
            else:
                logger.error(f"❌ Re-List fehlgeschlagen ({duration:.1f}s)")
            
            return count
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Re-List-Fehler: {e}", exc_info=True)
            
            self.stats.record_relist(
                success=False,
                players=0,
                duration=duration,
                error=str(e)
            )
            
            return -1
    
    def run_job(self) -> Tuple[bool, str]:
        """
        Führt kompletten Bot-Job aus (Login + Re-List).
        
        Returns:
            (success, status_message)
        """
        logger.info(f"🚀 Starte Bot-Job ({self.config.mode} mode)...")
        
        try:
            # Start Session
            if not self.session or not self.session.is_active:
                self.start_session()
            
            # Prüfe ob Session erfolgreich erstellt wurde
            if not self.session or not self.session.state:
                logger.error("❌ Session konnte nicht erstellt werden")
                return False, "session_failed"
            
            # Login
            if not self.session.state.is_logged_in:
                login_success = self.login()
                if login_success is None:
                    self.session.state.last_status = "already_logged_in"
                    logger.error("❌ Bot-Job fehlgeschlagen: Spieler konnten nicht neu angeboten werden (bereits auf anderem Gerät angemeldet)")
                    return False, "already_logged_in"
                elif not login_success:
                    self.session.state.last_status = "login_failed"
                    logger.error("❌ Bot-Job fehlgeschlagen: Login nicht erfolgreich")
                    return False, "login_failed"
            
            # Re-List
            relist_count = self.relist_all()
            
            if relist_count >= 0:
                logger.info("✅ Bot-Job erfolgreich")
                self.session.state.last_status = "success"
                return True, "success"
            else:
                logger.error("❌ Bot-Job teilweise fehlgeschlagen")
                self.session.state.last_status = "relist_failed"
                return False, "relist_failed"
                
        except Exception as e:
            logger.error(f"❌ Bot-Job fehlgeschlagen: {e}", exc_info=True)
            
            # Sicheres Setzen des Status (nur wenn session existiert)
            if self.session and hasattr(self.session, 'state') and self.session.state:
                self.session.state.last_status = "error"
            
            # Record error mit richtigem Format
            error_msg = f"{type(e).__name__}: {str(e)} (in run_job)"
            self.stats.record_error(error_msg)
            
            return False, "error"
    
    def cleanup(self):
        """Räumt Bot-Ressourcen auf."""
        logger.info("🧹 Räume auf...")
        
        # Beende Session
        if self.session:
            self.session.close()
            self.session = None
        
        # Beende Statistics
        self.stats.end_session()
        self.stats.print_summary()
        
        logger.info("✅ Aufräumen abgeschlossen")
    
    def __enter__(self):
        """Context Manager: Eintritt."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager: Austritt."""
        self.cleanup()
        return False
    
    def __repr__(self) -> str:
        """String-Repräsentation."""
        session_info = f"session={self.session.state.session_id}" if self.session else "no_session"
        return f"EAFC27Bot({session_info}, mode={self.config.mode})"


# Backward-Compatibility Alias
EAFC26Bot = EAFC27Bot


# Convenience Function
def create_bot(config_file: str = "config.yaml") -> EAFC27Bot:
    """
    Erstellt Bot-Instanz aus Config-Datei.
    
    Args:
        config_file: Pfad zur Config-Datei
        
    Returns:
        EAFC27Bot Instanz
    """
    from .bot_config import load_config
    config = load_config(config_file)
    return EAFC27Bot(config)


if __name__ == '__main__':
    # Test (muss aus parent directory ausgeführt werden)
    import sys
    from pathlib import Path
    
    # Füge parent directory zu sys.path hinzu
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    
    # Absolute Imports
    from services.bot_config import BotConfig
    from services.bot_main import EAFC27Bot
    
    config_path = parent_dir / "config.yaml"
    config = BotConfig.from_yaml(config_path)
    bot = EAFC27Bot(config)
    
    print(f"✅ Bot erstellt: {bot}")
    print(f"⚙️ Config: {bot.config}")
    
    bot.cleanup()
