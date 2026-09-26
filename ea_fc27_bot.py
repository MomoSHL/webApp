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
                    time.sleep(random.uniform(0.5, 1.0))
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
        with open(filepath, "wb") as f:
            pickle.dump(driver.get_cookies(), f)
        logger.info("✅ Cookies gespeichert: {filepath.name}")
        return True
    except Exception as e:
        logger.warning("⚠️ Cookie-Speicherung fehlgeschlagen: {e}")
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
# BROWSER INITIALIZATION
# ============================================================================

def get_platform_user_agent():
    """
    Gibt einen realistischen User-Agent für das aktuelle Betriebssystem zurück.
    """
    system = platform.system()
    
    if system == "Linux":
        return "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    elif system == "Darwin":  # macOS
        return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    else:  # Windows als Fallback
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def init_browser(headless: bool = True) -> uc.Chrome:
    """Initialisiert undetected-chromedriver mit erweiterten Anti-Detection Features."""
    options = uc.ChromeOptions()
    
    # Anti-Detection (Basis)
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    
    # Linux-spezifisch: Deaktiviere GPU falls Probleme
    if platform.system() == "Linux":
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
    
    # WebRTC Leak Prevention (wichtig!)
    options.add_argument("--disable-webrtc")
    options.add_argument("--disable-webrtc-hw-encoding")
    
    # Plattform-spezifischer User-Agent
    user_agent = get_platform_user_agent()
    options.add_argument(f"--user-agent={user_agent}")
    logger.info(f"   🖥️  OS: {platform.system()} ({platform.release()})")
    
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
    
    # Setze Timezone & Locale via CDP
    try:
        driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": "Europe/Berlin"})
        driver.execute_cdp_cmd("Emulation.setLocaleOverride", {"locale": "de-DE"})
    except:
        pass  # Ignoriere falls nicht unterstützt
    
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


def check_already_logged_in_elsewhere(driver):
    """
    Prüft ob User bereits auf anderem Gerät (z.B. PlayStation) angemeldet ist.
    Returns: True wenn "bereits angemeldet" Meldung erscheint
    """
    try:
        # Suche nach typischen "bereits angemeldet" Meldungen
        error_texts = [
            "already logged in",
            "bereits angemeldet",
            "logged in on another device",
            "auf einem anderen gerät",
            "another device",
            "anderes gerät",
            "sign out on other device",
            "auf einem anderen Gerät angemeldet",
        ]
        
        page_text = driver.page_source.lower()
        
        for error_text in error_texts:
            if error_text in page_text:
                logger.warning("⚠️ Erkannt: Bereits auf anderem Gerät angemeldet ('{error_text}')")
                return True
        
        # Suche nach spezifischen Error-Containern
        error_selectors = [
            "div.ut-error-view",
            "div.error-message",
            "div.notification",
            "//div[contains(@class, 'error')]",
            "//div[contains(@class, 'notification')]",
        ]
        
        for selector in error_selectors:
            try:
                if selector.startswith("//"):
                    error_elem = driver.find_element(By.XPATH, selector)
                else:
                    error_elem = driver.find_element(By.CSS_SELECTOR, selector)
                
                error_text = error_elem.text.lower()
                if any(err in error_text for err in ["already", "bereits", "other device", "anderes gerät"]):
                    logger.warning("⚠️ Error-Element gefunden: {error_text[:100]}")
                    return True
            except:
                continue
        
        return False
        
    except Exception as e:
        logger.debug("🔍 Debug: check_already_logged_in_elsewhere Fehler: {e}")
        return False


def login_via_ui(driver, cfg):
    """
    Login über UI mit Cookie-Persistenz und 2FA-Unterstützung.
    Returns: True wenn erfolgreich, False wenn Fehler, None wenn "bereits angemeldet"
    """
    username = cfg['username']
    wait = WebDriverWait(driver, 20)
    
    # Versuche Cookies zu laden
    driver.get(cfg['login_url'])
    human_like_delay(2, 3)
    
    # Zufälliges Verhalten nach Page-Load (wichtig!)
    random_mouse_movements(driver, num_movements=3)
    human_like_delay(1, 3)  # User schaut sich Seite an
    
    # Prüfe ob bereits auf anderem Gerät angemeldet
    if check_already_logged_in_elsewhere(driver):
        logger.warning("⚠️ WebApp nicht verfügbar: Bereits auf anderem Gerät angemeldet")
        return None  # Spezieller Rückgabewert für "bereits angemeldet"
    
    if load_cookies(driver, username):
        driver.refresh()
        human_like_delay(3, 5)
        
        # Prüfe ob bereits eingeloggt
        try:
            driver.find_element(By.CSS_SELECTOR, "button.ut-tab-bar-item.icon-transfer")
            logger.info("✅ Bereits eingeloggt via Cookies!")
            return True
        except NoSuchElementException:
            logger.warning("⚠️ Cookies ungültig, führe Login durch")
    
    selectors = cfg['ui_selectors']
    from selenium.webdriver.common.keys import Keys
    
    # Cookie-Consent Banner prüfen und akzeptieren (falls vorhanden)
    try:
        cookie_banners = driver.find_elements(
            By.CSS_SELECTOR, 
            "#onetrust-accept-btn-handler, button#onetrust-accept-btn-handler, #btn-accept-all, button.cookie-accept-all"
        )
        for cb in cookie_banners:
            if cb.is_displayed():
                cb.click()
                logger.info("✅ Cookie-Banner akzeptiert")
                human_like_delay(1, 2)
                break
    except Exception:
        pass
        
    # Klicke primären Login-Button auf der WebApp-Startseite
    primary_selectors = [
        selectors.get('primary_login_button', 'button.btn-standard.primary'),
        "button.btn-standard.primary",
        "button.ut-login-button",
        "//button[contains(@class, 'btn-standard') and (contains(., 'Login') or contains(., 'Anmelden') or contains(@class, 'primary'))]",
        "//button[contains(., 'Login') or contains(., 'Anmelden')]"
    ]
    
    login_btn = None
    for sel in primary_selectors:
        try:
            if sel.startswith("//"):
                login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, sel)))
            else:
                login_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            if login_btn:
                break
        except Exception:
            continue
            
    if login_btn:
        human_like_delay(0.5, 1.2)
        try:
            login_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", login_btn)
        logger.info("✅ Login-Button geklickt")
        human_like_delay(2, 4)
    else:
        logger.warning("⚠️ Primärer Login-Button nicht gefunden (möglicherweise bereits auf Login-Seite oder Seite lädt noch)")
    
    # Warte bis Login-Formular (signin.ea.com) geladen ist
    logger.info("⏳ Warte auf EA Anmeldeseite...")
    email_field = None
    email_selectors = [
        "input[name='email']",
        "input#email",
        "input[type='email']",
        selectors.get('username', "input[name='email']")
    ]
    for sel in email_selectors:
        try:
            email_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            if email_field:
                break
        except Exception:
            continue
            
    if not email_field:
        logger.error("❌ Email-Eingabefeld nicht gefunden!")
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
        next_btn = None
        next_selectors = [
            "a#logInBtn",
            "button#logInBtn",
            "#logInBtn",
            selectors.get('next_button', 'a#logInBtn'),
            "button[type='submit']"
        ]
        for sel in next_selectors:
            try:
                candidate = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                if candidate.is_displayed():
                    next_btn = candidate
                    break
            except Exception:
                continue
                
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
    pwd_field = None
    pwd_selectors = [
        "input[name='password']",
        "input#password",
        "input[type='password']",
        selectors.get('password', "input[name='password']")
    ]
    for sel in pwd_selectors:
        try:
            pwd_field = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, sel)))
            if pwd_field:
                break
        except Exception:
            continue
            
    if not pwd_field:
        logger.error("❌ Passwort-Feld nicht sichtbar geworden!")
        return False

    try:
        wait.until(EC.element_to_be_clickable(pwd_field))
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
        sign_btn = None
        sign_selectors = [
            "a#logInBtn",
            "button#logInBtn",
            "#logInBtn",
            selectors.get('sign_in_button', 'a#logInBtn'),
            "button[type='submit']"
        ]
        for sel in sign_selectors:
            try:
                candidate = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                if candidate.is_displayed():
                    sign_btn = candidate
                    break
            except Exception:
                continue
                
        if sign_btn:
            human_like_delay(0.4, 0.8)
            sign_btn.click()
        else:
            pwd_field.send_keys(Keys.RETURN)
            
        logger.info("✅ 'Sign In' geklickt")
    except Exception as e:
        logger.error(f"❌ Sign In fehlgeschlagen: {e}")
        return False
    
    human_like_delay(3, 5)
    
    # Prüfe auf Login-Fehlermeldungen auf der Seite
    for err in driver.find_elements(By.CSS_SELECTOR, ".origin-ux-element-error-message, .error, .banner-message, .otkform-error"):
        if err.is_displayed() and err.text.strip():
            logger.error(f"❌ EA-Login-Fehler: {err.text.strip()}")
            return False
            
    # 2FA behandeln
    if not handle_2fa(driver, wait):
        logger.error("❌ 2FA fehlgeschlagen")
        return False
    
    # Warte bis WebApp wieder geladen ist
    logger.info("⏳ Warte auf Weiterleitung zur WebApp...")
    try:
        WebDriverWait(driver, 30).until(
            lambda d: "ea.com" in d.current_url and ("fut" in d.current_url.lower() or "ultimate-team" in d.current_url.lower())
        )
        human_like_delay(3, 5)
    except Exception:
        pass
    
    # Cookies speichern
    save_cookies(driver, username)
    
    logger.info("✅ Login erfolgreich!\n")
    return True


# ============================================================================
# TRANSFER LIST NAVIGATION
# ============================================================================

def navigate_to_transfer_list(driver, cfg):
    """
    Navigiert zur Transfer-Liste.
    Returns: True wenn erfolgreich
    """
    wait = WebDriverWait(driver, 15)
    selectors = cfg.get('ui_selectors', {})
    
    # 1. Prüfe ob wir bereits auf der Transfer-Liste sind
    try:
        already_on_list = driver.find_elements(
            By.XPATH, 
            "//button[contains(@class, 'section-header-btn') and (contains(., 'Re-list') or contains(., 're-list') or contains(., 'Erneut') or contains(., 'neu'))] | //button[contains(., 'Re-list All')]"
        )
        if already_on_list and any(b.is_displayed() for b in already_on_list):
            logger.info("✅ Bereits auf der Transfer-Liste (Re-List Button sichtbar)")
            return True
    except Exception:
        pass

    try:
        # Natürliches Verhalten: User schaut sich erst um
        random_scroll_behavior(driver)
        human_like_delay(1, 2)
        
        # 2. Transfer-Tab finden und öffnen
        tab_selectors = [
            selectors.get('transfer_tab', 'button.ut-tab-bar-item.icon-transfer'),
            "button.ut-tab-bar-item.icon-transfer",
            "button.icon-transfer",
            "//button[contains(@class, 'icon-transfer')]",
            "//button[contains(@class, 'ut-tab-bar-item') and contains(., 'Transfers')]",
            "//button[contains(., 'Transfers')]"
        ]
        
        transfer_tab = None
        for sel in tab_selectors:
            try:
                if sel.startswith("//"):
                    transfer_tab = wait.until(EC.element_to_be_clickable((By.XPATH, sel)))
                else:
                    transfer_tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                if transfer_tab:
                    break
            except Exception:
                continue
                
        if not transfer_tab:
            logger.error("❌ Transfer-Tab nicht gefunden")
            return False
            
        random_mouse_movements(driver, num_movements=2)
        human_like_delay(0.5, 1.2)
        
        try:
            transfer_tab.click()
        except Exception:
            driver.execute_script("arguments[0].click();", transfer_tab)
            
        logger.info("✅ Transfer-Tab geöffnet")
        human_like_delay(1.5, 2.5)
        
        # 3. Transfer-Liste Tile finden und öffnen
        tile_selectors = [
            selectors.get('transfer_tile', '.tile.col-1-2.ut-tile-transfer-list.ut-tile-transfers'),
            ".tile.col-1-2.ut-tile-transfer-list.ut-tile-transfers",
            ".ut-tile-transfer-list",
            "//div[contains(@class, 'ut-tile-transfer-list')]",
            "//div[contains(@class, 'tile') and (contains(., 'Transfer List') or contains(., 'Transferliste'))]"
        ]
        
        transfer_tile = None
        for sel in tile_selectors:
            try:
                if sel.startswith("//"):
                    transfer_tile = wait.until(EC.element_to_be_clickable((By.XPATH, sel)))
                else:
                    transfer_tile = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                if transfer_tile:
                    break
            except Exception:
                continue
                
        if not transfer_tile:
            logger.error("❌ Transfer-Liste Tile nicht gefunden")
            return False
            
        human_like_delay(0.5, 1.0)
        try:
            transfer_tile.click()
        except Exception:
            driver.execute_script("arguments[0].click();", transfer_tile)
            
        logger.info("✅ Transfer-Liste geöffnet")
        human_like_delay(2, 3)
        
        # Simuliere Tab-Wechsel (manchmal)
        simulate_tab_switch(driver)
        
        return True
        
    except (TimeoutException, NoSuchElementException) as e:
        logger.error(f"❌ Transfer-Navigation fehlgeschlagen: {e}")
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
    wait = WebDriverWait(driver, 10)
    
    print("\n" + "="*60)
    logger.info("RE-LIST: Alle Transfer-Spieler neu anbieten")
    logger.info("="*60 + "\n")
    
    # 1. Navigiere zur Transfer-Liste
    if not navigate_to_transfer_list(driver, cfg):
        logger.error("❌ Konnte nicht zur Transfer-Liste navigieren")
        return -1
    
    try:
        # Warte kurz bis Items & Header geladen sind
        human_like_delay(2, 3)
        
        # Natürliches Verhalten: Leichter Scroll
        random_scroll_behavior(driver)
        human_like_delay(1, 1.5)
        
        # 2. Ermittle Anzahl & Namen abgelaufener Items (informativ, blockiert niemals)
        item_count = 0
        try:
            # Suche Header wie "Unsold Items (4)" oder "Nicht verkaufte Objekte (4)"
            headers = driver.find_elements(
                By.XPATH, 
                "//header[contains(., 'Unsold') or contains(., 'Nicht verkauft') or contains(., 'Abgelaufen')] | //h2[contains(., 'Unsold') or contains(., 'Nicht verkauft') or contains(., 'Abgelaufen')]"
            )
            for h in headers:
                match = re.search(r'\((\d+)\)', h.text)
                if match:
                    item_count = int(match.group(1))
                    break
        except Exception:
            pass
        
        player_names = []
        try:
            # Versuche Spielernamen aus den Karten zu lesen falls gerendert
            card_names = driver.find_elements(
                By.CSS_SELECTOR, 
                "div.rowContent .name, li.listFUTItem .name, .ut-pinned-list-container .name, div.name"
            )
            for cn in card_names:
                t = cn.text.strip()
                if t and t not in player_names:
                    player_names.append(t)
        except Exception:
            pass
            
        if player_names:
            logger.info(f"📋 {len(player_names)} Spieler auf der Transferliste erkannt:")
            for name in player_names:
                logger.info(f"   • {name}")
        elif item_count > 0:
            logger.info(f"📋 {item_count} abgelaufene Items in der Liste erkannt")
        else:
            logger.info("📋 Suche nach 'Re-list All' Button...")
            
        # 3. Finde den "Re-list All" Button
        # Vom User bereitgestelltes HTML: <button class="btn-standard section-header-btn mini primary hover" style="">Re-list All</button>
        relist_button = None
        
        # Strategie A: Spezifische Text- & Klassen-XPaths
        relist_xpaths = [
            "//button[contains(@class, 'section-header-btn') and (contains(., 'Re-list') or contains(., 're-list') or contains(., 'Erneut') or contains(., 'neu anbieten'))]",
            "//button[contains(., 'Re-list All') or contains(., 're-list all') or contains(., 'RE-LIST ALL')]",
            "//button[contains(., 'Erneut anbieten') or contains(., 'neu anbieten') or contains(., 'Neu anbieten')]",
            "//button[contains(@class, 'section-header-btn') and contains(@class, 'primary')]",
        ]
        
        for xpath in relist_xpaths:
            try:
                candidates = driver.find_elements(By.XPATH, xpath)
                for btn in candidates:
                    btn_text = btn.text.strip().lower()
                    if 'clear' in btn_text or 'löschen' in btn_text:
                        continue
                    relist_button = btn
                    logger.info(f"   ✓ 'Re-list All' Button gefunden via XPath: '{btn.text.strip()}'")
                    break
                if relist_button:
                    break
            except Exception:
                continue
                
        # Strategie B: CSS Selektoren (exakter Match mit Button-Klassen)
        if not relist_button:
            relist_css = [
                "button.btn-standard.section-header-btn.mini.primary",
                "button.section-header-btn.mini.primary",
                "button.btn-standard.section-header-btn",
                "button.section-header-btn.primary",
                "button.section-header-btn",
            ]
            for css in relist_css:
                try:
                    candidates = driver.find_elements(By.CSS_SELECTOR, css)
                    for btn in candidates:
                        btn_text = btn.text.strip().lower()
                        if 'clear' in btn_text or 'löschen' in btn_text:
                            continue
                        relist_button = btn
                        logger.info(f"   ✓ 'Re-list All' Button gefunden via CSS ({css}): '{btn.text.strip()}'")
                        break
                    if relist_button:
                        break
                except Exception:
                    continue
                    
        # Falls kein Button gefunden wurde:
        if not relist_button:
            if item_count == 0 and not player_names:
                logger.info("ℹ️ Kein 'Re-list All' Button vorhanden (keine abgelaufenen Items auf der Transferliste)")
                return 0
            else:
                logger.warning("⚠️ 'Re-list All' Button konnte nicht gefunden werden!")
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
                return 0
        except Exception:
            pass

        # 4. Klicke "Re-list All" Button mit 3-Stufen Fallback
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
                driver.execute_script("arguments[0].click();", relist_button)
                clicked = True
            except Exception as e:
                logger.error(f"❌ Klick auf 'Re-list All' fehlgeschlagen: {e}")
                return -1
                
        logger.info("✅ 'Re-list All' Button erfolgreich geklickt")
        
        # 5. Warte auf Bestätigungsdialog ("Yes" / "Ja")
        logger.info("⏳ Warte auf Bestätigungsdialog ('Yes' / 'Ja')...")
        human_like_delay(1.5, 2.5)
        
        confirm_btn = None
        confirm_selectors = [
            "//div[contains(@class, 'ea-dialog-view') or contains(@class, 'view-modal') or contains(@class, 'dialog') or contains(@class, 'ut-button-group')]//button[contains(., 'Yes') or contains(., 'Ja') or contains(@class, 'primary')]",
            "//button[contains(@class, 'btn-standard') and (contains(., 'Yes') or contains(., 'Ja') or contains(., 'YES') or contains(., 'JA'))]",
            "//button[normalize-space(text())='Yes' or normalize-space(text())='Ja']",
            "//button[contains(., 'Yes') or contains(., 'Ja')]",
            ".view-modal-container button.primary",
            ".ut-button-group button.btn-standard.primary",
            ".ut-button-group button.primary",
            "button.btn-standard.primary",
        ]
        
        for sel in confirm_selectors:
            try:
                if sel.startswith("//"):
                    elements = driver.find_elements(By.XPATH, sel)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, sel)
                    
                for el in elements:
                    txt = el.text.strip().lower()
                    # Schließe Ablehnung / Cancel aus
                    if any(neg in txt for neg in ['cancel', 'abbrechen', 'nein']) or (txt == 'no'):
                        continue
                    if el.is_displayed() or el.is_enabled():
                        confirm_btn = el
                        logger.info(f"   ✓ Bestätigungs-Button gefunden: '{el.text.strip()}'")
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
                    driver.execute_script("arguments[0].click();", confirm_btn)
                    confirm_clicked = True
                except Exception:
                    pass
                    
            if confirm_clicked:
                logger.info("✅ Bestätigung ('Yes' / 'Ja') erfolgreich geklickt")
            else:
                logger.warning("⚠️ Konnte Bestätigungs-Button nicht klicken")
        else:
            logger.info("ℹ️ Kein Bestätigungsdialog erschienen (Re-List direkt ausgeführt)")
            
        # 6. Warte auf Abschluss der Server-Aktion
        logger.info("⏳ Warte auf Abschluss der Re-List Aktion...")
        human_like_delay(3, 5)
        
        count = len(player_names) if player_names else (item_count if item_count > 0 else 1)
        
        print("\n" + "="*60)
        logger.info(f"✅ ERFOLGREICH NEU ANGEBOTEN: {count} Spieler")
        print("="*60)
        if player_names:
            for idx, name in enumerate(player_names, 1):
                logger.info(f"   {idx}. {name}")
        print("="*60 + "\n")
        
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
            # Bereits auf anderem Gerät angemeldet
            print("\n" + "="*60)
            logger.warning("⚠️ BEREITS AUF ANDEREM GERÄT ANGEMELDET")
            print("="*60)
            logger.debug("WebApp ist nicht verfügbar (z.B. PlayStation aktiv)")
            logger.debug("Warte 15 Minuten und versuche es erneut...")
            logger.debug("="*60 + "\n")
            
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
                
                if status == 'already_logged_in':
                    # Warte 15 Minuten
                    logger.debug(f"⏳ Warte {retry_delay // 60} Minuten bis zum nächsten Versuch...")
                    
                    # Wechsle zu Idle-Tab während Wartezeit
                    if shared_driver:
                        switch_to_idle_tab(shared_driver)
                    
                    time.sleep(retry_delay)
                    continue
                
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
    
    retry_delay = 15 * 60  # 15 Minuten
    
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
            
            if status == 'already_logged_in':
                # Warte 15 Minuten
                logger.debug(f"⏳ Warte {retry_delay // 60} Minuten bis zum nächsten Versuch...")
                time.sleep(retry_delay)
                continue
            
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
