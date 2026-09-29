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

    def test_dismiss_all_popups(self):
        """Testet automatisches Erkennen und Schließen von News/Info-Popouts."""
        from ea_fc27_bot import dismiss_all_popups
        
        class MockElement:
            def __init__(self, text="Continue"):
                self.text = text
                self.clicked = False
            def is_displayed(self):
                return True
            def is_enabled(self):
                return True
            def click(self):
                self.clicked = True
                
        btn = MockElement("Continue")
        
        class MockDriver:
            page_source = '<div><h2>What is New in Ultimate Team</h2></div>'
            def find_elements(self, by, value):
                if "Continue" in value or "btn-standard" in value:
                    return [btn]
                return []
            def execute_script(self, script, *args):
                pass
                
        driver = MockDriver()
        count = dismiss_all_popups(driver, max_passes=1)
        self.assertEqual(count, 1)
        self.assertTrue(btn.clicked)

    def test_dismiss_livemessage_popup(self):
        """Testet das Schließen der spezifischen EA 'MESSAGE FROM THE FC TEAM' Livemessage Popout."""
        from ea_fc27_bot import dismiss_all_popups
        
        class MockBtn:
            def __init__(self, text, displayed=True):
                self.text = text
                self._displayed = displayed
                self.clicked = False
            def is_displayed(self):
                return self._displayed
            def is_enabled(self):
                return True
            def click(self):
                self.clicked = True
                
        check_out_btn = MockBtn("Check it Out", displayed=False)
        continue_btn = MockBtn("Continue", displayed=True)
        
        class MockDriver:
            page_source = (
                '<div class="ut-livemessage" style="width: 800px; max-width: 90%;">'
                '<header class="ut-livemessage-header">'
                '<h1>MESSAGE FROM THE FC TEAM</h1><h2>PLAY EA SPORTS FC™ 27 NOW</h2>'
                '</header>'
                '<div class="ut-livemessage-footer">'
                '<button class="btn-standard primary" style="display: none;">Check it Out</button>'
                '<button class="btn-standard primary">Continue</button>'
                '</div></div>'
            )
            def find_elements(self, by, value):
                if "ut-livemessage" in value or "Continue" in value or "btn-standard" in value:
                    return [check_out_btn, continue_btn]
                return []
            def execute_script(self, script, *args):
                pass
                
        driver = MockDriver()
        count = dismiss_all_popups(driver, max_passes=1)
        self.assertEqual(count, 1)
        self.assertFalse(check_out_btn.clicked)
        self.assertTrue(continue_btn.clicked)


if __name__ == '__main__':
    unittest.main()
