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


if __name__ == '__main__':
    unittest.main()
