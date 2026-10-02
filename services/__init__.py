"""
Services Package
================
Bot Service-Module für EA FC27 WebApp Bot.
"""

from .bot_config import BotConfig, load_config
from .bot_session import BotSession, SessionState
from .bot_main import EAFC27Bot, EAFC26Bot, create_bot
from .bot_logger import get_logger, setup_bot_logging, setup_discord_logging, log_section, log_success, log_error, log_warning, log_info
from .bot_stats import BotStatistics
from .config_validator import validate_config, ConfigValidationError

def __getattr__(name):
    """Lazy load modules that depend on ea_fc27_bot to prevent circular imports."""
    if name in (
        'human_like_delay', 'is_night_time', 'calculate_sleep_until_morning',
        'random_mouse_movements', 'random_scroll_behavior', 'randomize_viewport',
        'simulate_tab_switch', 'human_type', 'human_click', 'dismiss_all_popups'
    ):
        from . import bot_helpers
        return getattr(bot_helpers, name)
    elif name in (
        'init_browser', 'get_platform_user_agent', 'apply_stealth_overrides', 'save_cookies', 'load_cookies',
        'switch_to_idle_tab', 'switch_to_webapp_tab', 'check_already_logged_in_elsewhere', 'is_logged_in_ui'
    ):
        from . import browser_utils
        return getattr(browser_utils, name)
    elif name in ('login_via_ui', 'handle_2fa', 'is_logged_in_ui'):
        from . import login_service
        return getattr(login_service, name)
    elif name in ('relist_all_transfer_items', 'navigate_to_transfer_list'):
        from . import relist_service
        return getattr(relist_service, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Core Services
    'BotConfig',
    'load_config',
    'BotSession',
    'SessionState',
    'EAFC27Bot',
    'EAFC26Bot',
    'create_bot',
    
    # Logger
    'get_logger',
    'setup_bot_logging',
    'log_section',
    'log_success',
    'log_error',
    'log_warning',
    'log_info',
    
    # Stats & Validation
    'BotStatistics',
    'validate_config',
    'ConfigValidationError',
    
    # Helper Functions
    'human_like_delay',
    'is_night_time',
    'calculate_sleep_until_morning',
    'random_mouse_movements',
    'random_scroll_behavior',
    'randomize_viewport',
    'simulate_tab_switch',
    'human_type',
    'human_click',
    'dismiss_all_popups',
    
    # Browser Utils
    'init_browser',
    'get_platform_user_agent',
    'apply_stealth_overrides',
    'save_cookies',
    'load_cookies',
    'switch_to_idle_tab',
    'switch_to_webapp_tab',
    'check_already_logged_in_elsewhere',
    
    # Login Service
    'login_via_ui',
    'handle_2fa',
    'is_logged_in_ui',
    
    # Relist Service
    'relist_all_transfer_items',
    'navigate_to_transfer_list'
]
