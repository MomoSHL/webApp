"""
🎮 Discord Webhook Service
==========================
Sendet Bot-Logs, Relist-Erfolge und Status-Updates asynchron an Discord.
"""

import json
import logging
import queue
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional


class DiscordWebhookHandler(logging.Handler):
    """
    Logging-Handler, der formatierte Log-Einträge via Discord-Webhook sendet.
    Nutzt eine Queue und einen Background-Worker, um Blockaden im Bot zu vermeiden.
    """
    
    def __init__(self, webhook_url: str, level: int = logging.INFO):
        super().__init__(level)
        self.webhook_url = webhook_url.strip() if webhook_url else ""
        self._queue = queue.Queue(maxsize=200)
        self._stop_event = threading.Event()
        self._worker_thread = None
        
        if self.webhook_url and self.webhook_url.startswith("http"):
            self._start_worker()
            
    def _start_worker(self):
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True, name="DiscordWebhookWorker")
        self._worker_thread.start()
        
    def _process_queue(self):
        while not self._stop_event.is_set():
            try:
                record = self._queue.get(timeout=1.0)
                if record is None:
                    break
                self._send_payload(record)
                self._queue.task_done()
                time.sleep(0.5)  # Discord Rate-Limit Schutz
            except queue.Empty:
                continue
            except Exception:
                pass
                
    def _send_payload(self, record: logging.LogRecord):
        if not self.webhook_url or not self.webhook_url.startswith("http"):
            return
            
        msg = record.getMessage().strip()
        if not msg:
            return
            
        # Farb- und Icon-Wahl basierend auf Level & Inhalt
        color = 0x3498DB  # Blau (Standard)
        if record.levelno >= logging.ERROR or "❌" in msg or "💥" in msg:
            color = 0xE74C3C  # Rot
        elif record.levelno >= logging.WARNING or "⚠️" in msg:
            color = 0xF1C40F  # Gelb
        elif "✅" in msg or "Erfolg" in msg or "gelistet" in msg:
            color = 0x2ECC71  # Grün
        elif "⏳" in msg or "Countdown" in msg or "Nächster" in msg:
            color = 0x9B59B6  # Lila
        elif "📊" in msg or "📈" in msg:
            color = 0x1ABC9C  # Türkis
            
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        payload = {
            "username": "EA FC27 Bot",
            "embeds": [
                {
                    "description": msg,
                    "color": color,
                    "timestamp": timestamp,
                    "footer": {
                        "text": f"EA FC27 Relist Bot • {record.levelname}"
                    }
                }
            ]
        }
        
        try:
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.webhook_url,
                data=req_data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) EAFC27Bot/2.0'
                }
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                pass
        except Exception:
            pass

    # Filter für wichtige Discord-Benachrichtigungen (kein technischer Browser-Spam)
    IMPORTANT_INFO_PATTERNS = [
        "Login erfolgreich",
        "Login fehlgeschlagen",
        "gelistet",
        "Re-List",
        "Nächster Durchlauf",
        "NACHTPAUSE",
        "Guten Morgen",
        "2FA",
        "Auf anderem Gerät",
        "BOT-STATISTIKEN",
        "Bot gestartet",
        "Bot gestoppt",
        "SCHEDULER-MODUS",
        "LIVE-SESSION MODUS",
        "Bot pausiert",
        "Pause beendet"
    ]

    IGNORED_PATTERNS = [
        "Viewport",
        "Browser initialisiert",
        "Cookies geladen",
        "Aktualisiere Seite",
        "Cookie-Banner",
        "Warte auf",
        "Email erfolgreich",
        "geklickt",
        "Browser-Identität",
        "CDP",
        "Aufräumen",
        "Session initialisiert",
        "Session beendet",
        "Schließe Session",
        "Öffne EA",
        "Countdown: Noch"  # Zwischen-Countdowns filtern, nur den Haupttimer nach dem Job senden
    ]

    def emit(self, record: logging.LogRecord):
        if not self.webhook_url or not self.webhook_url.startswith("http"):
            return
            
        # Nur WARNING, ERROR oder ausgewählte wichtige INFO-Events
        if record.levelno < logging.INFO:
            return
            
        msg = record.getMessage().strip()
        if not msg:
            return
            
        # Wenn nur INFO: Prüfe ob es eine wichtige Statusmeldung ist
        if record.levelno == logging.INFO:
            # Technische Details ignorieren
            if any(p in msg for p in self.IGNORED_PATTERNS):
                return
            # Nur senden wenn es ein wichtiges Bot-Event ist
            if not any(p in msg for p in self.IMPORTANT_INFO_PATTERNS):
                return
                
        try:
            self._queue.put_nowait(record)
        except queue.Full:
            pass

    def close(self):
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            try:
                self._queue.put_nowait(None)
            except Exception:
                pass
        super().close()


def send_direct_discord_message(webhook_url: str, title: str, description: str, color: int = 0x3498DB) -> bool:
    """
    Sendet eine direkte formatierte Nachricht an einen Discord-Webhook.
    """
    if not webhook_url or not webhook_url.startswith("http"):
        return False
        
    payload = {
        "username": "EA FC27 Bot",
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "footer": {
                    "text": "EA FC27 Relist Bot"
                }
            }
        ]
    }
    
    try:
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=req_data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) EAFC27Bot/2.0'
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status in (200, 204)
    except Exception:
        return False
