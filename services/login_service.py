"""
🔐 Login Service
================
Login-Logik, 2FA-Handling.

Wraps Login-Funktionen aus ea_fc27_bot.py.
"""

import sys
from pathlib import Path

# Parent directory zum Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

from ea_fc27_bot import (
    login_via_ui,
    handle_2fa,
    is_logged_in_ui
)

# Re-Export
__all__ = [
    'login_via_ui',
    'handle_2fa',
    'is_logged_in_ui'
]
