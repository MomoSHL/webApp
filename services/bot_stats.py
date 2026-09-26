"""
📊 Bot-Statistiken für EA FC27 WebApp Bot
==========================================
Sammelt und speichert Bot-Statistiken für Monitoring und Analyse.

Features:
- Session-Tracking
- Erfolgs-/Fehlerquoten
- Performance-Metriken
- JSON-Export

Usage:
    from bot_stats import BotStatistics
    
    stats = BotStatistics()
    stats.record_login(success=True, duration=5.2)
    stats.record_relist(players=12, duration=8.5)
    stats.save()
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field


STATS_FILE = Path(__file__).parent / "bot_stats.json"


@dataclass
class SessionStats:
    """Statistiken für eine einzelne Bot-Session."""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    
    # Login
    login_attempts: int = 0
    login_successes: int = 0
    login_failures: int = 0
    login_avg_duration: float = 0.0
    
    # Re-List
    relist_attempts: int = 0
    relist_successes: int = 0
    relist_failures: int = 0
    total_players_relisted: int = 0
    relist_avg_duration: float = 0.0
    
    # Errors
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Browser
    browser_crashes: int = 0
    browser_restarts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary."""
        return asdict(self)


@dataclass
class OverallStats:
    """Gesamt-Statistiken über alle Sessions."""
    first_run: str
    last_run: str
    total_sessions: int = 0
    total_runtime_hours: float = 0.0
    
    # Login Gesamt
    total_login_attempts: int = 0
    total_login_successes: int = 0
    total_login_failures: int = 0
    login_success_rate: float = 0.0
    
    # Re-List Gesamt
    total_relist_attempts: int = 0
    total_relist_successes: int = 0
    total_relist_failures: int = 0
    total_players_relisted: int = 0
    relist_success_rate: float = 0.0
    avg_players_per_relist: float = 0.0
    
    # Performance
    total_errors: int = 0
    total_warnings: int = 0
    total_browser_crashes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary."""
        return asdict(self)


class BotStatistics:
    """
    Verwaltet Bot-Statistiken.
    
    Tracked:
    - Login-Erfolge/-Fehler
    - Re-List-Operationen
    - Performance-Metriken
    - Fehler und Warnungen
    """
    
    def __init__(self, auto_save: bool = True):
        """
        Initialisiert Statistik-System.
        
        Args:
            auto_save: Automatisch speichern nach jeder Operation
        """
        self.auto_save = auto_save
        self.stats_file = STATS_FILE
        
        # Lade existierende Stats oder erstelle neue
        self._load_or_create()
        
        # Aktuelle Session
        self.current_session = SessionStats(
            session_id=datetime.now().strftime('%Y%m%d_%H%M%S'),
            start_time=datetime.now().isoformat()
        )
        self.session_start = datetime.now()
    
    def _load_or_create(self):
        """Lädt Stats aus Datei oder erstellt neue."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                self.overall = OverallStats(**data.get('overall', {}))
                self.sessions = [
                    SessionStats(**s) for s in data.get('sessions', [])
                ]
            except Exception:
                self._create_new()
        else:
            self._create_new()
    
    def _create_new(self):
        """Erstellt neue Stats."""
        now = datetime.now().isoformat()
        self.overall = OverallStats(
            first_run=now,
            last_run=now
        )
        self.sessions: List[SessionStats] = []
    
    def record_login(self, success: bool, duration: float = 0.0, error: Optional[str] = None):
        """
        Zeichnet Login-Versuch auf.
        
        Args:
            success: True wenn erfolgreich
            duration: Dauer in Sekunden
            error: Fehlermeldung (optional)
        """
        self.current_session.login_attempts += 1
        
        if success:
            self.current_session.login_successes += 1
        else:
            self.current_session.login_failures += 1
            if error:
                self.current_session.errors.append(f"Login: {error}")
        
        # Update Average
        if duration > 0:
            total_duration = (
                self.current_session.login_avg_duration * 
                (self.current_session.login_attempts - 1) + 
                duration
            )
            self.current_session.login_avg_duration = (
                total_duration / self.current_session.login_attempts
            )
        
        if self.auto_save:
            self.save()
    
    def record_relist(
        self, 
        success: bool, 
        players: int = 0, 
        duration: float = 0.0, 
        error: Optional[str] = None
    ):
        """
        Zeichnet Re-List-Operation auf.
        
        Args:
            success: True wenn erfolgreich
            players: Anzahl neu gelisteter Spieler
            duration: Dauer in Sekunden
            error: Fehlermeldung (optional)
        """
        self.current_session.relist_attempts += 1
        
        if success:
            self.current_session.relist_successes += 1
            self.current_session.total_players_relisted += players
        else:
            self.current_session.relist_failures += 1
            if error:
                self.current_session.errors.append(f"Re-List: {error}")
        
        # Update Average
        if duration > 0:
            total_duration = (
                self.current_session.relist_avg_duration * 
                (self.current_session.relist_attempts - 1) + 
                duration
            )
            self.current_session.relist_avg_duration = (
                total_duration / self.current_session.relist_attempts
            )
        
        if self.auto_save:
            self.save()
    
    def record_error(self, error_msg: str):
        """Zeichnet Fehler auf."""
        self.current_session.errors.append(error_msg)
        if self.auto_save:
            self.save()
    
    def record_warning(self, warning_msg: str):
        """Zeichnet Warnung auf."""
        self.current_session.warnings.append(warning_msg)
        if self.auto_save:
            self.save()
    
    def record_browser_crash(self):
        """Zeichnet Browser-Crash auf."""
        self.current_session.browser_crashes += 1
        if self.auto_save:
            self.save()
    
    def record_browser_restart(self):
        """Zeichnet Browser-Neustart auf."""
        self.current_session.browser_restarts += 1
        if self.auto_save:
            self.save()
    
    def end_session(self):
        """Beendet aktuelle Session und aktualisiert Gesamt-Stats."""
        # Session beenden
        self.current_session.end_time = datetime.now().isoformat()
        duration = (datetime.now() - self.session_start).total_seconds()
        self.current_session.duration_seconds = duration
        
        # Füge Session zu History hinzu
        self.sessions.append(self.current_session)
        
        # Update Overall Stats
        self._update_overall_stats()
        
        # Speichern
        self.save()
    
    def _update_overall_stats(self):
        """Aktualisiert Gesamt-Statistiken."""
        self.overall.last_run = datetime.now().isoformat()
        self.overall.total_sessions += 1
        
        # Summiere alle Sessions
        self.overall.total_runtime_hours = sum(
            s.duration_seconds for s in self.sessions
        ) / 3600
        
        self.overall.total_login_attempts = sum(
            s.login_attempts for s in self.sessions
        )
        self.overall.total_login_successes = sum(
            s.login_successes for s in self.sessions
        )
        self.overall.total_login_failures = sum(
            s.login_failures for s in self.sessions
        )
        
        if self.overall.total_login_attempts > 0:
            self.overall.login_success_rate = (
                self.overall.total_login_successes / 
                self.overall.total_login_attempts * 100
            )
        
        self.overall.total_relist_attempts = sum(
            s.relist_attempts for s in self.sessions
        )
        self.overall.total_relist_successes = sum(
            s.relist_successes for s in self.sessions
        )
        self.overall.total_relist_failures = sum(
            s.relist_failures for s in self.sessions
        )
        self.overall.total_players_relisted = sum(
            s.total_players_relisted for s in self.sessions
        )
        
        if self.overall.total_relist_attempts > 0:
            self.overall.relist_success_rate = (
                self.overall.total_relist_successes / 
                self.overall.total_relist_attempts * 100
            )
        
        if self.overall.total_relist_successes > 0:
            self.overall.avg_players_per_relist = (
                self.overall.total_players_relisted / 
                self.overall.total_relist_successes
            )
        
        self.overall.total_errors = sum(
            len(s.errors) for s in self.sessions
        )
        self.overall.total_warnings = sum(
            len(s.warnings) for s in self.sessions
        )
        self.overall.total_browser_crashes = sum(
            s.browser_crashes for s in self.sessions
        )
    
    def save(self):
        """Speichert Statistiken in JSON-Datei."""
        # Update overall vor dem Speichern (ohne Session zu beenden)
        self._update_overall_stats()
        
        data = {
            'overall': self.overall.to_dict(),
            'sessions': [s.to_dict() for s in self.sessions],
            'current_session': self.current_session.to_dict()
        }
        
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Statistiken konnten nicht gespeichert werden: {e}")
    
    def get_summary(self) -> str:
        """
        Gibt formatierte Zusammenfassung zurück.
        
        Returns:
            Formatierter Stats-String
        """
        lines = [
            "\n" + "="*60,
            "📊 BOT-STATISTIKEN",
            "="*60,
            "",
            "📈 Gesamt (Alle Sessions):",
            f"  • Gesamtlaufzeit: {self.overall.total_runtime_hours:.1f} Stunden",
            f"  • Sessions: {self.overall.total_sessions}",
            f"  • Login-Erfolgsrate: {self.overall.login_success_rate:.1f}%",
            f"  • Re-List-Erfolgsrate: {self.overall.relist_success_rate:.1f}%",
            f"  • Spieler neu gelistet: {self.overall.total_players_relisted}",
            f"  • Ø Spieler pro Re-List: {self.overall.avg_players_per_relist:.1f}",
            "",
            "📊 Aktuelle Session:",
            f"  • Login-Versuche: {self.current_session.login_attempts} "
            f"(✓ {self.current_session.login_successes}, "
            f"✗ {self.current_session.login_failures})",
            f"  • Re-List-Operationen: {self.current_session.relist_attempts} "
            f"(✓ {self.current_session.relist_successes}, "
            f"✗ {self.current_session.relist_failures})",
            f"  • Spieler neu gelistet: {self.current_session.total_players_relisted}",
            f"  • Fehler: {len(self.current_session.errors)}",
            f"  • Warnungen: {len(self.current_session.warnings)}",
            "="*60,
            ""
        ]
        return "\n".join(lines)
    
    def print_summary(self):
        """Gibt formatierte Zusammenfassung auf Console aus."""
        print(self.get_summary())


# Beispiel-Usage
if __name__ == '__main__':
    print("🧪 Bot-Statistics Test\n")
    
    # Erstelle Stats-Objekt
    stats = BotStatistics(auto_save=False)
    
    # Simuliere Session
    import time
    
    # Login
    print("Simuliere Login...")
    stats.record_login(success=True, duration=5.2)
    time.sleep(0.1)
    
    # Re-List
    print("Simuliere Re-List...")
    stats.record_relist(success=True, players=12, duration=8.5)
    time.sleep(0.1)
    
    # Zweites Re-List
    stats.record_relist(success=True, players=8, duration=7.2)
    
    # Fehler
    stats.record_error("Test-Fehler")
    stats.record_warning("Test-Warnung")
    
    # Session beenden
    stats.end_session()
    
    # Zusammenfassung
    stats.print_summary()
    
    print(f"✓ Stats gespeichert in: {STATS_FILE}")
