"""
✅ Config-Validierung für EA FC27 WebApp Bot
============================================
Validiert config.yaml beim Bot-Start und gibt hilfreiche Fehlermeldungen.

Usage:
    from config_validator import validate_config, ConfigValidationError
    
    try:
        config = validate_config('config.yaml')
    except ConfigValidationError as e:
        print(f"Config-Fehler: {e}")
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


class ConfigValidationError(Exception):
    """Custom Exception für Config-Validierungsfehler."""
    pass


@dataclass
class ValidationResult:
    """Ergebnis der Validierung."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def __str__(self):
        result = []
        if self.errors:
            result.append("❌ FEHLER:")
            for error in self.errors:
                result.append(f"  • {error}")
        if self.warnings:
            result.append("\n⚠️ WARNUNGEN:")
            for warning in self.warnings:
                result.append(f"  • {warning}")
        return "\n".join(result)


class ConfigValidator:
    """Validiert Bot-Konfiguration."""
    
    # Pflichtfelder mit Typ und Beschreibung
    REQUIRED_FIELDS = {
        'mode': (str, "Bot-Modus ('browser' oder 'api')"),
        'headless': (bool, "Browser-Modus (true/false)"),
        'login_url': (str, "EA WebApp URL"),
        'username': (str, "EA Account Username/Email"),
        'password': (str, "EA Account Passwort"),
        'ui_selectors': (dict, "UI-Selektoren Dictionary"),
    }
    
    # Optionale Felder mit Defaults
    OPTIONAL_FIELDS = {
        'test_mode': (bool, False),
        'schedule': (dict, {'type': 'interval', 'hours': 1}),
    }
    
    # Erlaubte Werte für bestimmte Felder
    ALLOWED_VALUES = {
        'mode': ['browser', 'api'],
    }
    
    # UI-Selektoren die vorhanden sein müssen
    REQUIRED_SELECTORS = [
        'primary_login_button',
        'username',
        'password',
        'next_button',
        'sign_in_button',
        'transfer_tab',
        'transfer_tile',
        'transfer_list_items',
        'player_name',
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialisiert Validator mit Config-Dictionary.
        
        Args:
            config: Geladenes config.yaml als Dictionary
        """
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self) -> ValidationResult:
        """
        Führt vollständige Validierung durch.
        
        Returns:
            ValidationResult mit Errors und Warnings
        """
        self._validate_required_fields()
        self._validate_types()
        self._validate_values()
        self._validate_selectors()
        self._validate_credentials()
        self._check_optional_fields()
        
        is_valid = len(self.errors) == 0
        return ValidationResult(is_valid, self.errors, self.warnings)
    
    def _validate_required_fields(self):
        """Prüft ob alle Pflichtfelder vorhanden sind."""
        for field, (field_type, description) in self.REQUIRED_FIELDS.items():
            if field not in self.config:
                self.errors.append(
                    f"Pflichtfeld '{field}' fehlt ({description})"
                )
    
    def _validate_types(self):
        """Prüft Typen aller Felder."""
        for field, (expected_type, description) in self.REQUIRED_FIELDS.items():
            if field in self.config:
                actual_value = self.config[field]
                if not isinstance(actual_value, expected_type):
                    actual_type = type(actual_value).__name__
                    expected_type_name = expected_type.__name__
                    self.errors.append(
                        f"Feld '{field}' hat falschen Typ: "
                        f"erwartet {expected_type_name}, ist {actual_type}"
                    )
    
    def _validate_values(self):
        """Prüft ob Werte in erlaubtem Bereich sind."""
        for field, allowed in self.ALLOWED_VALUES.items():
            if field in self.config:
                value = self.config[field]
                if value not in allowed:
                    self.errors.append(
                        f"Feld '{field}' hat ungültigen Wert '{value}'. "
                        f"Erlaubt: {', '.join(allowed)}"
                    )
        
        # URL-Validierung
        if 'login_url' in self.config:
            url = self.config['login_url']
            if not url.startswith(('http://', 'https://')):
                self.errors.append(
                    f"Feld 'login_url' muss mit http:// oder https:// beginnen"
                )
    
    def _validate_selectors(self):
        """Prüft ob alle UI-Selektoren vorhanden sind."""
        if 'ui_selectors' not in self.config:
            return  # Bereits in _validate_required_fields behandelt
        
        selectors = self.config['ui_selectors']
        
        if not isinstance(selectors, dict):
            return  # Bereits in _validate_types behandelt
        
        for selector in self.REQUIRED_SELECTORS:
            if selector not in selectors:
                self.errors.append(
                    f"UI-Selector '{selector}' fehlt in ui_selectors"
                )
            elif not selectors[selector]:
                self.warnings.append(
                    f"UI-Selector '{selector}' ist leer"
                )
    
    def _validate_credentials(self):
        """Prüft Credentials auf offensichtliche Probleme."""
        if 'username' in self.config:
            username = self.config['username']
            
            # Prüfe ob Beispiel-Wert
            if username in ['deine-email@example.com', 'your-email@example.com', '']:
                self.errors.append(
                    "Feld 'username' enthält Beispiel-Wert. "
                    "Bitte trage deine echte EA-Email ein!"
                )
            
            # Prüfe Email-Format (basic)
            elif '@' not in username:
                self.warnings.append(
                    "Feld 'username' sieht nicht wie Email aus (fehlt '@')"
                )
        
        if 'password' in self.config:
            password = self.config['password']
            
            # Prüfe ob Beispiel-Wert
            if password in ['dein-passwort', 'your-password', '']:
                self.errors.append(
                    "Feld 'password' enthält Beispiel-Wert. "
                    "Bitte trage dein echtes EA-Passwort ein!"
                )
            
            # Prüfe Passwort-Stärke (Warnung)
            elif len(password) < 8:
                self.warnings.append(
                    "Passwort ist sehr kurz (< 8 Zeichen). "
                    "Ist das wirklich dein EA-Passwort?"
                )
    
    def _check_optional_fields(self):
        """Prüft optionale Felder und gibt Hinweise."""
        # Schedule-Validierung
        if 'schedule' in self.config:
            schedule = self.config['schedule']
            if isinstance(schedule, dict):
                if 'type' in schedule and schedule['type'] == 'interval':
                    if 'hours' not in schedule and 'minutes' not in schedule:
                        self.warnings.append(
                            "schedule.type='interval' aber keine hours/minutes angegeben"
                        )


def validate_config(config_path: str | Path) -> Dict[str, Any]:
    """
    Lädt und validiert Config-Datei.
    
    Args:
        config_path: Pfad zu config.yaml
    
    Returns:
        Validiertes Config-Dictionary
    
    Raises:
        ConfigValidationError: Wenn Config ungültig
        FileNotFoundError: Wenn Config-Datei nicht existiert
    """
    config_path = Path(config_path)
    
    # Prüfe ob Datei existiert
    if not config_path.exists():
        raise FileNotFoundError(
            f"❌ Config-Datei nicht gefunden: {config_path}\n\n"
            f"💡 Tipp: Kopiere config.example.yaml zu config.yaml:\n"
            f"   cp config.example.yaml config.yaml"
        )
    
    # Lade YAML
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigValidationError(
            f"❌ Config-Datei ist kein gültiges YAML:\n{e}"
        )
    
    if not isinstance(config, dict):
        raise ConfigValidationError(
            "❌ Config-Datei muss ein YAML-Dictionary sein"
        )
    
    # Prüfe ob .env vorhanden ist und merge Credentials
    try:
        import os
        from dotenv import load_dotenv
        env_file = Path(config_path).parent / '.env'
        if env_file.exists():
            load_dotenv(env_file, override=True)
        if os.environ.get('EA_USERNAME'):
            config['username'] = os.environ.get('EA_USERNAME')
        if os.environ.get('EA_PASSWORD'):
            config['password'] = os.environ.get('EA_PASSWORD')
        if os.environ.get('EA_LOGIN_URL'):
            config['login_url'] = os.environ.get('EA_LOGIN_URL')
    except Exception:
        pass
    
    # Validiere Config
    validator = ConfigValidator(config)
    result = validator.validate()
    
    # Bei Fehlern: Exception werfen
    if not result.is_valid:
        raise ConfigValidationError(
            f"\n❌ CONFIG-VALIDIERUNG FEHLGESCHLAGEN\n"
            f"{'='*60}\n\n"
            f"{result}\n\n"
            f"{'='*60}\n"
            f"Bitte korrigiere die Fehler in {config_path}"
        )
    
    # Bei Warnungen: Ausgeben aber fortfahren
    if result.warnings:
        print(f"\n⚠️ CONFIG-WARNUNGEN\n{'='*60}")
        print(result)
        print("="*60 + "\n")
    
    return config


def validate_config_silent(config: Dict[str, Any]) -> ValidationResult:
    """
    Validiert Config ohne Exceptions zu werfen.
    Nützlich für Tests.
    
    Args:
        config: Config-Dictionary
    
    Returns:
        ValidationResult
    """
    validator = ConfigValidator(config)
    return validator.validate()


# Beispiel-Usage / Tests
if __name__ == '__main__':
    print("🧪 Config-Validator Tests\n")
    
    # Test 1: Minimale gültige Config
    print("Test 1: Minimale Config")
    minimal_config = {
        'mode': 'browser',
        'headless': False,
        'login_url': 'https://www.ea.com/fifa/ultimate-team/web-app/',
        'username': 'test@example.com',
        'password': 'test12345',
        'ui_selectors': {
            'primary_login_button': 'button',
            'username': 'input[name="email"]',
            'password': 'input[name="password"]',
            'next_button': '#next',
            'sign_in_button': '#signin',
            'transfer_tab': '.transfer',
            'transfer_tile': '.tile',
            'transfer_list_items': '.item',
            'player_name': '.name',
        }
    }
    result = validate_config_silent(minimal_config)
    print(f"✓ Valid: {result.is_valid}")
    if result.warnings:
        print(f"  Warnings: {len(result.warnings)}")
    
    # Test 2: Fehlerhafte Config
    print("\nTest 2: Fehlerhafte Config")
    bad_config = {
        'mode': 'invalid',  # Falscher Wert
        'headless': 'yes',  # Falscher Typ
        # login_url fehlt
        'username': 'deine-email@example.com',  # Beispiel-Wert
        'password': '123',  # Zu kurz
    }
    result = validate_config_silent(bad_config)
    print(f"✓ Valid: {result.is_valid}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Warnings: {len(result.warnings)}")
    
    print("\n✅ Tests abgeschlossen")
