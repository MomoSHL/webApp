"""
⚙️ Bot Configuration Management
================================
Type-safe Configuration mit Dataclasses.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import os


@dataclass
class ScheduleConfig:
    """Schedule-Konfiguration."""
    type: str = 'interval'
    hours: int = 1
    minutes: int = 0
    
    def __post_init__(self):
        """Validierung."""
        if self.type not in ['interval', 'cron']:
            raise ValueError(f"Invalid schedule type: {self.type}")
        if self.hours < 0 or self.minutes < 0:
            raise ValueError("Hours and minutes must be positive")


# UISelectors stored as Dict for flexibility with config.yaml structure
# config.yaml has fields like: primary_login_button, username, password, transfer_tab, etc.
UISelectors = Dict[str, str]


@dataclass
class BotConfig:
    """
    Haupt-Konfiguration für EA FC27 Bot.
    
    Attributes:
        username: EA Account Email
        password: EA Account Passwort
        login_url: WebApp Login URL
        mode: Bot-Modus ('browser' oder 'api')
        headless: Browser im Headless-Modus
        test_mode: Einmalige Ausführung
        schedule: Schedule-Konfiguration
        ui_selectors: UI-Selektoren
        delays: Verzögerungen in Sekunden
    """
    
    # Pflichtfelder
    username: str
    password: str
    login_url: str
    
    # Optional mit Defaults
    mode: str = 'browser'
    headless: bool = True
    test_mode: bool = False
    
    # NEU: Chrome Binary Pfad (optional, für Linux ohne Root)
    chrome_binary: Optional[str] = None
    
    # Nested Config
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    ui_selectors: Dict[str, str] = field(default_factory=dict)
    
    # Delays
    delays: Dict[str, float] = field(default_factory=lambda: {
        'min': 0.3,
        'max': 1.5,
        'after_login': 2.0,
        'after_page_load': 1.0
    })
    
    # Paths
    cookies_dir: Path = field(default_factory=lambda: Path('cookies'))
    
    def __post_init__(self):
        """Post-Init Validierung und Konvertierung."""
        # Konvertiere schedule zu ScheduleConfig wenn Dict
        if isinstance(self.schedule, dict):
            self.schedule = ScheduleConfig(**self.schedule)
        
        # ui_selectors bleibt als Dict - keine Konvertierung nötig
        
        # Konvertiere cookies_dir zu Path
        if isinstance(self.cookies_dir, str):
            self.cookies_dir = Path(self.cookies_dir)
        
        # Erstelle cookies_dir
        self.cookies_dir.mkdir(exist_ok=True)
        
        # NEU: Expandiere ~ im chrome_binary Pfad und stelle sicher dass es ein String ist
        if self.chrome_binary:
            # Konvertiere zu String falls es kein String ist
            if not isinstance(self.chrome_binary, str):
                raise ValueError(f"chrome_binary muss ein String sein, nicht {type(self.chrome_binary)}")
            self.chrome_binary = os.path.expanduser(self.chrome_binary)
    
    @classmethod
    def from_yaml(cls, filepath: Path) -> 'BotConfig':
        """
        Lädt Config aus YAML-Datei.
        
        Args:
            filepath: Pfad zur config.yaml (String oder Path)
            
        Returns:
            BotConfig Instanz
            
        Raises:
            FileNotFoundError: Wenn Datei nicht existiert
            ValueError: Wenn YAML invalid
        """
        # Konvertiere String zu Path falls nötig
        if isinstance(filepath, str):
            filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Config-Datei nicht gefunden: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise ValueError("Config-Datei ist leer")
        
        # Extrahiere Werte aus verschachtelter Struktur
        # config.yaml hat oft: bot: { headless: true, chrome_binary: "..." }
        bot_config = data.get('bot', {})
        
        # Chrome Binary aus bot-Sektion extrahieren (falls vorhanden)
        chrome_binary = bot_config.get('chrome_binary') or data.get('chrome_binary')
        
        # .env laden (Priorität oder Fallback für Credentials)
        try:
            from dotenv import load_dotenv
            env_file = filepath.parent / '.env'
            if env_file.exists():
                load_dotenv(env_file, override=True)
        except Exception:
            pass
            
        raw_user = os.environ.get('EA_USERNAME') or data.get('username') or ''
        raw_pwd = os.environ.get('EA_PASSWORD') or data.get('password') or ''
        username = str(raw_user).strip().strip('"\'')
        password = str(raw_pwd).strip().strip('"\'')
        
        login_url = os.environ.get('EA_LOGIN_URL') or data.get('login_url') or 'https://www.ea.com/ea-sports-fc/ultimate-team/web-app/'
        
        headless = data.get('headless', False)
        if 'headless' in bot_config:
            headless = bot_config.get('headless')
        if os.environ.get('EA_HEADLESS') is not None:
            headless = os.environ.get('EA_HEADLESS').strip().lower() in ('true', '1', 'yes')
            
        test_mode = data.get('test_mode', True)
        if os.environ.get('EA_TEST_MODE') is not None:
            test_mode = os.environ.get('EA_TEST_MODE').strip().lower() in ('true', '1', 'yes')
        
        # Baue flache Struktur für BotConfig
        config_data = {
            'username': username,
            'password': password,
            'login_url': login_url,
            'mode': data.get('mode', 'browser'),
            'headless': headless,
            'test_mode': test_mode,
            'chrome_binary': chrome_binary,  # Kann None sein
            'schedule': data.get('schedule', {}),
            'ui_selectors': data.get('ui_selectors', {}),
            'delays': data.get('delays', {}),
            'cookies_dir': data.get('cookies_dir', 'cookies')
        }
        
        return cls(**config_data)
    
    def to_yaml(self, filepath: Path) -> None:
        """
        Speichert Config als YAML-Datei.
        
        Args:
            filepath: Pfad zur Zieldatei
        """
        data = {
            'username': self.username,
            'password': self.password,
            'login_url': self.login_url,
            'mode': self.mode,
            'headless': self.headless,
            'test_mode': self.test_mode,
            'schedule': {
                'type': self.schedule.type,
                'hours': self.schedule.hours,
                'minutes': self.schedule.minutes
            },
            'delays': self.delays
        }
        
        # NEU: Chrome Binary nur speichern wenn gesetzt
        if self.chrome_binary:
            data['chrome_binary'] = self.chrome_binary
        
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    def validate(self) -> bool:
        """
        Validiert die Konfiguration.
        
        Returns:
            True wenn gültig
            
        Raises:
            ValueError: Bei ungültiger Konfiguration
        """
        # Username Check
        if not self.username or '@' not in self.username:
            raise ValueError("Ungültige Email-Adresse")
        
        # Password Check
        if not self.password or len(self.password) < 8:
            raise ValueError("Passwort muss mindestens 8 Zeichen haben")
        
        # URL Check
        if not self.login_url.startswith('http'):
            raise ValueError("Login-URL muss mit http:// oder https:// beginnen")
        
        # Mode Check
        if self.mode not in ['browser', 'api']:
            raise ValueError("Mode muss 'browser' oder 'api' sein")
        
        # NEU: Chrome Binary Check (falls gesetzt)
        if self.chrome_binary and not os.path.exists(self.chrome_binary):
            raise ValueError(f"Chrome Binary nicht gefunden: {self.chrome_binary}")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Konvertiert Config zu Dict (für Legacy-Funktionen).
        
        Returns:
            Dict mit allen Config-Werten
        """
        result = {
            'username': self.username,
            'password': self.password,
            'login_url': self.login_url,
            'mode': self.mode,
            'headless': self.headless,
            'test_mode': self.test_mode,
            'schedule': {
                'type': self.schedule.type,
                'hours': self.schedule.hours,
                'minutes': self.schedule.minutes
            },
            'ui_selectors': self.ui_selectors,
            'delays': self.delays,
            'cookies_dir': str(self.cookies_dir)
        }
        
        # NEU: Chrome Binary nur hinzufügen wenn gesetzt
        if self.chrome_binary:
            result['chrome_binary'] = self.chrome_binary
        
        return result
    
    @property
    def cookie_file(self) -> Path:
        """Pfad zur Cookie-Datei für diesen User."""
        safe_username = self.username.replace('@', '_at_').replace('.', '_')
        return self.cookies_dir / f"cookies_{safe_username}.pkl"
    
    def __repr__(self) -> str:
        """String-Repräsentation (ohne Passwort)."""
        chrome_info = f", chrome_binary='{self.chrome_binary}'" if self.chrome_binary else ""
        return (
            f"BotConfig("
            f"username='{self.username}', "
            f"mode='{self.mode}', "
            f"headless={self.headless}, "
            f"test_mode={self.test_mode}"
            f"{chrome_info}"
            ")"
        )


# Convenience Function
def load_config(filepath: str = "config.yaml") -> BotConfig:
    """
    Lädt Bot-Konfiguration aus Datei.
    
    Args:
        filepath: Pfad zur Config-Datei (Standard: config.yaml)
        
    Returns:
        BotConfig Instanz
    """
    return BotConfig.from_yaml(Path(filepath))


if __name__ == '__main__':
    # Test (muss aus parent directory ausgeführt werden)
    import sys
    from pathlib import Path
    
    # Füge parent directory zu sys.path hinzu
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    
    # Absolute Import
    from services.bot_config import BotConfig
    
    config_path = parent_dir / "config.yaml"
    config = BotConfig.from_yaml(config_path)
    print(f"✅ Config geladen: {config}")
    print(f"📁 Cookie-Datei: {config.cookie_file}")
    config.validate()
    print("✅ Config ist gültig")
