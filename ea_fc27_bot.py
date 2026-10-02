#!/usr/bin/env python3
"""
EA FC27 WebApp Bot - Enterprise Edition
========================================
Automatischer Bot für EA FC27 WebApp mit:
- Re-List Funktion (alle Transfer-Spieler neu anbieten)
- Structured Logging (File + Console mit Rotation)
- Config-Validierung
- Statistics/Metrics
- Error-Recovery
- Anti-Detection Features

Author: Momo
Version: 2.1.0 (EA FC27)
"""

import time
import random
import pickle
import os
import platform
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple
import re

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException
)

import yaml
from apscheduler.schedulers.blocking import BlockingScheduler

# Service-Module importieren
from services.bot_logger import get_logger, log_section, log_success, log_error, log_warning, log_info
from services.config_validator import validate_config, ConfigValidationError
from services.bot_stats import BotStatistics
from services.player_parser import parse_transfer_list_html
from services.discord_service import send_relist_embed, send_device_conflict_embed, send_no_items_embed

# Logger initialisieren
logger = get_logger(__name__)

# Version
__version__ = "2.0.0"


# Verzeichnisse
COOKIES_DIR = Path(__file__).parent / "cookies"
COOKIES_DIR.mkdir(exist_ok=True)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def human_like_delay(min_sec: float = 0.3, max_sec: float = 1.5):
    """Simuliert menschliche Verzögerung zwischen Aktionen."""
    time.sleep(random.uniform(min_sec, max_sec))


def is_night_time(start_hour: int = 1, end_hour: int = 6):
    """
    Prüft ob aktuell Nachtpause ist (Standard: 1:00 - 6:00 Uhr).
    
    Args:
        start_hour: Beginn der Nachtpause (Standard: 1 Uhr)
        end_hour: Ende der Nachtpause (Standard: 6 Uhr)
    
    Returns:
        True wenn zwischen start_hour und end_hour
    """
    current_hour = datetime.now().hour
    return start_hour <= current_hour < end_hour


def calculate_sleep_until_morning(wake_hour: int = 6):
    """
    Berechnet Sekunden bis zur angegebenen Uhrzeit.
    
    Args:
        wake_hour: Uhrzeit zum Aufwachen (Standard: 6 Uhr)
    
    Returns:
        Sekunden bis wake_hour erreicht ist
    """
    now = datetime.now()
    wake_time = now.replace(hour=wake_hour, minute=0, second=0, microsecond=0)
    
    # Wenn wake_hour bereits vorbei ist, nimm morgen
    if now >= wake_time:
        wake_time += timedelta(days=1)
    
    sleep_seconds = (wake_time - now).total_seconds()
    return sleep_seconds, wake_time


def random_mouse_movements(driver, num_movements=None):
    """
    Führt zufällige Mausbewegungen aus (wie echter User der sich umsieht).
    
    Args:
        driver: WebDriver Instanz
        num_movements: Anzahl Bewegungen (None = zufällig 2-4)
    """
    if num_movements is None:
        num_movements = random.randint(2, 4)
    
    try:
        actions = ActionChains(driver)
        
        for _ in range(num_movements):
            # Zufällige kleine Bewegungen
            x_offset = random.randint(-150, 150)
            y_offset = random.randint(-100, 100)
            
            actions.move_by_offset(x_offset, y_offset)
            actions.pause(random.uniform(0.3, 0.8))
        
        actions.perform()
        
        # Reset mouse position
        actions = ActionChains(driver)
        actions.move_by_offset(0, 0)
        actions.perform()
        
    except Exception as e:
        # Ignoriere Fehler bei Mouse-Movements (nicht kritisch)
        pass


def random_scroll_behavior(driver):
    """
    Simuliert natürliches Scroll-Verhalten (wichtig für Detection!).
    Echte User scrollen oft, auch wenn nicht nötig.
    """
    if random.random() < 0.3:  # 30% Chance zu scrollen
        scroll_types = ["smooth", "fast", "hesitant"]
        scroll_type = random.choice(scroll_types)
        
        try:
            if scroll_type == "smooth":
                # Smooth continuous scroll
                for _ in range(random.randint(2, 4)):
                    scroll_amount = random.randint(100, 300)
                    driver.execute_script(f"window.scrollBy({{top: {scroll_amount}, behavior: 'smooth'}});")
                    time.sleep(random.uniform(0.2, 0.5))
            
            elif scroll_type == "fast":
                # Schneller Scroll zu Position
                scroll_amount = random.randint(300, 800)
                driver.execute_script(f"window.scrollBy({{top: {scroll_amount}, behavior: 'auto'}});")
            
            else:  # hesitant
                # Scroll mit Zurück-Bewegungen (User sucht was)
                for _ in range(random.randint(2, 5)):
                    scroll_amount = random.randint(50, 200) * random.choice([1, -1])
                    driver.execute_script(f"window.scrollBy({{top: {scroll_amount}, behavior: 'smooth'}});")
                    time.sleep(random.uniform(0.3, 0.8))
            
            # Scroll zurück nach oben (manchmal)
            if random.random() < 0.4:
                time.sleep(random.uniform(0.5, 1.5))
                driver.execute_script("window.scrollTo({top: 0, behavior: 'smooth'});")
                
        except Exception as e:
            pass  # Ignoriere Scroll-Fehler


def randomize_viewport(driver):
    """
    Setzt zufällige, realistische Viewport-Größe.
    Immer gleiche Größe ist Bot-Indikator!
    """
    # Gängige Desktop-Auflösungen
    resolutions = [
        (1920, 1080), (1366, 768), (1536, 864),
        (1440, 900), (1680, 1050), (2560, 1440),
        (1600, 900), (1280, 720)
    ]
    
    width, height = random.choice(resolutions)
    
    # Kleine zufällige Variation (User hat nicht immer Fullscreen)
    width += random.randint(-100, 50)
    height += random.randint(-80, 30)
    
    try:
        driver.set_window_size(width, height)
        logger.info(f"   🖥️  Viewport: {width}x{height}")
    except:
        pass  # Fallback zu maximize_window


def switch_to_idle_tab(driver):
    """
    Wechselt zu einem neutralen Tab (z.B. Google) während Bot wartet.
    Öffnet neuen Tab falls noch keiner existiert.
    """
    try:
        # Prüfe ob Driver noch aktiv ist
        if not driver or not driver.window_handles:
            logger.debug("   ⚠ Keine aktiven Browser-Windows")
            return False
        
        # Prüfe ob bereits ein Google-Tab existiert
        google_tab = None
        for handle in driver.window_handles:
            try:
                driver.switch_to.window(handle)
                if "google.com" in driver.current_url:
                    google_tab = handle
                    logger.debug("   📑 Gewechselt zu existierendem Idle-Tab (Google)")
                    return True
            except:
                continue
        
        # Öffne neuen Tab mit neutraler Seite
        driver.execute_script("window.open('https://www.google.com', '_blank');")
        time.sleep(random.uniform(0.5, 1.0))
        
        # Wechsle zum neuen Tab
        if driver.window_handles:
            driver.switch_to.window(driver.window_handles[-1])
            logger.debug("   📑 Gewechselt zu Idle-Tab (Google)")
            return True
        
        return False
        
    except Exception as e:
        logger.debug(f"   ⚠ Tab-Wechsel fehlgeschlagen: {e}")
        return False


def switch_to_webapp_tab(driver, webapp_url):
    """
    Wechselt zurück zum WebApp-Tab (oder öffnet ihn neu falls geschlossen).
    
    Returns:
        bool: True wenn erfolgreich
    """
    try:
        # Prüfe ob Driver noch aktiv ist
        if not driver:
            logger.debug("   ✗ Driver nicht verfügbar")
            return False
        
        # Prüfe ob überhaupt Windows offen sind
        try:
            handles = driver.window_handles
            if not handles:
                logger.debug("   ✗ Keine Browser-Windows offen")
                return False
        except Exception as e:
            logger.debug(f"   ✗ Kann Window-Handles nicht abrufen: {e}")
            return False
        
        # Finde WebApp-Tab
        webapp_handle = None
        for handle in handles:
            try:
                driver.switch_to.window(handle)
                current_url = driver.current_url
                if "ea.com" in current_url or "fut" in current_url.lower():
                    webapp_handle = handle
                    logger.debug("   📱 Zurück zum WebApp-Tab")
                    try:
                        driver.execute_script("""
                            window.focus();
                            document.dispatchEvent(new Event('focus'));
                            document.dispatchEvent(new Event('visibilitychange'));
                        """)
                    except Exception:
                        pass
                    time.sleep(random.uniform(1.0, 1.8))
                    return True
            except Exception as e:
                # Handle könnte geschlossen worden sein
                continue
        
        # WebApp-Tab nicht gefunden, öffne in aktuellem/neuem Tab
        logger.debug("   ⚠ WebApp-Tab nicht gefunden, lade WebApp...")
        try:
            # Versuche aktuellen Tab zu nutzen
            driver.get(webapp_url)
            time.sleep(random.uniform(2, 3))
            return True
        except:
            # Falls das fehlschlägt, öffne neuen Tab
            driver.execute_script(f"window.open('{webapp_url}', '_blank');")
            time.sleep(random.uniform(1, 2))
            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(random.uniform(2, 3))
            return True
            
    except Exception as e:
        logger.debug(f"   ✗ Fehler beim WebApp-Tab Wechsel: {e}")
        return False


def simulate_tab_switch(driver):
    """
    Simuliert kurzes Tab-Wechseln (User checkt kurz was anderes).
    10% Chance - sehr realistisch!
    """
    if random.random() < 0.10:  # 10% Chance
        logger.debug("   🔄 Simuliere kurzen Tab-Wechsel...")
        try:
            driver.execute_script("window.blur();")
            time.sleep(random.uniform(1, 3))  # Nur 1-3 Sekunden
            driver.execute_script("window.focus();")
            time.sleep(random.uniform(0.3, 0.7))
        except:
            pass


def human_type(element, text: str, min_delay: float = 0.05, max_delay: float = 0.15):
    """Tippt Text mit zufälligen Verzögerungen wie ein Mensch."""
    # Manchmal schneller, manchmal langsamer
    if random.random() < 0.3:
        min_delay *= 0.5
        max_delay *= 0.5
    elif random.random() < 0.1:
        min_delay *= 2
        max_delay *= 2
    
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))


def human_click(driver, element, method="move"):
    """
    Führt einen menschenähnlichen Klick aus.
    
    Args:
        driver: WebDriver Instanz
        element: Element zum Klicken
        method: "move" (ActionChains mit Mouse-Move), "direct" (normaler Klick), "js" (JavaScript)
    
    Returns:
        bool: True wenn erfolgreich
    """
    try:
        # Scroll zum Element mit smooth behavior
        driver.execute_script("""
            arguments[0].scrollIntoView({
                block: 'center',
                inline: 'center',
                behavior: 'smooth'
            });
        """, element)
        human_like_delay(0.5, 1.0)  # Warte nach Scroll
        
        # Prüfe ob Element wirklich sichtbar ist
        if not element.is_displayed():
            logger.debug(f"      ⚠ Element nicht sichtbar")
            return False
        
        # Prüfe ob Element enabled ist
        if not element.is_enabled():
            logger.debug(f"      ⚠ Element nicht enabled")
            return False
        
        if method == "move":
            # Methode 1: ActionChains mit echter Mouse-Bewegung (am menschlichsten)
            try:
                # Warte kurz damit Scroll fertig ist
                human_like_delay(0.2, 0.4)
                
                actions = ActionChains(driver)
                
                # Bewege Maus zum Element
                actions.move_to_element(element)
                human_like_delay(0.15, 0.35)  # Kurze Pause nach Mouse-Move
                
                # Führe Klick aus
                actions.click()
                actions.perform()
                
                human_like_delay(0.2, 0.4)  # Pause nach Klick
                return True
                
            except Exception as e:
                logger.debug(f"      ⚠ ActionChains fehlgeschlagen: {str(e)[:100]}")
                method = "direct"  # Fallback
        
        if method == "direct":
            # Methode 2: Normaler Selenium-Klick
            try:
                human_like_delay(0.2, 0.4)
                element.click()
                human_like_delay(0.2, 0.4)
                return True
            except Exception as e:
                logger.debug(f"      ⚠ Direkter Klick fehlgeschlagen: {str(e)[:100]}")
                method = "js"  # Fallback
        
        if method == "js":
            # Methode 3: JavaScript-Klick (letzter Ausweg)
            try:
                human_like_delay(0.2, 0.4)
                driver.execute_script("arguments[0].click();", element)
                human_like_delay(0.2, 0.4)
                return True
            except Exception as e:
                logger.debug(f"      ⚠ JavaScript-Klick fehlgeschlagen: {str(e)[:100]}")
                return False
            
    except Exception as e:
        logger.debug(f"      ✗ Alle Klick-Methoden fehlgeschlagen: {str(e)[:100]}")
        return False
    
    return False


def get_cookie_filepath(username: str) -> Path:
    """Generiert Cookie-Dateipfad für Account (Multi-Account-Support)."""
    safe_username = "".join(c for c in username if c.isalnum() or c in "._-@")
    return COOKIES_DIR / f"{safe_username}.pkl"


def save_cookies(driver, username: str):
    """Speichert Browser-Cookies für Account."""
    filepath = get_cookie_filepath(username)
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump(driver.get_cookies(), f)
        logger.info(f"✅ Cookies gespeichert: {filepath.name}")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Cookie-Speicherung fehlgeschlagen: {e}")
        return False


def load_cookies(driver, username: str):
    """Lädt gespeicherte Cookies für Account."""
    filepath = get_cookie_filepath(username)
    
    if not filepath.exists():
        # Fallback 1: cookies_xxx.pkl Format
        safe_name = username.replace('@', '_at_').replace('.', '_')
        alt_path = COOKIES_DIR / f"cookies_{safe_name}.pkl"
        if alt_path.exists():
            filepath = alt_path
        else:
            # Fallback 2: Jede vorhandene .pkl Datei im cookies/ Ordner
            pkl_files = list(COOKIES_DIR.glob("*.pkl"))
            if pkl_files:
                filepath = pkl_files[0]
            else:
                logger.warning(f"⚠️ Keine Cookie-Datei für '{username}' in {COOKIES_DIR} gefunden.")
                return False
    
    try:
        with open(filepath, "rb") as f:
            cookies = pickle.load(f)
        
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass
        
        logger.info(f"✅ Cookies geladen aus '{filepath.name}': {len(cookies)} Einträge")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Cookie-Laden fehlgeschlagen: {e}")
        return False


# ============================================================================
# BROWSER INITIALIZATION & ANTI-DETECTION
# ============================================================================

WINDOWS_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def get_platform_user_agent() -> str:
    """
    Gibt immer einen Windows Desktop User-Agent zurück.
    Verhindert die EA-Sperre ('Unsupported Browser / Browser not supported') unter Linux.
    """
    return WINDOWS_USER_AGENT


def apply_stealth_overrides(driver, user_agent: Optional[str] = None) -> None:
    """
    Wendet umfassende Anti-Detection & Windows-Spoofing CDP Overrides an.
    Bypasst die 'Browser not supported' Sperre von EA auf Linux/Headless-Servern.
    """
    if not user_agent:
        user_agent = get_platform_user_agent()

    # CDP Domains aktivieren
    try:
        driver.execute_cdp_cmd("Page.enable", {})
    except Exception:
        pass
    try:
        driver.execute_cdp_cmd("Network.enable", {})
    except Exception:
        pass

    # 1. Timezone & Locale via CDP
    try:
        driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": "Europe/Berlin"})
        driver.execute_cdp_cmd("Emulation.setLocaleOverride", {"locale": "de-DE"})
    except Exception as e:
        logger.debug(f"   ℹ️  CDP Emulation Override: {e}")

    # 2. Network User Agent & Client Hints Override (CDP)
    try:
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": user_agent,
            "acceptLanguage": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "platform": "Win32",
            "userAgentMetadata": {
                "brands": [
                    {"brand": "Google Chrome", "version": "131"},
                    {"brand": "Chromium", "version": "131"},
                    {"brand": "Not_A Brand", "version": "24"}
                ],
                "fullVersionList": [
                    {"brand": "Google Chrome", "version": "131.0.6778.86"},
                    {"brand": "Chromium", "version": "131.0.6778.86"},
                    {"brand": "Not_A Brand", "version": "24.0.0.0"}
                ],
                "platform": "Windows",
                "platformVersion": "10.0.0",
                "architecture": "x86",
                "model": "",
                "mobile": False,
                "bitness": "64"
            }
        })
    except Exception as e:
        logger.debug(f"   ℹ️  CDP Network.setUserAgentOverride: {e}")

    # 3. JavaScript Injektion vor jedem Laden (navigator.platform, userAgentData, WebGL)
    app_ver = user_agent.replace("Mozilla/", "")
    stealth_js = f"""
    // Spoof navigator.platform (kritisch für EA WebApp auf Linux)
    Object.defineProperty(navigator, 'platform', {{
        get: () => 'Win32'
    }});

    // Spoof navigator.userAgent & appVersion
    Object.defineProperty(navigator, 'userAgent', {{
        get: () => '{user_agent}'
    }});
    Object.defineProperty(navigator, 'appVersion', {{
        get: () => '{app_ver}'
    }});

    // Spoof navigator.vendor
    Object.defineProperty(navigator, 'vendor', {{
        get: () => 'Google Inc.'
    }});

    // Spoof navigator.maxTouchPoints
    Object.defineProperty(navigator, 'maxTouchPoints', {{
        get: () => 0
    }});

    // Spoof navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {{
        get: () => undefined
    }});

    // Chrome object mock
    if (!window.chrome) {{
        window.chrome = {{}};
    }}
    if (!window.chrome.runtime) {{
        window.chrome.runtime = {{}};
    }}

    // Spoof navigator.userAgentData (Client Hints)
    if (navigator.userAgentData) {{
        const brands = [
            {{brand: 'Google Chrome', version: '131'}},
            {{brand: 'Chromium', version: '131'}},
            {{brand: 'Not_A Brand', version: '24'}}
        ];
        const fullVersionList = [
            {{brand: 'Google Chrome', version: '131.0.6778.86'}},
            {{brand: 'Chromium', version: '131.0.6778.86'}},
            {{brand: 'Not_A Brand', version: '24.0.0.0'}}
        ];

        Object.defineProperty(navigator, 'userAgentData', {{
            get: () => ({{
                brands: brands,
                mobile: false,
                platform: 'Windows',
                getHighEntropyValues: async (hints) => ({{
                    architecture: 'x86',
                    bitness: '64',
                    brands: brands,
                    fullVersionList: fullVersionList,
                    mobile: false,
                    model: '',
                    platform: 'Windows',
                    platformVersion: '10.0.0',
                    uaFullVersion: '131.0.6778.86'
                }}),
                toJSON: () => ({{
                    brands: brands,
                    mobile: false,
                    platform: 'Windows'
                }})
            }})
        }});
    }}

    // WebGL Vendor & Renderer spoofing for headless/Xvfb (verhindert Mesa/Gallium/llvmpipe Leak)
    const getParameterProxy = function(target, thisArg, args) {{
        const param = args[0];
        if (param === 37445) {{
            return 'Google Inc. (NVIDIA)';
        }}
        if (param === 37446) {{
            return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)';
        }}
        return Reflect.apply(target, thisArg, args);
    }};

    if (typeof WebGLRenderingContext !== 'undefined') {{
        WebGLRenderingContext.prototype.getParameter = new Proxy(
            WebGLRenderingContext.prototype.getParameter,
            {{ apply: getParameterProxy }}
        );
    }}
    if (typeof WebGL2RenderingContext !== 'undefined') {{
        WebGL2RenderingContext.prototype.getParameter = new Proxy(
            WebGL2RenderingContext.prototype.getParameter,
            {{ apply: getParameterProxy }}
        );
    }}
    """
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": stealth_js})
    except Exception as e:
        logger.debug(f"   ℹ️  CDP Page.addScriptToEvaluateOnNewDocument: {e}")


def init_browser(headless: bool = True) -> uc.Chrome:
    """Initialisiert undetected-chromedriver mit erweiterten Anti-Detection Features."""
    options = uc.ChromeOptions()
    
    # Anti-Detection (Basis)
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    # WebRTC Leak Prevention (wichtig!)
    options.add_argument("--disable-webrtc")
    options.add_argument("--disable-webrtc-hw-encoding")
    
    # WebGL & GPU Enablement (für Linux/Xvfb ohne GPU-Block)
    options.add_argument("--ignore-gpu-blocklist")
    options.add_argument("--enable-webgl")
    options.add_argument("--enable-accelerated-2d-canvas")
    
    # Anti-Throttling (verhindert Einschlafen im Hintergrund/Xvfb)
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=CalculateNativeWinOcclusion")
    options.add_argument("--window-size=1920,1080")
    
    # Plattform-spezifischer User-Agent (immer Windows für EA Kompatibilität)
    user_agent = get_platform_user_agent()
    options.add_argument(f"--user-agent={user_agent}")
    logger.info(f"   🖥️  OS: {platform.system()} ({platform.release()}) [Spoofed: Windows 10/11]")
    
    # Language & Locale
    options.add_argument("--lang=de-DE")
    
    if headless:
        options.add_argument("--headless=new")
    
    driver = uc.Chrome(options=options, version_main=None)
    driver.set_page_load_timeout(60)
    
    # Zufällige Viewport-Größe (wichtig für Anti-Detection!)
    if not headless:
        randomize_viewport(driver)
    else:
        driver.maximize_window()
    
    # Anwenden der Stealth & Spoofing Overrides (CDP)
    apply_stealth_overrides(driver, user_agent)
    
    logger.info("✅ Browser initialisiert (Erweiterte Anti-Detection aktiv)")
    return driver


# ============================================================================
# LOGIN & 2FA
# ============================================================================

def handle_2fa(driver, wait):
    """
    Erkennt 2FA-Aufforderung und ermöglicht interaktive Code-Eingabe.
    Returns: True wenn erfolgreich
    """
    print("\n🔐 Prüfe auf 2FA...")
    time.sleep(2)
    
    # Suche 2FA-Indikatoren (URL, Titel oder Elemente)
    two_fa_detected = False
    try:
        current_url_lower = driver.current_url.lower()
        if "twofactor" in current_url_lower or "two-factor" in current_url_lower or "Two Factor" in driver.title:
            two_fa_detected = True
        elif driver.find_elements(By.CSS_SELECTOR, "label.origin-ux-radio-button-label, input#twoFactorCode, input[name='twoFactorCode']"):
            two_fa_detected = True
    except Exception:
        pass
    
    if not two_fa_detected:
        logger.info("✅ Keine 2FA erforderlich")
        return True
    
    print("\n" + "="*60)
    print("🔐 2FA-VERIFIZIERUNG ERFORDERLICH")
    print("="*60)
    
    # Finde verfügbare 2FA-Methoden
    labels = driver.find_elements(By.CSS_SELECTOR, "label.origin-ux-radio-button-label")
    available_methods = []
    method_elements = {}
    
    for label in labels:
        try:
            method_id = label.get_attribute("for")
            method_text = label.text.strip()
            
            if method_id and method_text:
                display_name = f"{method_id}: {method_text}"
                available_methods.append(display_name)
                method_elements[display_name] = (label, method_id)
        except Exception:
            continue
    
    # Zeige Methoden an
    if available_methods:
        print("\nVerfügbare Verifizierungsmethoden:")
        for idx, method in enumerate(available_methods, 1):
            print(f"  {idx}. {method}")
        
        # User-Auswahl
        while True:
            try:
                choice = int(input(f"\nWähle eine Methode (1-{len(available_methods)}): ").strip())
                if 1 <= choice <= len(available_methods):
                    selected_method = available_methods[choice - 1]
                    logger.info(f"✅ Ausgewählt: {selected_method}")
                    
                    # Klicke Label
                    elem, method_id = method_elements[selected_method]
                    elem.click()
                    time.sleep(1)
                    
                    # Klicke "Send Code"
                    try:
                        send_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#btnSendCode, button#btnSendCode, a#btnSendCode")))
                        send_btn.click()
                        logger.info("✅ 'Send Code' angeklickt")
                        time.sleep(2)
                    except Exception as e:
                        logger.warning(f"⚠️ 'Send Code' nicht gefunden: {e}")
                    
                    break
            except ValueError:
                print("Ungültige Eingabe! Bitte eine Zahl eingeben.")
            except KeyboardInterrupt:
                return False
    
    # Code-Eingabe
    code_input_selectors = [
        "input[name='twoFactorCode']",
        "input#twoFactorCode",
        "input[name='oneTimeCode']",
        "input[type='text'][placeholder*='code' i]",
        "input[type='tel'][placeholder*='code' i]",
    ]
    
    code_field = None
    for sel in code_input_selectors:
        try:
            code_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            break
        except Exception:
            continue
    
    if not code_field:
        logger.error("❌ Code-Eingabefeld nicht gefunden!")
        return False
    
    try:
        two_fa_code = input("\nGib den Verifizierungscode ein: ").strip()
        if not two_fa_code:
            return False
        
        # In das Code-Feld tippen
        code_field.click()
        time.sleep(0.2)
        code_field.clear()
        code_field.send_keys(two_fa_code)
        time.sleep(1)
        
        # Optional: "Trust this device" Checkbox aktivieren
        try:
            trust_checkbox = driver.find_element(By.CSS_SELECTOR, "label[for='trustThisDevice'], #trustThisDevice")
            if trust_checkbox and not driver.find_element(By.ID, "trustThisDevice").is_selected():
                trust_checkbox.click()
                time.sleep(0.3)
        except Exception:
            pass

        # Submit-Button ("NEXT" / a#btnSubmit) klicken
        submitted = False
        submit_selectors = [
            "a#btnSubmit",
            "#btnSubmit",
            "button#btnSubmit",
            "a#btnSendCode",
            "button#btnSendCode",
            "#btnSendCode",
            "#btnTwoFactorSubmit",
            "button[type='submit']",
            "a.otkbtn"
        ]
        for sub_sel in submit_selectors:
            try:
                candidate = driver.find_element(By.CSS_SELECTOR, sub_sel)
                if candidate.is_displayed():
                    human_like_delay(0.3, 0.6)
                    candidate.click()
                    submitted = True
                    logger.info(f"✅ 2FA-Bestätigungsbutton geklickt ('{candidate.text.strip()}')")
                    break
            except Exception:
                continue
                
        if not submitted:
            from selenium.webdriver.common.keys import Keys
            code_field.send_keys(Keys.RETURN)
        
        time.sleep(3)
        
        # Prüfe auf 2FA-Fehler
        for err in driver.find_elements(By.CSS_SELECTOR, ".origin-ux-element-error-message, .error, .banner-message, .otkform-error"):
            if err.is_displayed() and err.text.strip():
                logger.error(f"❌ 2FA-Fehler: {err.text.strip()}")
                return False
                
        logger.info("✅ 2FA-Code übermittelt")
        logger.info("="*60 + "\n")
        return True
        
    except KeyboardInterrupt:
        return False
    except Exception as e:
        logger.error(f"❌ 2FA-Fehler: {e}")
        return False



def save_page_diagnostics(driver, stage_name: str):
    """
    Speichert detaillierte Diagnose-Informationen (Screenshot, HTML-Dump, URL, Titel, DOM-Ausschnitt, Console-Logs).
    """
    try:
        diag_dir = Path("logs") / "diagnostics"
        diag_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{timestamp}_{stage_name}"
        
        # 1. Screenshot speichern
        screenshot_path = diag_dir / f"{prefix}.png"
        driver.save_screenshot(str(screenshot_path))
        
        # 2. HTML Quelle speichern
        html_path = diag_dir / f"{prefix}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
            
        # 3. Detaillierte Infos erfassen
        cur_url = driver.current_url
        cur_title = driver.title
        
        # Prüfe sichtbaren Text
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
            text_preview = " ".join(body_text.split()[:40])
        except Exception:
            text_preview = "N/A"
            
        # Prüfe gefundene Buttons
        btn_info = []
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            btn_info = [f"'{b.text.strip()}' ({b.get_attribute('class')})" for b in buttons if b.text.strip() or b.get_attribute('class')]
        except Exception:
            pass
            
        # Prüfe gefundene Inputs
        inp_info = []
        try:
            inputs = driver.find_elements(By.TAG_NAME, "input")
            inp_info = [f"name='{i.get_attribute('name')}' type='{i.get_attribute('type')}'" for i in inputs]
        except Exception:
            pass
            
        # Prüfe Browser Console Logs
        console_logs = []
        try:
            raw_logs = driver.get_log("browser")
            for entry in raw_logs:
                if entry.get("level") in ["SEVERE", "WARNING"]:
                    console_logs.append(f"[{entry.get('level')}] {entry.get('message')}")
        except Exception:
            pass
            
        logger.debug(f"🔍 [DIAGNOSE - {stage_name}]")
        logger.debug(f"   • URL: {cur_url}")
        logger.debug(f"   • Titel: '{cur_title}'")
        logger.debug(f"   • Text-Auszug: {text_preview[:120]}...")
        if btn_info:
            logger.debug(f"   • Buttons ({len(btn_info)}): {btn_info[:6]}")
        if inp_info:
            logger.debug(f"   • Inputs ({len(inp_info)}): {inp_info[:6]}")
        if console_logs:
            logger.debug(f"   • Browser-Fehler ({len(console_logs)}):")
            for cl in console_logs[:3]:
                logger.debug(f"     ⚠ {cl}")
        logger.debug(f"   • Screenshot: {screenshot_path}")
                
    except Exception as e:
        logger.debug(f"Diagnose-Erfassung fehlgeschlagen: {e}")


def _check_and_accept_cookie_banner(driver) -> bool:
    """Prüft und akzeptiert OneTrust / Cookie Consent Banner falls vorhanden."""
    try:
        cookie_selectors = [
            "#onetrust-accept-btn-handler",
            "button#onetrust-accept-btn-handler",
            "#onetrust-reject-all-handler",
            "button#onetrust-reject-all-handler",
            "#accept-recommended-btn-handler",
            "button#accept-recommended-btn-handler",
            "#btn-accept-all",
            "button.cookie-accept-all",
            "button.onetrust-close-btn-handler",
            "//button[contains(@id, 'onetrust-accept')]",
            "//button[contains(@id, 'onetrust') and (contains(., 'Accept') or contains(., 'Akzeptieren') or contains(., 'Alle') or contains(., 'Agree') or contains(., 'Zustimmen'))]",
            "//button[contains(., 'Accept All') or contains(., 'Alle akzeptieren') or contains(., 'Alle annehmen') or contains(., 'Zustimmen') or contains(., 'Akzeptieren')]",
        ]
        for sel in cookie_selectors:
            try:
                if sel.startswith("//"):
                    elems = driver.find_elements(By.XPATH, sel)
                else:
                    elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for cb in elems:
                    if cb.is_displayed() and cb.is_enabled():
                        try:
                            cb.click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", cb)
                        logger.info(f"✅ Cookie-Banner akzeptiert ('{cb.text.strip()}')")
                        human_like_delay(0.5, 1.0)
                        return True
            except Exception:
                continue
                
        # Entferne verbleibende OneTrust Overlays via JavaScript falls vorhanden
        try:
            driver.execute_script("""
                const ot = document.getElementById('onetrust-consent-sdk');
                if (ot) ot.style.display = 'none';
                const backdrop = document.querySelector('.onetrust-pc-dark-filter');
                if (backdrop) backdrop.style.display = 'none';
            """)
        except Exception:
            pass
    except Exception:
        pass
    return False


def dismiss_all_popups(driver, max_passes: int = 5) -> int:
    """
    Erkennt und schließt automatisch Popouts, Nachrichten-Dialoge, Willkommens-/Saison-Banner,
    Feature-Walkthroughs, News-Karten und Info-Overlays auf der Startseite/Hub der WebApp.
    
    Returns: Anzahl der geschlossenen Popups
    """
    total_dismissed = 0
    from selenium.webdriver.common.keys import Keys
    
    # 1. Cookie-Banner prüfen und akzeptieren
    _check_and_accept_cookie_banner(driver)
    
    for pass_num in range(max_passes):
        # Sicherheits-Check: Bei Gerätekonflikt ('Signed Into Another Device') nicht eingreifen!
        if check_already_logged_in_elsewhere(driver):
            break
            
        found_and_clicked = False
        
        # Selektoren für Popout-Schließen / Bestätigen
        popup_button_xpaths = [
            # 1. Spezifische Text-Buttons in Livemessages, Dialogen & Modal-Containern
            "//div[contains(@class, 'ut-livemessage') or contains(@class, 'ea-dialog-view') or contains(@class, 'view-modal') or contains(@class, 'ut-messages-view') or contains(@class, 'ut-popup-view') or contains(@class, 'ut-feature-walkthrough-view') or contains(@class, 'ut-notification-view') or contains(@class, 'dialog-body') or contains(@class, 'ut-livemessage-footer')]//button[contains(., 'Continue') or contains(., 'Weiter') or contains(., 'Fortfahren') or contains(., 'Next') or contains(., 'Vorwärts') or contains(., 'Got it') or contains(., 'Verstanden') or contains(., 'Claim Later') or contains(., 'Später anfordern') or contains(., 'Später') or contains(., 'Skip') or contains(., 'Überspringen') or contains(., 'I Agree') or contains(., 'Agree') or contains(., 'Accept') or contains(., 'Akzeptieren') or contains(., 'Done') or contains(., 'Fertig') or contains(., 'Close') or contains(., 'Schließen') or contains(., 'Reload') or contains(., 'Neu laden') or contains(., 'Refresh') or contains(., 'Erneut laden') or normalize-space(text())='OK' or normalize-space(text())='Ok']",
            
            # 2. Explizite Buttons in ut-livemessage-footer (z.B. Continue, Check it Out)
            "//div[contains(@class, 'ut-livemessage')]//button[contains(@class, 'btn-standard') and (contains(., 'Continue') or contains(., 'Weiter') or contains(., 'Fortfahren'))]",
            "div.ut-livemessage button.btn-standard.primary",
            "div.ut-livemessage-footer button.btn-standard.primary",
            "div.ut-livemessage-footer button",
            
            # 3. Explizite Schließen-Buttons in Dialogen
            "//div[contains(@class, 'ea-dialog-view') or contains(@class, 'view-modal') or contains(@class, 'ut-messages-view') or contains(@class, 'ut-popup-view')]//button[contains(@class, 'close-btn') or contains(@class, 'close') or contains(@class, 'dismiss') or contains(@class, 'icon-close')]",
            
            # 4. Standard 'Continue', 'Weiter', 'Next', 'Reload' Buttons in WebApp
            "//button[contains(@class, 'btn-standard') and (contains(., 'Continue') or contains(., 'Weiter') or contains(., 'Fortfahren') or contains(., 'Next') or contains(., 'Reload') or contains(., 'Neu laden') or normalize-space(text())='OK' or normalize-space(text())='Ok' or contains(., 'Got it') or contains(., 'Verstanden') or contains(., 'Claim Later') or contains(., 'Skip') or contains(., 'Überspringen'))]",
            
            # 5. Standard Dialog Close Buttons
            "button.flat.close-btn",
            "button.ut-dialog-close-btn",
            "button.dialog-close-btn",
            "button.icon-close",
            "button[aria-label='Close']",
            "button[aria-label='Schließen']",
            "button[aria-label='Dismiss']",
            "button[aria-label='dismiss']"
        ]
        
        for sel in popup_button_xpaths:
            try:
                if sel.startswith("//"):
                    buttons = driver.find_elements(By.XPATH, sel)
                else:
                    buttons = driver.find_elements(By.CSS_SELECTOR, sel)
                    
                for btn in buttons:
                    if not btn.is_displayed() or not btn.is_enabled():
                        continue
                        
                    btn_text = btn.text.strip()
                    btn_text_lower = btn_text.lower()
                    
                    # Schließe Re-List Confirmation Dialoge und Gerätekonflikt-Buttons aus!
                    if any(kw in btn_text_lower for kw in ['re-list', 'erneut anbieten', 'change', 'ändern', 'transfers', 'abbrechen']):
                        continue
                        
                    # Extrahiere optionalen Titel des Popouts
                    popup_title = ""
                    try:
                        title_elems = driver.find_elements(
                            By.XPATH, 
                            "//div[contains(@class, 'ut-livemessage') or contains(@class, 'ea-dialog-view') or contains(@class, 'view-modal') or contains(@class, 'ut-messages-view')]//h1 | //div[contains(@class, 'ut-livemessage') or contains(@class, 'ea-dialog-view') or contains(@class, 'view-modal') or contains(@class, 'ut-messages-view')]//h2 | //div[contains(@class, 'ea-dialog-view') or contains(@class, 'view-modal') or contains(@class, 'ut-messages-view')]//div[contains(@class, 'title')]"
                        )
                        for te in title_elems:
                            if te.is_displayed() and te.text.strip():
                                popup_title = te.text.strip()
                                break
                    except Exception:
                        pass
                        
                    # Klicke Button
                    clicked = False
                    try:
                        btn.click()
                        clicked = True
                    except Exception:
                        try:
                            driver.execute_script("arguments[0].click();", btn)
                            clicked = True
                        except Exception:
                            pass
                            
                    if clicked:
                        title_info = f" ('{popup_title}')" if popup_title else ""
                        btn_info = f"'{btn_text}'" if btn_text else "Close-Button"
                        logger.info(f"ℹ️ Popout/Info-Dialog geschlossen via {btn_info}{title_info}")
                        total_dismissed += 1
                        found_and_clicked = True
                        human_like_delay(0.8, 1.5)
                        break
                        
                if found_and_clicked:
                    break
            except Exception:
                continue
                
        # Wenn kein Button geklickt wurde, prüfe ob ein verbleibender Click-Shield existiert
        if not found_and_clicked:
            try:
                shields = driver.find_elements(By.CSS_SELECTOR, ".ut-click-shield")
                if shields and any(s.is_displayed() for s in shields):
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(0.5)
            except Exception:
                pass
            break
            
    return total_dismissed


def find_element_with_fallbacks(driver, selector_list, timeout=15, condition="clickable"):
    """
    Findet das erste passende Element aus einer Liste von Selektoren (CSS oder XPath),
    ohne für jeden Selektor die volle Timeout-Dauer sequentiell zu blockieren.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        for sel in selector_list:
            if not sel:
                continue
            try:
                if sel.startswith("//") or sel.startswith("("):
                    elems = driver.find_elements(By.XPATH, sel)
                else:
                    elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elems:
                    if condition == "clickable" and el.is_displayed() and el.is_enabled():
                        return el
                    elif condition == "visible" and el.is_displayed():
                        return el
                    elif condition == "present":
                        return el
            except Exception:
                continue
        time.sleep(0.4)
    return None


def check_already_logged_in_elsewhere(driver) -> bool:
    """
    Prüft ob User bereits auf anderem Gerät (z.B. Konsole/PC) angemeldet ist
    (z.B. 'Signed Into Another Device' Dialog).
    
    Returns: True wenn "bereits angemeldet" Meldung erscheint
    """
    try:
        page_text = driver.page_source.lower()
        
        # Spezifische Textphrasen des EA 'Signed Into Another Device' Dialogs
        conflict_patterns = [
            "signed into another device",
            "cannot use the fc companion app or web app",
            "while signed into football ultimate team",
            "while signed into ultimate team",
            "sign out from your football ultimate team account",
            "backing out of the mode to the main fc menu",
            "shutting off your console or pc while logged into ultimate team",
            "already logged in",
            "bereits angemeldet",
            "logged in on another device",
            "auf einem anderen gerät",
            "auf einem anderen gerät angemeldet",
            "another device",
            "anderes gerät"
        ]
        
        detected_pattern = None
        for pat in conflict_patterns:
            if pat in page_text:
                detected_pattern = pat
                break
                
        if not detected_pattern:
            return False
            
        # Versuche genauen Text aus dem HTML/Dialog zu extrahieren
        dialog_text = ""
        try:
            for sel in [
                "//h2[contains(., 'Signed Into Another Device') or contains(., 'Another Device') or contains(., 'anderem Gerät')]/..",
                "//h2[contains(., 'Signed Into Another Device')]/parent::*",
                "div.ut-error-view",
                "div.ea-dialog-view",
                "div.view-modal",
                "div.error-message"
            ]:
                elements = driver.find_elements(By.XPATH if sel.startswith("//") else By.CSS_SELECTOR, sel)
                for el in elements:
                    txt = el.text.strip()
                    if txt and any(p in txt.lower() for p in ["another device", "companion app", "ultimate team", "anderes gerät"]):
                        dialog_text = txt
                        break
                if dialog_text:
                    break
        except Exception:
            pass
            
        logger.warning("⚠️ WebApp nicht verfügbar: 'Signed Into Another Device' erkannt!")
        if dialog_text:
            for line in dialog_text.splitlines():
                line = line.strip()
                if line:
                    logger.warning(f"   ℹ️ {line}")
        else:
            logger.warning("   ℹ️ 'Sorry, you cannot use the FC Companion App or Web App while signed into Football Ultimate Team on your Console or PC.'")
            logger.warning("   ℹ️ 'Please sign out from your Football Ultimate Team account on your console by backing out of the mode to the main FC Menu.'")
            
        return True
        
    except Exception as e:
        logger.debug(f"🔍 Debug: check_already_logged_in_elsewhere Fehler: {e}")
        return False


def is_logged_in_ui(driver) -> bool:
    """
    Prüft schnell und zuverlässig im Browser-DOM, ob die WebApp aktuell
    eingeloggt ist und der Ultimate Team Hub bzw. die Navigationsleiste angezeigt wird.
    
    Returns:
        bool: True wenn Hub / Navigation aktiv und sichtbar ist
    """
    if not driver:
        return False
    try:
        # Prüfe ob Driver responsive ist
        _ = driver.current_url
    except Exception:
        return False

    # Schneller Check auf Hub / Tab-Bar Indikatoren
    logged_in_selectors = [
        "button.ut-tab-bar-item.icon-transfer",
        ".ut-tab-bar-item.icon-transfer",
        "button.icon-transfer",
        ".ut-navigation-container-view",
        ".ut-hub-view",
        "button.ut-tab-bar-item",
        "nav.ut-tab-bar",
        ".ut-sectioned-item-list-view"
    ]
    for sel in logged_in_selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems and any(e.is_displayed() for e in elems):
                return True
        except Exception:
            continue
    return False


def login_via_ui(driver, cfg):
    """
    Login über UI mit intelligenter Status-Erkennung, Cookie-Persistenz und 2FA-Unterstützung.
    Returns: True wenn erfolgreich, False wenn Fehler, None wenn "bereits angemeldet"
    """
    username = cfg.get('username', '')
    selectors = cfg.get('ui_selectors', {})
    from selenium.webdriver.common.keys import Keys
    
    # 1. WebApp URL laden
    logger.info("🌐 Öffne EA WebApp...")
    driver.get(cfg['login_url'])
    human_like_delay(2, 3)
    
    # Logge Browser-Identität für Server-Diagnose
    try:
        cur_plat = driver.execute_script("return navigator.platform;")
        cur_ua = driver.execute_script("return navigator.userAgent;")
        logger.debug(f"🔍 Browser-Identität: platform='{cur_plat}', UA='{cur_ua[:40]}...'")
    except Exception:
        pass
        
    _check_and_accept_cookie_banner(driver)
    save_page_diagnostics(driver, "01_page_opened")
    
    # 2. Gespeicherte Cookies laden (falls vorhanden)
    has_cookies = load_cookies(driver, username)
    if has_cookies:
        logger.info("🔄 Aktualisiere Seite für Cookie-Authentifizierung...")
        driver.refresh()
        human_like_delay(2, 4)
        _check_and_accept_cookie_banner(driver)
        save_page_diagnostics(driver, "02_after_cookies_refresh")
    
    random_mouse_movements(driver, num_movements=2)
    
    # 3. Warte intelligent auf aktuellen Status der WebApp (Logged In, Landing Button, Login Form, Device Conflict)
    logger.info("⏳ Warte auf WebApp-Status (prüfe Cookies / Login-Button)...")
    
    start_time = time.time()
    max_wait = 60.0  # Bis zu 60 Sekunden für vollständigen Start auf Server/Xvfb
    app_state = None
    login_btn_elem = None
    email_elem = None
    last_log_time = 0
    diagnostics_taken_15s = False
    
    while time.time() - start_time < max_wait:
        # Cookie Banner & Popouts prüfen und schließen
        dismiss_all_popups(driver, max_passes=2)
        
        # Periodische Status-Logs
        elapsed = int(time.time() - start_time)
        if elapsed > 0 and elapsed % 10 == 0 and elapsed != last_log_time:
            last_log_time = elapsed
            cur_url = driver.current_url
            cur_title = driver.title
            logger.info(f"⏳ WebApp lädt... ({elapsed}s/{int(max_wait)}s) [Titel: '{cur_title}']")
            
        if elapsed >= 15 and not diagnostics_taken_15s:
            diagnostics_taken_15s = True
            save_page_diagnostics(driver, "03_loading_15s")
        
        # Bereits auf anderem Gerät angemeldet?
        if check_already_logged_in_elsewhere(driver):
            save_page_diagnostics(driver, "err_device_conflict")
            return None
            
        # Prüfe ob bereits eingeloggt (Transfer Tab oder Navigation sichtbar)
        for sel in [
            "button.ut-tab-bar-item.icon-transfer",
            ".ut-tab-bar-item.icon-transfer",
            "button.icon-transfer",
            ".ut-navigation-container-view",
            ".ut-hub-view",
            "button.ut-tab-bar-item"
        ]:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                if elems and any(e.is_displayed() for e in elems):
                    logger.info("✅ Login erfolgreich (via Cookies)")
                    save_cookies(driver, username)
                    save_page_diagnostics(driver, "success_already_logged_in")
                    dismiss_all_popups(driver)
                    return True
            except Exception:
                pass
                
        # Prüfe ob direkt auf EA-Anmeldeseite (Email-Feld)
        for sel in ["input[name='email']", "input#email", "input[type='email']", "#email"]:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for e in elems:
                    if e.is_displayed() and e.is_enabled():
                        app_state = "LOGIN_FORM"
                        email_elem = e
                        break
                if app_state == "LOGIN_FORM":
                    break
            except Exception:
                pass
        if app_state == "LOGIN_FORM":
            break
            
        # Prüfe ob Landing-Page Login-Button sichtbar ist
        primary_candidate_selectors = [
            selectors.get('primary_login_button', 'button.btn-standard.call-to-action'),
            "button.btn-standard.call-to-action",
            "button.call-to-action",
            "button.ut-login-button",
            "button.btn-standard.primary",
            "button.btn-standard",
            ".ut-login-view button",
            ".ut-landing-view button",
            "//button[contains(@class, 'btn-standard') and (contains(., 'Login') or contains(., 'Anmelden') or contains(., 'Sign In') or contains(@class, 'call-to-action'))]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'anmelden') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'einloggen')]",
            "//button[contains(@class, 'call-to-action')]",
            "//div[contains(@class, 'ut-login-view')]//button",
            "//div[contains(@class, 'ut-landing-view')]//button",
        ]
        for sel in primary_candidate_selectors:
            try:
                if sel.startswith("//"):
                    elems = driver.find_elements(By.XPATH, sel)
                else:
                    elems = driver.find_elements(By.CSS_SELECTOR, sel)
                for e in elems:
                    try:
                        if e.is_displayed() or "call-to-action" in (e.get_attribute("class") or ""):
                            btn_text = (e.text or "").strip().lower()
                            if any(w in btn_text for w in ["cookie", "datenschutz", "privacy", "settings", "einstellungen"]):
                                continue
                            app_state = "LANDING_LOGIN"
                            login_btn_elem = e
                            break
                    except Exception:
                        continue
                if app_state == "LANDING_LOGIN":
                    break
            except Exception:
                pass
        if app_state == "LANDING_LOGIN":
            break
            
        time.sleep(0.8)
        
    if app_state == "LANDING_LOGIN" and login_btn_elem:
        btn_name = login_btn_elem.text.strip() if login_btn_elem.text else "Login"
        logger.info(f"🔑 Klick auf Login-Button ('{btn_name}')...")
        save_page_diagnostics(driver, "04_landing_button_found")
        human_like_delay(0.5, 1.2)
        try:
            login_btn_elem.click()
        except Exception:
            driver.execute_script("arguments[0].click();", login_btn_elem)
        logger.info("✅ Login-Button geklickt, warte auf Weiterleitung zur EA Anmeldeseite...")
        human_like_delay(2, 4)
        
        # Warte auf Navigation zu signin.ea.com
        start_nav = time.time()
        while time.time() - start_nav < 15:
            if "signin" in driver.current_url.lower() or "accounts.ea" in driver.current_url.lower():
                break
            time.sleep(0.5)
            
    elif not app_state:
        logger.warning(f"⚠️ WebApp-Status nach Wartezeit unklar. URL: '{driver.current_url}', Titel: '{driver.title}'")
        save_page_diagnostics(driver, "05_state_unknown")
            
        # Notfall: Suche nach passenden Buttons auf der Seite und klicke ggf.
        try:
            all_buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in all_buttons:
                btn_txt = (btn.text or "").strip().lower()
                if any(k in btn_txt for k in ["login", "anmelden", "sign in", "einloggen"]) or "call-to-action" in (btn.get_attribute("class") or ""):
                    logger.info(f"🔄 Notfall-Klick auf gefundenen Button: '{btn.text.strip()}'")
                    driver.execute_script("arguments[0].click();", btn)
                    human_like_delay(2, 4)
                    break
        except Exception:
            pass
        
    # Warte bis Login-Formular (signin.ea.com) geladen ist
    logger.info("⏳ Warte auf EA Anmeldeseite...")
    email_selectors = [
        "input[name='email']",
        "input#email",
        "input[type='email']",
        "#email",
        selectors.get('username', "input[name='email']"),
        "//input[@type='email' or @name='email' or @id='email']"
    ]
    email_field = email_elem or find_element_with_fallbacks(driver, email_selectors, timeout=25, condition="clickable")
    
    if not email_field:
        logger.error(f"❌ Email-Eingabefeld nicht gefunden! (URL: '{driver.current_url}', Titel: '{driver.title}')")
        save_page_diagnostics(driver, "06_email_field_missing")
        return False

    # Email eingeben
    try:
        human_like_delay(0.4, 0.8)
        email_field.click()
        time.sleep(0.2)
        email_field.send_keys(Keys.CONTROL + "a")
        email_field.send_keys(Keys.BACKSPACE)
        email_field.clear()
        time.sleep(0.2)
        human_type(email_field, cfg['username'])
        human_like_delay(0.5, 1.0)
        
        # Verifiziere Email-Wert
        val = email_field.get_attribute('value')
        if not val:
            logger.warning("⚠️ Email-Feld war noch leer, versuche direkte Eingabe...")
            email_field.send_keys(cfg['username'])
            val = email_field.get_attribute('value')
            
        if not val or '@' not in val:
            logger.error(f"❌ Ungültiger Email-Wert im Feld: '{val}'! Bitte überprüfe EA_USERNAME in .env oder config.yaml.")
            return False
            
        masked = f"{val[:3]}***{val[-4:] if len(val) > 7 else ''}"
        logger.info(f"✅ Email erfolgreich eingegeben ({masked})")
    except Exception as e:
        logger.error(f"❌ Email-Eingabe fehlgeschlagen: {e}")
        return False
    
    # Next klicken
    try:
        next_selectors = [
            "a#logInBtn",
            "button#logInBtn",
            "#logInBtn",
            selectors.get('next_button', 'a#logInBtn'),
            "button[type='submit']",
            "//button[contains(., 'Next') or contains(., 'Weiter') or contains(., 'Sign in')]",
            "//a[contains(., 'Next') or contains(., 'Weiter') or contains(., 'Sign in')]"
        ]
        next_btn = find_element_with_fallbacks(driver, next_selectors, timeout=8, condition="clickable")
        if next_btn:
            human_like_delay(0.4, 0.8)
            next_btn.click()
        else:
            email_field.send_keys(Keys.RETURN)
            
        logger.info("✅ 'Next' geklickt")
        
        # Prüfe sofort auf EA-Validierungsfehler (z. B. ungültige E-Mail)
        time.sleep(1.0)
        for err in driver.find_elements(By.CSS_SELECTOR, ".origin-ux-element-error-message, .error, .otkform-error, .banner-message"):
            if err.is_displayed() and err.text.strip():
                logger.error(f"❌ EA meldet Fehler bei der E-Mail-Adresse: {err.text.strip()}")
                return False
    except Exception as e:
        logger.error(f"❌ Next-Button fehlgeschlagen: {e}")
        return False
    
    # Passwort eingeben - WICHTIG: Warte bis das Feld wirklich SICHTBAR ist (Schritt 2)!
    logger.info("⏳ Warte auf Passwort-Feld (Schritt 2)...")
    pwd_selectors = [
        "input[name='password']",
        "input#password",
        "input[type='password']",
        selectors.get('password', "input[name='password']"),
        "//input[@type='password' or @name='password' or @id='password']"
    ]
    pwd_field = find_element_with_fallbacks(driver, pwd_selectors, timeout=20, condition="visible")
    
    if not pwd_field:
        logger.error("❌ Passwort-Feld nicht sichtbar geworden!")
        return False

    try:
        human_like_delay(0.4, 0.8)
        pwd_field.click()
        time.sleep(0.2)
        pwd_field.send_keys(Keys.CONTROL + "a")
        pwd_field.send_keys(Keys.BACKSPACE)
        pwd_field.clear()
        time.sleep(0.2)
        human_type(pwd_field, cfg['password'])
        human_like_delay(0.5, 1.0)
        logger.info("✅ Passwort eingegeben")
    except Exception as e:
        logger.error(f"❌ Passwort-Eingabe fehlgeschlagen: {e}")
        return False
    
    # Sign In klicken
    try:
        sign_selectors = [
            "a#logInBtn",
            "button#logInBtn",
            "#logInBtn",
            selectors.get('sign_in_button', 'a#logInBtn'),
            "button[type='submit']",
            "//button[contains(., 'Sign in') or contains(., 'Anmelden') or contains(., 'Log In')]",
            "//a[contains(., 'Sign in') or contains(., 'Anmelden') or contains(., 'Log In')]"
        ]
        sign_btn = find_element_with_fallbacks(driver, sign_selectors, timeout=8, condition="clickable")
        if sign_btn:
            human_like_delay(0.4, 0.8)
            sign_btn.click()
        else:
            pwd_field.send_keys(Keys.RETURN)
            
        logger.info("✅ 'Sign In' geklickt")
    except Exception as e:
        logger.error(f"❌ Sign In fehlgeschlagen: {e}")
        return False
    
    human_like_delay(2, 4)
    
    # Prüfe auf Login-Fehlermeldungen auf der Seite
    for err in driver.find_elements(By.CSS_SELECTOR, ".origin-ux-element-error-message, .error, .banner-message, .otkform-error"):
        if err.is_displayed() and err.text.strip():
            logger.error(f"❌ EA-Login-Fehler: {err.text.strip()}")
            return False
            
    # 2FA behandeln
    wait = WebDriverWait(driver, 20)
    if not handle_2fa(driver, wait):
        logger.error("❌ 2FA fehlgeschlagen")
        return False
    
    # Warte bis WebApp geladen ist
    logger.info("⏳ Warte auf Laden der WebApp...")
    hub_loaded = False
    start_wait_hub = time.time()
    while time.time() - start_wait_hub < 40:
        # Cookie Banner & Popouts prüfen und schließen
        dismiss_all_popups(driver, max_passes=2)
        
        # Prüfe ob nach dem Login 'Signed Into Another Device' erscheint
        if check_already_logged_in_elsewhere(driver):
            save_page_diagnostics(driver, "err_device_conflict_post_login")
            return None
            
        for sel in [
            "button.ut-tab-bar-item.icon-transfer",
            ".ut-tab-bar-item.icon-transfer",
            "button.icon-transfer",
            ".ut-navigation-container-view",
            ".ut-hub-view",
            "button.ut-tab-bar-item"
        ]:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, sel)
                if elems and any(e.is_displayed() for e in elems):
                    hub_loaded = True
                    break
            except Exception:
                pass
        if hub_loaded:
            break
        time.sleep(1.0)
        
    if hub_loaded:
        save_cookies(driver, username)
        logger.info("✅ Login erfolgreich und Ultimate Team Hub geladen!\n")
        dismiss_all_popups(driver)
        return True
    else:
        # Nochmalige Konfliktprüfung bei Timeout
        if check_already_logged_in_elsewhere(driver):
            save_page_diagnostics(driver, "err_device_conflict_timeout")
            return None
            
        logger.error("❌ WebApp Hub konnte nach Login nicht geladen werden")
        return False


# ============================================================================
# TRANSFER LIST NAVIGATION
# ============================================================================

def _is_on_transfer_list_view(driver) -> bool:
    """Prüft ob der Browser sich aktuell in der Transfer-Listen-Ansicht befindet."""
    tl_signatures = [
        "//div[contains(@class, 'ut-sectioned-item-list-view')]",
        "//section[contains(@class, 'ut-sectioned-item-list-view')]",
        "//div[contains(@class, 'ut-pinned-list-container')]",
        "//div[contains(@class, 'ut-item-list-view')]",
        "//ul[contains(@class, 'itemList')]",
        "//button[contains(@class, 'section-header-btn') and (contains(., 'Re-list') or contains(., 're-list') or contains(., 'Erneut') or contains(., 'neu') or contains(., 'Clear') or contains(., 'löschen'))]",
        "//h1[contains(., 'Transfer List') or contains(., 'Transferliste')]",
        "//div[contains(@class, 'title') and (contains(., 'Transfer List') or contains(., 'Transferliste'))]"
    ]
    for xpath in tl_signatures:
        try:
            elems = driver.find_elements(By.XPATH, xpath)
            if elems and any(e.is_displayed() for e in elems):
                return True
        except Exception:
            continue
    return False


def navigate_to_transfer_list(driver, cfg):
    """
    Navigiert zur Transfer-Liste mit robuster Verifikation und Popout-Erkennung.
    Returns: True wenn erfolgreich auf Transfer-Liste angelangt
    """
    selectors = cfg.get('ui_selectors', {})
    
    # 1. Vorab alle Popouts / News / Dialoge schließen
    dismiss_all_popups(driver)
    
    # 2. Prüfe ob wir bereits auf der Transfer-Liste sind
    if _is_on_transfer_list_view(driver):
        logger.info("✅ Bereits auf der Transfer-Liste (View aktiv)")
        return True

    try:
        # Natürliches Verhalten: User schaut sich erst um
        random_scroll_behavior(driver)
        human_like_delay(0.5, 1.0)
        
        # 3. Transfer-Tile Selektoren definieren
        tile_selectors = [
            selectors.get('transfer_tile', '.tile.col-1-2.ut-tile-transfer-list.ut-tile-transfers'),
            ".tile.col-1-2.ut-tile-transfer-list.ut-tile-transfers",
            ".ut-tile-transfer-list",
            "div.ut-tile-transfer-list",
            "//div[contains(@class, 'ut-tile-transfer-list')]",
            "//div[contains(@class, 'tile') and (contains(., 'Transfer List') or contains(., 'Transferliste'))]"
        ]
        
        # Prüfe ob Transfer-Tile bereits sichtbar ist (wir sind schon im Transfers-Tab)
        transfer_tile = find_element_with_fallbacks(driver, tile_selectors, timeout=3, condition="visible")
        
        # Falls nicht sichtbar, klicke Transfers-Tab in der Navigationsleiste
        if not transfer_tile:
            tab_selectors = [
                selectors.get('transfer_tab', 'button.ut-tab-bar-item.icon-transfer'),
                "button.ut-tab-bar-item.icon-transfer",
                "button.icon-transfer",
                ".ut-tab-bar-item.icon-transfer",
                "//button[contains(@class, 'icon-transfer')]",
                "//button[contains(@class, 'ut-tab-bar-item') and contains(., 'Transfers')]",
                "//button[contains(., 'Transfers')]"
            ]
            
            transfer_tab = find_element_with_fallbacks(driver, tab_selectors, timeout=8, condition="clickable")
            if not transfer_tab:
                dismiss_all_popups(driver)
                transfer_tab = find_element_with_fallbacks(driver, tab_selectors, timeout=8, condition="clickable")
                
            if not transfer_tab:
                # Prüfe Gerätekonflikt
                if check_already_logged_in_elsewhere(driver):
                    save_page_diagnostics(driver, "err_device_conflict_nav")
                    return False
                    
                # Prüfe ob WebApp ausgeloggt ist oder Session abgelaufen ist
                if not is_logged_in_ui(driver):
                    logger.warning("⚠️ Transfer-Tab nicht gefunden: Session möglicherweise abgelaufen. Versuche automatische Re-Authentifizierung...")
                    login_recovered = login_via_ui(driver, cfg)
                    if login_recovered is True:
                        logger.info("🔄 Re-Login erfolgreich! Wiederhole Navigation zur Transfer-Liste...")
                        dismiss_all_popups(driver)
                        # Prüfe direkt ob wir nach Login auf Transfer List oder Hub gelandet sind
                        if _is_on_transfer_list_view(driver):
                            logger.info("✅ Bereits auf der Transfer-Liste (nach Re-Login)")
                            return True
                        transfer_tile = find_element_with_fallbacks(driver, tile_selectors, timeout=4, condition="visible")
                        if not transfer_tile:
                            transfer_tab = find_element_with_fallbacks(driver, tab_selectors, timeout=8, condition="clickable")
                
            if not transfer_tab and not transfer_tile:
                logger.error("❌ Transfer-Tab nicht gefunden")
                save_page_diagnostics(driver, "err_transfer_tab_not_found")
                return False
                
            if transfer_tab and not transfer_tile:
                random_mouse_movements(driver, num_movements=2)
                human_like_delay(0.3, 0.6)
                
                try:
                    transfer_tab.click()
                except Exception:
                    dismiss_all_popups(driver)
                    try:
                        driver.execute_script("arguments[0].click();", transfer_tab)
                    except Exception as e:
                        logger.error(f"❌ Klick auf Transfer-Tab fehlgeschlagen: {e}")
                        return False
                    
                logger.info("🖱️ Klick auf 'Transfers'-Tab (erfolgreich geöffnet)")
                human_like_delay(1.5, 2.5)
                dismiss_all_popups(driver)
                
                # Jetzt Transfer-Tile auf der Transfers-Hub-Seite suchen
                transfer_tile = find_element_with_fallbacks(driver, tile_selectors, timeout=8, condition="visible")
                if not transfer_tile:
                    dismiss_all_popups(driver)
                    transfer_tile = find_element_with_fallbacks(driver, tile_selectors, timeout=6, condition="visible")
        
        if not transfer_tile:
            # Prüfe ob wir vielleicht schon direkt auf der Transfer-Liste sind
            if _is_on_transfer_list_view(driver):
                logger.info("✅ Bereits auf der Transfer-Liste")
                return True
            logger.error("❌ Transfer-Liste Tile nicht gefunden")
            save_page_diagnostics(driver, "err_transfer_tile_not_found")
            return False
            
        human_like_delay(0.4, 0.8)
        
        # 4. Klicke Transfer-Liste Kachel mit Multi-Strategie
        logger.info("🖱️ Öffne 'Transfer List'-Kachel...")
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center', behavior: 'smooth'});", transfer_tile)
            time.sleep(0.3)
        except Exception:
            pass
            
        tile_clicked = False
        try:
            tile_clicked = human_click(driver, transfer_tile, method="move")
        except Exception:
            pass
            
        if not tile_clicked:
            try:
                transfer_tile.click()
                tile_clicked = True
            except Exception:
                pass
                
        if not tile_clicked:
            try:
                driver.execute_script("""
                    arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                    arguments[0].click();
                """, transfer_tile)
                tile_clicked = True
            except Exception:
                pass
                
        # 5. Verifikations-Schleife: Warten bis Transfer-Liste tatsächlich geladen ist
        start_wait = time.time()
        max_verify_time = 12.0
        verified = False
        
        while time.time() - start_wait < max_verify_time:
            if _is_on_transfer_list_view(driver):
                verified = True
                break
                
            dismiss_all_popups(driver)
            
            # Nach 4 Sekunden erneut versuchen zu klicken falls wir noch auf Hub feststecken
            elapsed = time.time() - start_wait
            if elapsed > 4.0:
                try:
                    tile_retry = find_element_with_fallbacks(driver, tile_selectors, timeout=1, condition="present")
                    if tile_retry and tile_retry.is_displayed():
                        driver.execute_script("""
                            arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                            arguments[0].click();
                        """, tile_retry)
                except Exception:
                    pass
                    
            time.sleep(0.6)
            
        if not verified:
            logger.error("❌ Transfer-Listen-Ansicht konnte nicht geladen werden (Timeout)")
            save_page_diagnostics(driver, "err_transfer_list_load_timeout")
            return False
            
        logger.info("🖱️ 'Transfer List' erfolgreich geöffnet (View aktiv)")
        human_like_delay(1.0, 2.0)
        dismiss_all_popups(driver)
        return True
        
    except Exception as e:
        logger.error(f"❌ Transfer-Navigation fehlgeschlagen: {e}")
        save_page_diagnostics(driver, "err_transfer_nav_exception")
        return False


# ============================================================================
# RE-LIST FUNCTION
# ============================================================================

def relist_all_transfer_items(driver, cfg):
    """
    Bietet alle Spieler auf der Transferliste neu an.
    Drückt den 'Re-list All'-Button und bestätigt die Aktion im Modal-Dialog.
    
    Returns: Anzahl der neu angebotenen Spieler (>0 bei Erfolg, 0 wenn keine Items, -1 bei Fehler)
    """
    selectors = cfg.get('ui_selectors', {})
    
    # 1. Navigiere zur Transfer-Liste
    if not navigate_to_transfer_list(driver, cfg):
        logger.error("❌ Konnte nicht zur Transfer-Liste navigieren")
        return -1
    
    try:
        # Natürliches Verhalten: Leichter Scroll
        random_scroll_behavior(driver)
        human_like_delay(0.5, 1.0)
        
        # 2. Dynamische Warterunde für asynchrones Laden der Tradepile & Buttons
        # EA WebApp lädt tradepile Items per AJAX (/ut/game/fc27/tradepile).
        # Auf Ubuntu / Remote-Servern kann das 3-8 Sekunden dauern.
        logger.info("⏳ Lade Transferliste & prüfe abgelaufene Karten...")
        
        # Finde den echten "Re-list All" Button (niemals Clear Sold oder leere Buttons)
        def _is_valid_relist_btn(btn):
            try:
                txt = (btn.get_attribute("textContent") or btn.text or "").strip().lower()
                if not txt:
                    return False
                if any(bad in txt for bad in ['clear', 'sold', 'löschen', 'verkauft', 'abholen', 'claim']):
                    return False
                if any(good in txt for good in ['re-list', 'relist', 'erneut', 'neu anbieten', 'anbieten']):
                    return True
                return False
            except Exception:
                return False

        relist_xpaths = [
            "//header[contains(., 'Unsold') or contains(., 'Nicht verkauft') or contains(., 'Abgelaufen')]//button[contains(@class, 'section-header-btn')]",
            "//button[contains(@class, 'section-header-btn') and (contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 're-list') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'erneut') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'neu anbieten'))]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 're-list all') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 're-list')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'erneut anbieten') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'neu anbieten')]",
        ]
        relist_css = [
            ".ut-sectioned-item-list-view header button.section-header-btn",
            "button.btn-standard.section-header-btn.mini.primary",
            "button.section-header-btn.mini.primary",
            "button.btn-standard.section-header-btn",
        ]
        
        start_poll = time.time()
        max_poll_time = 15.0
        parsed_data = {'total_count': 0, 'unique_count': 0, 'players': [], 'grouped': []}
        relist_button = None
        
        while time.time() - start_poll < max_poll_time:
            dismiss_all_popups(driver)
            
            # Extrahiere abgelaufene Spielerdaten aus aktuellem DOM
            try:
                page_html = driver.page_source
                parsed_data = parse_transfer_list_html(page_html)
            except Exception as e:
                logger.debug(f"🔍 Fehler bei Spieler-Extraktion: {e}")
                
            # Suche nach Relist-Button
            found_btn = None
            for xpath in relist_xpaths:
                try:
                    candidates = driver.find_elements(By.XPATH, xpath)
                    for btn in candidates:
                        if _is_valid_relist_btn(btn) and (btn.is_displayed() or btn.is_enabled()):
                            found_btn = btn
                            break
                    if found_btn:
                        break
                except Exception:
                    continue
                    
            if not found_btn:
                for css in relist_css:
                    try:
                        candidates = driver.find_elements(By.CSS_SELECTOR, css)
                        for btn in candidates:
                            if _is_valid_relist_btn(btn) and (btn.is_displayed() or btn.is_enabled()):
                                found_btn = btn
                                break
                        if found_btn:
                            break
                    except Exception:
                        continue
                        
            if found_btn:
                relist_button = found_btn
                
            # Wenn Spieler gefunden wurden oder Relist-Button da ist, sind die Daten geladen
            if parsed_data['total_count'] > 0 or relist_button:
                break
                
            time.sleep(0.8)
            
        total_players = parsed_data['total_count']
        grouped_players = parsed_data['grouped']
        
        if total_players > 0:
            logger.info(f"📋 {total_players} abgelaufene Spieler auf der Transferliste erkannt ({parsed_data['unique_count']} verschiedene):")
            for g in grouped_players:
                logger.info(f"   • {g['count']}x {g['name']} ({g['rating']}, {g['position']})")
                
            # Detailliertes Debug-Log für den Server (jeder einzelne Spieler mit Preisen)
            logger.debug(f"🔍 Detaillierte Spielerübersicht ({total_players} Karten):")
            for idx, p in enumerate(parsed_data['players'], 1):
                logger.debug(
                    f"   [{idx:02d}/{total_players:02d}] {p['name']} (OVR {p['rating']}, {p['position']}) "
                    f"| Start: {p['start_price']} | Sofortkauf: {p['buy_now_price']} | Gebot: {p['bid_price']} | Status: {p['status']}"
                )
        else:
            logger.info("📋 Suche nach 'Re-list All' Button...")
            
        # Falls kein Button gefunden wurde:
        if not relist_button:
            if total_players == 0:
                logger.info("ℹ️ Kein 'Re-list All' Button vorhanden (keine abgelaufenen Items auf der Transferliste)")
                save_page_diagnostics(driver, "transfer_list_empty")
                webhook_url = cfg.get('discord_webhook')
                if webhook_url:
                    try:
                        send_no_items_embed(webhook_url)
                    except Exception:
                        pass
                return 0
            else:
                logger.warning(f"⚠️ 'Re-list All' Button konnte nicht gefunden werden (trotz {total_players} abgelaufener Spieler)!")
                save_page_diagnostics(driver, "relist_button_missing_with_players")
                return 0
                
        # Prüfe ob Button deaktiviert ist
        try:
            is_disabled = (
                relist_button.get_attribute("disabled") is not None or
                "disabled" in (relist_button.get_attribute("class") or "").lower() or
                not relist_button.is_enabled()
            )
            if is_disabled:
                logger.info("ℹ️ 'Re-list All' Button ist deaktiviert (keine abgelaufenen Spieler zum Anbieten)")
                webhook_url = cfg.get('discord_webhook')
                if webhook_url:
                    try:
                        send_no_items_embed(webhook_url)
                    except Exception:
                        pass
                return 0
        except Exception:
            pass

        # 3. Klicke "Re-list All" Button mit 3-Stufen Fallback
        logger.info("🔄 Klicke 'Re-list All' Button...")
        
        # Scroll ins Zentrum des Sichtfelds
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center', behavior: 'smooth'});", relist_button)
            human_like_delay(0.4, 0.8)
        except Exception:
            pass
            
        clicked = False
        # Stufe 1: ActionChains (Menschliche Mausbewegung)
        try:
            clicked = human_click(driver, relist_button, method="move")
        except Exception:
            clicked = False
            
        # Stufe 2: Normaler Selenium Klick
        if not clicked:
            try:
                relist_button.click()
                clicked = True
            except Exception:
                pass
                
        # Stufe 3: JavaScript Klick (Garantiert, umgeht Overlay/Intercepting)
        if not clicked:
            try:
                driver.execute_script("""
                    arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                    arguments[0].click();
                """, relist_button)
                clicked = True
            except Exception as e:
                logger.error(f"❌ Klick auf 'Re-list All' fehlgeschlagen: {e}")
                return -1
                
        logger.info("✅ 'Re-list All' Button erfolgreich geklickt")
        
        # 4. Warte auf Bestätigungsdialog ("Yes" / "Ja")
        logger.info("⏳ Warte auf Bestätigungsdialog ('Yes' / 'Ja')...")
        human_like_delay(1.5, 2.5)
        
        confirm_btn = None
        confirm_selectors = [
            "//div[contains(@class, 'ea-dialog-view') or contains(@class, 'view-modal') or contains(@class, 'dialog')]//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'yes') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ja') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ok') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'confirm') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'erneut') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 're-list')]",
            "//div[contains(@class, 'ea-dialog-view') or contains(@class, 'view-modal')]//div[contains(@class, 'ut-button-group')]//button[contains(@class, 'primary')]",
            "//div[contains(@class, 'ea-dialog-view') or contains(@class, 'view-modal')]//button[contains(@class, 'btn-standard')]",
        ]
        
        def _is_valid_confirm_btn(el):
            try:
                txt = (el.get_attribute("textContent") or el.text or "").strip().lower()
                if any(bad in txt for bad in ['cancel', 'abbrechen', 'nein', 'no', 'clear', 'sold', 'löschen', 'close']):
                    return False
                if txt and any(good in txt for good in ['yes', 'ja', 'ok', 'confirm', 'bestätigen', 're-list', 'erneut', 'weiter']):
                    return True
                cls = (el.get_attribute("class") or "").lower()
                if 'primary' in cls and (not txt or txt in ['yes', 'ja', 'ok']):
                    return True
                return False
            except Exception:
                return False
        
        for sel in confirm_selectors:
            try:
                if sel.startswith("//"):
                    elements = driver.find_elements(By.XPATH, sel)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, sel)
                    
                for el in elements:
                    if _is_valid_confirm_btn(el) and (el.is_displayed() or el.is_enabled()):
                        confirm_btn = el
                        logger.info(f"   ✓ Bestätigungs-Button gefunden: '{el.text.strip() or el.get_attribute('textContent') or ''}'")
                        break
                if confirm_btn:
                    break
            except Exception:
                continue
                
        if confirm_btn:
            confirm_clicked = False
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", confirm_btn)
                human_like_delay(0.3, 0.6)
            except Exception:
                pass
                
            try:
                confirm_clicked = human_click(driver, confirm_btn, method="move")
            except Exception:
                pass
            if not confirm_clicked:
                try:
                    confirm_btn.click()
                    confirm_clicked = True
                except Exception:
                    pass
            if not confirm_clicked:
                try:
                    driver.execute_script("""
                        arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                        arguments[0].click();
                    """, confirm_btn)
                    confirm_clicked = True
                except Exception:
                    pass
                    
            if confirm_clicked:
                logger.info("✅ Bestätigung ('Yes' / 'Ja') erfolgreich geklickt")
            else:
                logger.warning("⚠️ Konnte Bestätigungs-Button nicht klicken")
        else:
            logger.info("ℹ️ Kein Bestätigungsdialog erschienen (Re-List direkt ausgeführt)")
            
        # 5. Warte auf Abschluss der Server-Aktion
        logger.info("⏳ Warte auf Abschluss der Re-List Aktion...")
        human_like_delay(3, 5)
        
        count = total_players if total_players > 0 else 1
        
        logger.info(f"✅ ERFOLGREICH NEU ANGEBOTEN: {count} Spieler")
        
        # Sende Discord Rich Embed wenn Webhook konfiguriert
        webhook_url = cfg.get('discord_webhook')
        if webhook_url and total_players > 0:
            try:
                send_relist_embed(webhook_url, total_players, grouped_players)
            except Exception as embed_err:
                logger.debug(f"🔍 Discord-Embed Fehler: {embed_err}")
                
        return count
        
    except Exception as e:
        logger.error(f"❌ Re-List-Fehler: {e}")
        import traceback
        traceback.print_exc()
        return -1


# ============================================================================
# AUTOBUYER (PLACEHOLDER)
# ============================================================================

def autobuyer(driver, cfg):
    """
    Autobuyer-Funktion (für später).
    
    Returns: Anzahl der gekauften Spieler
    """
    logger.info("\n⏳ AUTOBUYER: Noch nicht implementiert")
    logger.info("   Wird nach Re-List-Feature entwickelt\n")
    return 0


# ============================================================================
# MAIN JOB
# ============================================================================

def main_job(cfg, reuse_driver=None):
    """
    Hauptjob: Login und Re-Listen aller Transfermarkt-Spieler.
    
    Args:
        cfg: Konfiguration
        reuse_driver: Bestehender WebDriver (für Live-Session)
        
    Returns:
        (driver, status) wobei status = 'success', 'already_logged_in', 'error'
    """
    # Statistics initialisieren (Enterprise)
    stats = BotStatistics()
    
    driver = reuse_driver
    created_driver = False
    
    try:
        print("\n" + "="*60)
        logger.info("EA FC27 WebApp Bot - Gestartet")
        logger.info("="*60 + "\n")
        
        # Erstelle Browser nur wenn nicht wiederverwendet
        if driver is None:
            driver = init_browser(headless=cfg.get('headless', True))
            created_driver = True
        else:
            logger.debug("♻️ Verwende bestehende Browser-Session")
            
            # Prüfe ob Browser noch aktiv ist
            try:
                _ = driver.window_handles
            except Exception as e:
                logger.warning("⚠️ Browser-Session nicht mehr gültig: {e}")
                logger.debug("   Erstelle neuen Browser...")
                driver = init_browser(headless=cfg.get('headless', True))
                created_driver = True
        
        # Login
        logger.info("🔐 Login...")
        start_time = time.time()
        login_result = login_via_ui(driver, cfg)
        login_duration = time.time() - start_time
        
        # Record Login Statistics
        stats.record_login(
            success=login_result is True,
            duration=login_duration,
            error=None if login_result else "Login fehlgeschlagen"
        )
        
        if login_result is None:
            logger.error("❌ Bot-Job fehlgeschlagen: Spieler konnten nicht neu angeboten werden (bereits auf anderem Gerät angemeldet)")
            if created_driver and cfg.get('headless', True):
                driver.quit()
                return None, 'already_logged_in'
            return driver, 'already_logged_in'
        
        if not login_result:
            logger.error("❌ Login fehlgeschlagen!")
            if created_driver and cfg.get('headless', True):
                driver.quit()
                return None, 'error'
            return driver, 'error'
        
        # Re-Liste alle Spieler
        logger.info("🔄 Re-Liste Transfer-Spieler...")
        start_time = time.time()
        relisted_count = relist_all_transfer_items(driver, cfg)
        relist_duration = time.time() - start_time
        
        # Record Re-List Statistics
        stats.record_relist(
            success=relisted_count >= 0,
            players=relisted_count if relisted_count > 0 else 0,
            duration=relist_duration,
            error=None if relisted_count >= 0 else "Re-List fehlgeschlagen"
        )
        
        if relisted_count > 0:
            logger.debug(f"\n✅ {relisted_count} Spieler neu angeboten!")
        else:
            logger.debug("\n⚠ Keine Spieler neu angeboten")
            logger.debug("   (Keine abgelaufenen Items gefunden)")
        
        print("\n" + "="*60)
        logger.info("Job abgeschlossen!")
        logger.info("="*60 + "\n")
        
        # Session beenden und Statistiken anzeigen (Enterprise)
        stats.end_session()
        stats.print_summary()
        
        # Wechsle zu Idle-Tab nach Job (Live-Session)
        if not cfg.get('headless', True) and driver:
            switch_to_idle_tab(driver)
            logger.info("ℹ️ Browser bleibt für Live-Session offen (Idle-Tab aktiv)")
            return driver, 'success'
        
        # Browser offen lassen wenn headless=false (Live-Session)
        if not cfg.get('headless', True):
            logger.info("ℹ️ Browser bleibt für Live-Session offen")
            return driver, 'success'
        
        # Ansonsten schließen
        if created_driver:
            human_like_delay(2, 3)
            driver.quit()
        
        return None, 'success'
        
    except Exception as e:
        # Record Error Statistics
        stats.record_error(
            error_type=type(e).__name__,
            message=str(e),
            context="main_job"
        )
        stats.end_session()
        
        logger.error("❌ Fehler im Hauptjob: {e}")
        import traceback
        traceback.print_exc()
        
        # Versuche Browser zu schließen bei Fehler
        if driver:
            try:
                # Prüfe ob Browser noch läuft
                _ = driver.window_handles
                
                if created_driver and cfg.get('headless', True):
                    try:
                        driver.quit()
                    except:
                        pass
            except:
                # Browser ist bereits tot
                logger.debug("   ℹ️ Browser-Session bereits beendet")
                driver = None
        
        # Bei Live-Session: Versuche Browser neu zu starten
        if not cfg.get('headless', True):
            logger.debug("   🔄 Versuche Browser-Neustart bei nächstem Job...")
            return None, 'error'  # Signalisiere Neustart erforderlich
        
        return driver if not cfg.get('headless', True) else None, 'error'


def main():
    """Startet Bot mit Scheduler und Live-Session Support."""
    config_path = Path(__file__).parent / "config.yaml"
    
    # Config-Validierung (Enterprise)
    try:
        cfg = validate_config(config_path)
        logger.info("✅ Konfiguration validiert")
    except ConfigValidationError as e:
        logger.critical(f"💥 Config-Validierung fehlgeschlagen:\n{e}")
        return 1
    except FileNotFoundError as e:
        logger.critical(f"💥 Konfigurationsdatei nicht gefunden: {e}")
        return 1
    
    schedule = cfg.get('schedule', {'type': 'interval', 'hours': 1})
    
    # Test-Modus: Einmalige Ausführung
    if cfg.get('test_mode', False):
        logger.info("🧪 TEST-MODUS: Einmalige Ausführung\n")
        driver, status = main_job(cfg)
        if driver and not cfg.get('headless', True):
            input("\nDrücke Enter zum Beenden...")
            driver.quit()
        return
    
    # Live-Session Modus (headless=false): Browser bleibt offen
    if not cfg.get('headless', True):
        logger.info("🔄 LIVE-SESSION MODUS")
        logger.info("   Browser bleibt zwischen Jobs offen")
        logger.info("   Drücke Ctrl+C zum Beenden\n")
        
        shared_driver = None
        retry_delay = 15 * 60  # 15 Minuten in Sekunden
        MAX_RETRIES = 3
        retry_count = 0
        
        try:
            while True:
                # Prüfe ob Nachtpause (1:00 - 6:00 Uhr)
                if is_night_time(start_hour=1, end_hour=6):
                    sleep_seconds, wake_time = calculate_sleep_until_morning(wake_hour=6)
                    sleep_hours = sleep_seconds / 3600
                    logger.debug(f"\n😴 NACHTPAUSE (1:00 - 6:00 Uhr)")
                    logger.debug(f"   Schlafe für {sleep_hours:.1f} Stunden")
                    logger.debug(f"   Aufwachen um: {wake_time.strftime('%H:%M:%S')}")
                    
                    # Wechsle zu Idle-Tab während Nachtpause
                    if shared_driver:
                        switch_to_idle_tab(shared_driver)
                    
                    time.sleep(sleep_seconds)
                    logger.debug("\n☀️ Guten Morgen! Bot startet wieder...\n")
                    continue
                
                # Wechsle zurück zur WebApp vor Job
                if shared_driver:
                    logger.debug("\n🔄 Starte Job...")
                    if not switch_to_webapp_tab(shared_driver, cfg['login_url']):
                        logger.error("❌ Konnte nicht zur WebApp wechseln")
                        human_like_delay(2, 3)
                        continue
                    human_like_delay(1, 2)
                
                # Job mit Error-Recovery ausführen
                try:
                    shared_driver, status = main_job(cfg, reuse_driver=shared_driver)
                    retry_count = 0  # Reset bei Erfolg
                    
                except WebDriverException as e:
                    retry_count += 1
                    logger.error(f"❌ Browser-Crash (Versuch {retry_count}/{MAX_RETRIES}): {e}", exc_info=True)
                    
                    # Browser aufräumen
                    if shared_driver:
                        try:
                            shared_driver.quit()
                        except:
                            pass
                        shared_driver = None
                    
                    # Retry oder Aufgeben
                    if retry_count < MAX_RETRIES:
                        logger.info(f"🔄 Neustart in 10 Sekunden...")
                        time.sleep(10)
                        
                        # Browser neu starten
                        try:
                            shared_driver = init_browser(headless=False)
                            logger.info("✅ Browser neu gestartet")
                            human_like_delay(2, 3)
                            continue
                        except Exception as restart_error:
                            logger.error(f"❌ Browser-Neustart fehlgeschlagen: {restart_error}")
                            time.sleep(retry_delay)
                            continue
                    else:
                        logger.critical(f"💥 Maximale Retry-Versuche ({MAX_RETRIES}) erreicht!")
                        raise
                
                except Exception as e:
                    logger.error(f"❌ Unerwarteter Fehler: {e}", exc_info=True)
                    time.sleep(retry_delay)
                    continue
                
                if shared_driver and status == 'already_logged_in':
                    switch_to_idle_tab(shared_driver)
                
                # Normale Wartezeit: 1h 1min bis 1h 20min (zufällig)
                base_seconds = 3600  # 1 Stunde
                random_extra = random.randint(10, 200)  # 10-200 Sekunden
                wait_seconds = base_seconds + random_extra
                
                wait_minutes = wait_seconds // 60
                next_run = datetime.now() + timedelta(seconds=wait_seconds)
                logger.debug(f"\n⏳ Nächster Job in {wait_minutes} Minuten ({wait_minutes // 60}h {wait_minutes % 60}min)")
                logger.debug(f"   Geplante Uhrzeit: {next_run.strftime('%H:%M:%S')}")
                logger.debug(f"   WebApp im Hintergrund (Idle-Tab aktiv)")
                time.sleep(wait_seconds)
                
        except KeyboardInterrupt:
            logger.debug("\n✓ Bot gestoppt")
            if shared_driver:
                try:
                    shared_driver.quit()
                except:
                    pass
        return
    
    # Headless-Modus mit manueller Loop (für variable Wartezeiten)
    logger.info(f"⏰ SCHEDULER-MODUS (Headless)")
    logger.info(f"   Alle ~1 Stunde (1h 1min bis 1h 20min zufällig)")
    logger.info(f"   Nachtpause: 1:00 - 6:00 Uhr")
    logger.info("   Drücke Ctrl+C zum Beenden\n")
    
    try:
        while True:
            # Prüfe ob Nachtpause (1:00 - 6:00 Uhr)
            if is_night_time(start_hour=1, end_hour=6):
                sleep_seconds, wake_time = calculate_sleep_until_morning(wake_hour=6)
                sleep_hours = sleep_seconds / 3600
                logger.debug(f"\n😴 NACHTPAUSE (1:00 - 6:00 Uhr)")
                logger.debug(f"   Schlafe für {sleep_hours:.1f} Stunden")
                logger.debug(f"   Aufwachen um: {wake_time.strftime('%H:%M:%S')}")
                time.sleep(sleep_seconds)
                logger.debug("\n☀️ Guten Morgen! Bot startet wieder...\n")
                continue
            
            driver, status = main_job(cfg)
            
            # Zufällige Wartezeit: 1h 1min bis 1h 20min
            base_seconds = 3600  # 1 Stunde
            random_extra = random.randint(60, 1200)  # 1-20 Minuten
            wait_seconds = base_seconds + random_extra
            
            wait_minutes = wait_seconds // 60
            next_run = datetime.now() + timedelta(seconds=wait_seconds)
            logger.debug(f"\n⏳ Nächster Job in {wait_minutes} Minuten ({wait_minutes // 60}h {wait_minutes % 60}min)")
            logger.debug(f"   Geplante Uhrzeit: {next_run.strftime('%H:%M:%S')}")
            time.sleep(wait_seconds)
            
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n✓ Scheduler gestoppt")


if __name__ == '__main__':
    main()
