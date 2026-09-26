"""
🎮 Bot Session Management
==========================
Verwaltet Browser-Sessions und State.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import pickle

from selenium import webdriver
from .bot_config import BotConfig
from .bot_logger import get_logger

logger = get_logger(__name__)


@dataclass
class SessionState:
    """Session-State Management."""
    
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # Status
    is_logged_in: bool = False
    cookies_loaded: bool = False
    login_attempts: int = 0
    last_status: Optional[str] = None  # z.B. 'already_logged_in', 'success', etc.
    
    # Operations
    relist_count: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> float:
        """Session-Dauer in Sekunden."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def add_error(self, error: str):
        """Fügt Fehler hinzu."""
        self.errors.append(error)
        logger.error(f"❌ Session Error: {error}")
    
    def add_warning(self, warning: str):
        """Fügt Warnung hinzu."""
        self.warnings.append(warning)
        logger.warning(f"⚠️ Session Warning: {warning}")


class BotSession:
    """
    Bot Session Management.
    
    Verwaltet:
    - Browser-Instanz
    - Login-State
    - Cookies
    - Session-Statistiken
    """
    
    def __init__(self, config: BotConfig):
        """
        Initialisiert Bot-Session.
        
        Args:
            config: Bot-Konfiguration
        """
        self.config = config
        self.driver: Optional[webdriver.Chrome] = None
        self.state = SessionState(
            session_id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        logger.info(f"🎮 Session initialisiert: {self.state.session_id}")
    
    @property
    def is_active(self) -> bool:
        """Prüft ob Session aktiv ist."""
        if not self.driver:
            return False
        
        try:
            # Prüfe ob Browser noch läuft
            _ = self.driver.window_handles
            return True
        except Exception:
            return False
    
    def load_cookies(self) -> bool:
        """
        Lädt gespeicherte Cookies.
        
        Returns:
            True wenn erfolgreich geladen
        """
        cookie_file = self.config.cookie_file
        
        if not cookie_file.exists():
            logger.debug("🍪 Keine gespeicherten Cookies gefunden")
            return False
        
        try:
            with open(cookie_file, 'rb') as f:
                cookies = pickle.load(f)
            
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Cookie nicht geladen: {e}")
            
            self.state.cookies_loaded = True
            logger.info(f"✅ {len(cookies)} Cookies geladen")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Cookies konnten nicht geladen werden: {e}")
            return False
    
    def save_cookies(self) -> bool:
        """
        Speichert aktuelle Cookies.
        
        Returns:
            True wenn erfolgreich gespeichert
        """
        if not self.driver:
            return False
        
        try:
            cookies = self.driver.get_cookies()
            cookie_file = self.config.cookie_file
            
            with open(cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            
            logger.info(f"✅ {len(cookies)} Cookies gespeichert")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cookies speichern fehlgeschlagen: {e}")
            return False
    
    def close(self):
        """Schließt Session und Browser."""
        logger.info("🔚 Schließe Session...")
        
        # Speichere Cookies vor dem Schließen
        if self.driver and self.state.is_logged_in:
            try:
                self.save_cookies()
            except:
                pass  # Ignoriere Fehler beim Cookie-Speichern
        
        # Schließe Browser (mit verbessertem Error-Handling)
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✅ Browser geschlossen")
                
            except OSError as e:
                # Windows Handle-Fehler ignorieren
                if "WinError 6" in str(e) or "Handle ist ungültig" in str(e):
                    logger.debug(f"   ℹ️  Browser-Cleanup-Warnung ignoriert")
                else:
                    logger.debug(f"   ℹ️  Browser-Cleanup: {e}")
            except Exception as e:
                logger.debug(f"   ℹ️  Browser bereits geschlossen oder Fehler: {e}")
            finally:
                self.driver = None
        
        # Markiere Session als beendet
        self.state.end_time = datetime.now()
        logger.info(f"✅ Session beendet (Dauer: {self.state.duration:.1f}s)")
    
    def __enter__(self):
        """Context Manager: Eintritt."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager: Austritt."""
        self.close()
        return False  # Exception nicht unterdrücken
    
    def __repr__(self) -> str:
        """String-Repräsentation."""
        status = "aktiv" if self.is_active else "inaktiv"
        login = "✅" if self.state.is_logged_in else "❌"
        return (
            f"BotSession("
            f"id='{self.state.session_id}', "
            f"status='{status}', "
            f"logged_in={login}, "
            f"duration={self.state.duration:.1f}s"
            ")"
        )


# Convenience Function
def create_session(config: BotConfig) -> BotSession:
    """
    Erstellt neue Bot-Session.
    
    Args:
        config: Bot-Konfiguration
        
    Returns:
        BotSession Instanz
    """
    return BotSession(config)


if __name__ == '__main__':
    # Test (muss aus parent directory ausgeführt werden)
    import sys
    from pathlib import Path
    
    # Füge parent directory zu sys.path hinzu
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    
    # Jetzt absolute Imports verwenden
    from services.bot_config import BotConfig
    from services.bot_session import create_session
    
    config_path = parent_dir / "config.yaml"
    config = BotConfig.from_yaml(config_path)
    
    with create_session(config) as session:
        print(f"✅ Session erstellt: {session}")
        print(f"📊 Aktiv: {session.is_active}")
        print(f"🔐 Eingeloggt: {session.state.is_logged_in}")
