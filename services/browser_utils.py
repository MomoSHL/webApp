"""
🌐 Browser Utilities
====================
Browser-Management, Tab-Handling, Cookie-Management.
"""

import sys
import os
from pathlib import Path
from typing import Union, Dict
from selenium.webdriver.remote.webdriver import WebDriver
import undetected_chromedriver as uc

# Parent directory zum Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import aus ea_fc27_bot für Re-Export
from ea_fc27_bot import (
    get_platform_user_agent,
    get_cookie_filepath,
    save_cookies,
    load_cookies,
    switch_to_idle_tab,
    switch_to_webapp_tab,
    check_already_logged_in_elsewhere
)


def init_browser(config: Union[Dict, 'BotConfig'], user_agent: str = None) -> WebDriver:
    """
    Initialisiert Browser mit undetected-chromedriver.
    
    NEU: Unterstützt chrome_binary aus Config für Linux ohne Root!
    
    Args:
        config: BotConfig oder Dict mit Konfiguration
        user_agent: Optional custom User-Agent
        
    Returns:
        WebDriver Instanz
    """
    from services.bot_logger import logger
    
    options = uc.ChromeOptions()
    
    # Headless Mode
    headless = config.get('headless', True) if isinstance(config, dict) else getattr(config, 'headless', True)
    if headless:
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
    
    # User-Agent (nur falls explizit gesetzt)
    if not user_agent:
        user_agent = get_platform_user_agent()
    if user_agent:
        options.add_argument(f'--user-agent={user_agent}')
    
    # Weitere Optionen
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-notifications')
    
    # NEU: Custom Chrome Binary (falls gesetzt)
    chrome_binary = None
    if isinstance(config, dict):
        chrome_binary = config.get('chrome_binary')
    else:
        chrome_binary = getattr(config, 'chrome_binary', None)
    
    if chrome_binary:
        # Expandiere ~ zu Home-Verzeichnis
        chrome_binary = os.path.expanduser(chrome_binary)
        
        if os.path.exists(chrome_binary):
            options.binary_location = chrome_binary
            logger.info(f"🔧 Using custom Chrome binary: {chrome_binary}")
        else:
            logger.error(f"❌ Chrome binary not found: {chrome_binary}")
            raise FileNotFoundError(f"Chrome binary not found: {chrome_binary}")
    
    # Browser initialisieren
    try:
        driver = uc.Chrome(options=options, version_main=None)
        logger.info("✅ Browser erfolgreich initialisiert")
        return driver
    except Exception as e:
        logger.error(f"❌ Browser-Initialisierung fehlgeschlagen: {e}")
        raise


# Re-Export für saubere API
__all__ = [
    'init_browser',
    'get_platform_user_agent',
    'get_cookie_filepath',
    'save_cookies',
    'load_cookies',
    'switch_to_idle_tab',
    'switch_to_webapp_tab',
    'check_already_logged_in_elsewhere'
]
