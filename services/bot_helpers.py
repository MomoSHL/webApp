"""
🛠️ Bot Helper Functions
=======================
Allgemeine Helper-Funktionen für den Bot.

Kombiniert eigene Hilfsfunktionen mit Importen aus ea_fc27_bot.py.
"""

import time
import random
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Tuple

from selenium.webdriver.common.action_chains import ActionChains

from .bot_logger import get_logger

logger = get_logger(__name__)

# Parent directory zum Pfad hinzufügen für ea_fc27_bot Import
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Helper-Funktionen aus ea_fc27_bot
from ea_fc27_bot import (
    human_like_delay,
    is_night_time,
    calculate_sleep_until_morning,
    random_mouse_movements,
    random_scroll_behavior,
    randomize_viewport,
    simulate_tab_switch,
    human_type,
    human_click
)

# Re-Export
__all__ = [
    'human_like_delay',
    'is_night_time',
    'calculate_sleep_until_morning',
    'random_mouse_movements',
    'random_scroll_behavior',
    'randomize_viewport',
    'simulate_tab_switch',
    'human_type',
    'human_click'
]
