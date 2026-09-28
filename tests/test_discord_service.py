"""
Unit Tests für Discord Service
==============================
Testet Embed-Formatierung und Filter-Logik.
"""

import unittest
from pathlib import Path
import sys
import logging
from datetime import datetime

# Root zum Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.discord_service import (
    DiscordWebhookHandler,
    send_relist_embed,
    send_device_conflict_embed
)


class TestDiscordService(unittest.TestCase):
    """Test-Suite für Discord-Webhook-Funktionalität."""
    
    def test_discord_handler_filters(self):
        """Testet welche Log-Nachrichten durchgelassen und welche gefiltert werden."""
        handler = DiscordWebhookHandler(webhook_url="", level=logging.INFO)
        
        # Test IMPORTANT messages
        important_msgs = [
            "🚀 Starte Bot-Durchlauf...",
            "🌐 Öffne EA WebApp...",
            "🍪 32 Cookies geladen",
            "🖱️ Klick auf 'Transfers'-Tab",
            "🖱️ Klick auf 'Transfer List'-Kachel",
            "🔄 Klick auf 'Re-list All'-Button",
            "✅ Bestätigung ('Yes' / 'Ja') erfolgreich geklickt",
            "⚠️ WebApp nicht verfügbar: Bereits auf anderem Gerät angemeldet (Konsole/PC)",
            "🔐 2FA-Code benötigt",
            "⏳ Job erfolgreich! Nächster Durchlauf in 65 Minuten"
        ]
        
        for msg in important_msgs:
            rec = logging.LogRecord("test", logging.INFO, "path", 1, msg, (), None)
            handler.emit(rec)
            msg_lower = msg.lower()
            is_ignored = any(p.lower() in msg_lower for p in handler.IGNORED_PATTERNS)
            is_important = any(p.lower() in msg_lower for p in handler.IMPORTANT_INFO_PATTERNS)
            self.assertFalse(is_ignored, f"Should not be ignored: {msg}")
            self.assertTrue(is_important, f"Should be recognized as important: {msg}")
            
        # Test IGNORED messages
        ignored_msgs = [
            "🖥️ Viewport: 1920x1080",
            "🔍 Browser-Identität: platform='Win32'",
            "Warte auf WebApp-Status (prüfe Cookies / Login-Button)...",
            "⏳ Countdown: Noch 15 Minuten bis zum nächsten Durchlauf"
        ]
        
        for msg in ignored_msgs:
            rec = logging.LogRecord("test", logging.INFO, "path", 1, msg, (), None)
            handler.emit(rec)
            msg_lower = msg.lower()
            is_ignored = any(p.lower() in msg_lower for p in handler.IGNORED_PATTERNS)
            self.assertTrue(is_ignored, f"Should be ignored: {msg}")

    def test_relist_embed_without_webhook(self):
        """Prüft dass send_relist_embed bei leerer URL sauber False zurückgibt."""
        res = send_relist_embed("", 37, [{'name': 'Tah', 'rating': '87', 'position': 'CB', 'count': 9}])
        self.assertFalse(res)
        
    def test_device_conflict_embed_without_webhook(self):
        """Prüft dass send_device_conflict_embed bei leerer URL sauber False zurückgibt."""
        res = send_device_conflict_embed("", 15)
        self.assertFalse(res)


if __name__ == '__main__':
    unittest.main()
