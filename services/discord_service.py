"""
🎮 Discord Webhook Service
==========================
Sendet gebündelte Bot-Status-Updates, Relist-Ergebnisse und Warnungen an Discord.
Verhindert Nachrichten-Spam durch thematische Gruppierung (z.B. Re-List Embed, Status Embeds).
"""

import json
import logging
import queue
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, List, Dict, Any


class DiscordWebhookHandler(logging.Handler):
    """
    Logging-Handler für globale Bot-Events (Warnungen, Fehler, Nachtpause, Pause/Resume).
    Routine-Aktionen wie einzelne Klicks werden nicht einzeln gesendet, sondern gebündelt.
    """
    
    # Nur übergeordnete Lifecycle-Events & Pausen über den Logger senden
    IMPORTANT_INFO_PATTERNS = [
        "NACHTPAUSE",
        "Guten Morgen",
        "Bot pausiert",
        "Pause beendet",
        "Bot gestartet",
        "Bot gestoppt",
        "SCHEDULER-MODUS",
        "LIVE-SESSION MODUS",
        "TEST-MODUS",
        "2FA"
    ]

    IGNORED_PATTERNS = [
        "Viewport",
        "Browser-Identität",
        "CDP",
        "Window size",
        "Warte auf",
        "Cookie-Banner",
        "Countdown: Noch",
        "Cookies geladen",
        "Cookies gespeichert",
        "Öffne EA WebApp",
        "Klick auf",
        "geklickt",
        "Bestätigung",
        "Re-list",
        "ERFOLGREICH NEU ANGEBOTEN",
        "abgelaufene Spieler auf der Transferliste erkannt",
        "Nächster Durchlauf",
        "Job erfolgreich"
    ]
    
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
        color = 0x3498DB  # Blau
        if record.levelno >= logging.ERROR or "❌" in msg or "💥" in msg:
            color = 0xE74C3C  # Rot
        elif record.levelno >= logging.WARNING or "⚠️" in msg:
            color = 0xF1C40F  # Gelb / Orange
        elif "✅" in msg:
            color = 0x2ECC71  # Grün
        elif "😴" in msg or "⏸️" in msg:
            color = 0x9B59B6  # Lila
            
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

    def emit(self, record: logging.LogRecord):
        if not self.webhook_url or not self.webhook_url.startswith("http"):
            return
            
        msg = record.getMessage().strip()
        if not msg:
            return
            
        msg_lower = msg.lower()
        
        # Ignoriere Nachrichten, die bereits über spezialisierte Embeds gesendet werden
        if any(p.lower() in msg_lower for p in self.IGNORED_PATTERNS):
            return
            
        # WARNING, ERROR oder CRITICAL senden (falls nicht ignoriert)
        if record.levelno >= logging.WARNING:
            try:
                self._queue.put_nowait(record)
            except queue.Full:
                pass
            return
            
        if record.levelno < logging.INFO:
            return
            
        # Übergeordnete Lifecycle-Events senden
        if any(p.lower() in msg_lower for p in self.IMPORTANT_INFO_PATTERNS):
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


def send_relist_embed(
    webhook_url: str,
    total_count: int,
    grouped_players: List[Dict[str, Any]],
    next_run: Optional[datetime] = None
) -> bool:
    """
    Sendet das zentrale Re-List Zusammenfassungs-Embed an Discord.
    
    Args:
        webhook_url: Discord Webhook URL
        total_count: Gesamtzahl der neu eingestellten Spieler
        grouped_players: Aggregierte Spieler-Liste (Name, Rating, Position, Count)
        next_run: Optionaler Zeitpunkt des nächsten Durchlaufs
        
    Returns:
        True wenn erfolgreich gesendet
    """
    if not webhook_url or not webhook_url.startswith("http"):
        return False
        
    title = f"✅ Transferliste: {total_count} Spieler neu angeboten"
    
    # Baue Spieler-Übersicht (z. B. • 9x Tah (87, CB))
    lines = []
    for g in grouped_players:
        lines.append(f"• **{g['count']}x** {g['name']} ({g['rating']}, {g['position']})")
        
    desc = "**Übersicht der Spieler:**\n" + "\n".join(lines) if lines else "Alle abgelaufenen Spieler wurden erfolgreich neu angeboten."
    if len(desc) > 3500:
        desc = desc[:3450] + "\n... *(weitere Spieler abgeschnitten)*"
        
    fields = [
        {
            "name": "Menge",
            "value": f"{total_count} Spieler",
            "inline": True
        },
        {
            "name": "Verschiedene",
            "value": f"{len(grouped_players)} Spieler",
            "inline": True
        }
    ]
    
    if next_run:
        fields.append({
            "name": "Nächster Durchlauf",
            "value": f"Geplant um {next_run.strftime('%H:%M:%S')} Uhr",
            "inline": False
        })
        
    payload = {
        "username": "EA FC27 Bot",
        "embeds": [
            {
                "title": title,
                "description": desc,
                "color": 0x2ECC71,  # Grün
                "fields": fields,
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
    except Exception as e:
        return False


def send_no_items_embed(webhook_url: str, next_run: Optional[datetime] = None) -> bool:
    """
    Sendet ein kurzes Embed wenn keine abgelaufenen Spieler vorhanden sind.
    """
    if not webhook_url or not webhook_url.startswith("http"):
        return False
        
    fields = []
    if next_run:
        fields.append({
            "name": "Nächster Durchlauf",
            "value": f"Geplant um {next_run.strftime('%H:%M:%S')} Uhr",
            "inline": False
        })
        
    payload = {
        "username": "EA FC27 Bot",
        "embeds": [
            {
                "title": "ℹ️ Transferliste: Keine abgelaufenen Spieler",
                "description": "Aktuell müssen keine Spieler neu angeboten werden.",
                "color": 0x3498DB,  # Blau
                "fields": fields,
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


def send_device_conflict_embed(webhook_url: str, *args, **kwargs) -> bool:
    """
    Sendet eine Warnmeldung an Discord, wenn Ultimate Team bereits auf einem anderen Gerät aktiv ist.
    
    Args:
        webhook_url: Discord Webhook URL
        
    Returns:
        True wenn erfolgreich gesendet
    """
    if not webhook_url or not webhook_url.startswith("http"):
        return False
        
    payload = {
        "username": "EA FC27 Bot",
        "embeds": [
            {
                "title": "⚠️ WebApp pausiert: Auf anderem Gerät aktiv",
                "description": (
                    "Ultimate Team läuft aktuell auf einem anderen Gerät (Konsole/PC).\n"
                    "Der Bot pausiert und versucht es beim nächsten regulären Durchlauf erneut."
                ),
                "color": 0xF39C12,  # Orange
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "footer": {
                    "text": "EA FC27 Relist Bot • Geräte-Konflikt"
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
