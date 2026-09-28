"""
Unit Tests für Discord Service
==============================
Testet Embed-Formatierung und Filter-Logik für gebündelte Discord-Nachrichten.
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
    send_device_conflict_embed,
    send_no_items_embed
)


class TestDiscordService(unittest.TestCase):
    """Test-Suite für Discord-Webhook-Funktionalität."""
    
    def test_discord_handler_filters_and_grouping(self):
        """Testet welche Log-Nachrichten durchgelassen und welche zur Entlastung von Discord gefiltert werden."""
        handler = DiscordWebhookHandler(webhook_url="", level=logging.INFO)
        
        # Lifecycle-Events sollten durchgelassen werden
        lifecycle_msgs = [
            "😴 NACHTPAUSE (1:00 - 6:00 Uhr)",
            "☀️ Guten Morgen! Bot setzt Arbeit fort...",
            "⏸️ Bot pausiert",
            "▶️ Pause beendet",
            "🔐 2FA-Code benötigt"
        ]
        
        for msg in lifecycle_msgs:
            rec = logging.LogRecord("test", logging.INFO, "path", 1, msg, (), None)
            handler.emit(rec)
            msg_lower = msg.lower()
            is_ignored = any(p.lower() in msg_lower for p in handler.IGNORED_PATTERNS)
            is_important = any(p.lower() in msg_lower for p in handler.IMPORTANT_INFO_PATTERNS)
            self.assertFalse(is_ignored, f"Lifecycle message should not be ignored: {msg}")
            self.assertTrue(is_important, f"Lifecycle message should be recognized as important: {msg}")
            
        # Routine-Aktionen & Micro-Klicks sollen NICHT einzeln als Chat-Spam gesendet werden
        # (diese werden kompakt in Rich Embeds zusammengefasst)
        routine_ignored_msgs = [
            "🌐 Öffne EA WebApp...",
            "🍪 32 Cookies geladen",
            "🖱️ Klick auf 'Transfers'-Tab",
            "🖱️ Klick auf 'Transfer List'-Kachel",
            "🔄 Klick auf 'Re-list All'-Button",
            "✅ Bestätigung ('Yes' / 'Ja') erfolgreich geklickt",
            "🖥️ Viewport: 1920x1080",
            "🔍 Browser-Identität: platform='Win32'",
            "Warte auf WebApp-Status (prüfe Cookies / Login-Button)...",
            "⏳ Countdown: Noch 15 Minuten bis zum nächsten Durchlauf",
            "📋 37 abgelaufene Spieler auf der Transferliste erkannt (9 verschiedene):"
        ]
        
        for msg in routine_ignored_msgs:
            rec = logging.LogRecord("test", logging.INFO, "path", 1, msg, (), None)
            handler.emit(rec)
            msg_lower = msg.lower()
            is_ignored = any(p.lower() in msg_lower for p in handler.IGNORED_PATTERNS)
            self.assertTrue(is_ignored, f"Routine log should be ignored to prevent spam: {msg}")

    def test_relist_embed_without_webhook(self):
        """Prüft dass send_relist_embed bei leerer URL sauber False zurückgibt."""
        res = send_relist_embed("", 37, [{'name': 'Tah', 'rating': '87', 'position': 'CB', 'count': 9}])
        self.assertFalse(res)
        
    def test_device_conflict_embed_without_webhook(self):
        """Prüft dass send_device_conflict_embed bei leerer URL sauber False zurückgibt."""
        res = send_device_conflict_embed("", 15)
        self.assertFalse(res)

    def test_no_items_embed_without_webhook(self):
        """Prüft dass send_no_items_embed bei leerer URL sauber False zurückgibt."""
        res = send_no_items_embed("")
        self.assertFalse(res)


if __name__ == '__main__':
    unittest.main()

