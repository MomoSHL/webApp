"""
📋 Player Parser Service
========================
Extrahiert und aggregiert Spielerdaten von der EA WebApp Transferliste.
"""

from collections import Counter
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup

from .bot_logger import get_logger

logger = get_logger(__name__)


def parse_transfer_list_html(html_content: str) -> Dict[str, Any]:
    """
    Parst das HTML der Transferliste und extrahiert alle Spielerkarten mit Details.
    
    Args:
        html_content: HTML-Quelltext der Seite oder des Transferlisten-Containers
        
    Returns:
        Dict mit:
        - 'total_count': Gesamtzahl der Spieler
        - 'unique_count': Anzahl verschiedener Spielertypen (Name + Rating + Position)
        - 'players': Liste aller einzelnen Spielerkarten als Dict
        - 'grouped': Liste der aggregierten Spielergruppen mit Häufigkeit
    """
    if not html_content:
        return {
            'total_count': 0,
            'unique_count': 0,
            'players': [],
            'grouped': []
        }
        
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Finde alle Item-Karten auf der Transferliste
        items = soup.select('li.listFUTItem')
        if not items:
            # Fallback falls li-Elemente andere Klassen haben
            items = soup.select('.itemList li, .ut-sectioned-item-list-view li')
            
        players = []
        for item in items:
            # Spielername: Erstes nicht-leeres Element mit Klasse .name
            # Wichtig: <div class="main-view name"></div> ignorieren
            names = [el.text.strip() for el in item.select('.name') if el.text.strip()]
            name = names[0] if names else 'Unbekannt'
            
            # Rating / Gesamtstärke
            rating_elem = item.select_one('.rating')
            rating = rating_elem.text.strip() if rating_elem else '?'
            
            # Position
            pos_elem = item.select_one('.position')
            position = pos_elem.text.strip() if pos_elem else '?'
            
            # Auktionspreise
            start_price = ''
            buy_now_price = ''
            bid_price = ''
            
            # Startpreis
            start_elem = item.select_one('.auctionStartPrice .value, .auctionStartPrice .currency-coins')
            if start_elem:
                start_price = start_elem.text.strip()
                
            # Alle Auktionswerte durchsuchen
            auction_vals = item.select('.auction .auctionValue')
            for av in auction_vals:
                lbl = av.select_one('.label')
                val = av.select_one('.value, .currency-coins')
                if lbl and val:
                    lbl_txt = lbl.text.lower()
                    if 'start' in lbl_txt and not start_price:
                        start_price = val.text.strip()
                    elif 'buy now' in lbl_txt or 'sofort' in lbl_txt:
                        buy_now_price = val.text.strip()
                    elif 'bid' in lbl_txt or 'gebot' in lbl_txt:
                        bid_price = val.text.strip()
                        
            # Status (z. B. Expired / Abgelaufen)
            time_elem = item.select_one('.auction-state .time')
            if not time_elem:
                time_elem = item.select_one('.auction-state')
                
            status = 'Expired'
            if time_elem:
                status_raw = time_elem.text.strip()
                # Entferne ggf. vorangestelltes 'Time' Label
                if status_raw.startswith('Time'):
                    status_raw = status_raw[4:].strip()
                status = status_raw if status_raw else 'Expired'
            
            players.append({
                'name': name,
                'rating': rating,
                'position': position,
                'start_price': start_price,
                'buy_now_price': buy_now_price,
                'bid_price': bid_price,
                'status': status
            })
            
        # Gruppierung & Aggregation
        group_counts = Counter()
        for p in players:
            key = (p['name'], p['rating'], p['position'])
            group_counts[key] += 1
            
        grouped = []
        # Sortiere nach Häufigkeit absteigend, dann Rating absteigend, dann Name
        for (p_name, p_rating, p_pos), count in group_counts.most_common():
            grouped.append({
                'name': p_name,
                'rating': p_rating,
                'position': p_pos,
                'count': count
            })
            
        return {
            'total_count': len(players),
            'unique_count': len(grouped),
            'players': players,
            'grouped': grouped
        }
        
    except Exception as e:
        logger.error(f"❌ Fehler beim Parsen der Transferliste: {e}", exc_info=True)
        return {
            'total_count': 0,
            'unique_count': 0,
            'players': [],
            'grouped': []
        }
