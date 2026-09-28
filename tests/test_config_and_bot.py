"""
Unit Tests für BotConfig und Logger
===================================
"""

import unittest
from pathlib import Path
import sys

# Root zum Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.bot_config import BotConfig
from services.bot_logger import get_logger, setup_bot_logging


class TestBotConfigAndLogger(unittest.TestCase):
    """Testet Konfigurations-Parsing und Logger-Erstellung."""
    
    def test_bot_config_validation(self):
        """Testet Validierung der Konfiguration."""
        config_dict = {
            'username': 'test@example.com',
            'password': 'password123',
            'login_url': 'https://www.ea.com/ea-sports-fc/ultimate-team/web-app/',
            'mode': 'browser',
            'headless': True,
            'test_mode': False,
            'discord_webhook': 'https://discord.com/api/webhooks/123/abc'
        }
        config = BotConfig(**config_dict)
        self.assertEqual(config.username, 'test@example.com')
        self.assertEqual(config.mode, 'browser')
        self.assertTrue(config.headless)
        self.assertEqual(config.discord_webhook, 'https://discord.com/api/webhooks/123/abc')
        
    def test_logger_creation(self):
        """Testet dass der Logger ordnungsgemäß initialisiert wird."""
        logger = get_logger("test_module")
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "test_module")
        
    def test_signed_into_another_device_detection(self):
        """Testet die Erkennung der 'Signed Into Another Device' Fehlermeldung."""
        from ea_fc27_bot import check_already_logged_in_elsewhere
        
        class MockDriver:
            page_source = (
                '<div><h2>Signed Into Another Device</h2><p>Sorry, you cannot use the FC '
                'Companion App or Web App while signed into Football Ultimate Team on your '
                'Console or PC.</p><p>Please sign out from your Football Ultimate Team account '
                'on your console by backing out of the mode to the main FC Menu, and retry logging '
                'into the app.\n\nShutting off your console or PC while logged into Ultimate Team '
                'will not log you out of the mode properly.</p><button class="btn-standard primary">Retry</button></div>'
            )
            def find_elements(self, by, value):
                return []
                
        driver = MockDriver()
        self.assertTrue(check_already_logged_in_elsewhere(driver))


if __name__ == '__main__':
    unittest.main()
