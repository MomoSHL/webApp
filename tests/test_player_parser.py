"""
Unit Tests für Player Parser Service
=====================================
Testet die Erkennung, Extraktion und Gruppierung von Spielern auf der Transferliste.
"""

import unittest
from pathlib import Path
import sys

# Root zum Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.player_parser import parse_transfer_list_html


class TestPlayerParser(unittest.TestCase):
    """Test-Suite für den Player-Parser."""
    
    @classmethod
    def setUpClass(cls):
        html_path = Path(__file__).parent.parent / "player_list.html"
        with open(html_path, "r", encoding="utf-8") as f:
            cls.sample_html = f.read()
            
    def test_parse_player_list_html(self):
        """Prüft die Extraktion aller 37 Spieler aus player_list.html."""
        result = parse_transfer_list_html(self.sample_html)
        
        # 1. Gesamtzahlen prüfen
        self.assertEqual(result['total_count'], 37)
        self.assertEqual(result['unique_count'], 9)
        self.assertEqual(len(result['players']), 37)
        self.assertEqual(len(result['grouped']), 9)
        
        # 2. Gruppierte Verteilung prüfen
        group_dict = {g['name']: g['count'] for g in result['grouped']}
        expected_counts = {
            'Tah': 9,
            'Roord': 8,
            'Rice': 6,
            'Kimmich': 4,
            'Berger': 3,
            'Hasegawa': 2,
            'Hampton': 2,
            'Hemp': 2,
            'Harder': 1
        }
        self.assertEqual(group_dict, expected_counts)
        
        # 3. Erste Spielerkarte im Detail prüfen (Hasegawa)
        first_player = result['players'][0]
        self.assertEqual(first_player['name'], 'Hasegawa')
        self.assertEqual(first_player['rating'], '88')
        self.assertEqual(first_player['position'], 'CDM')
        self.assertEqual(first_player['start_price'], '21,750')
        self.assertEqual(first_player['buy_now_price'], '30,000')
        self.assertEqual(first_player['status'], 'Expired')
        
        # 4. GK Karte prüfen (Hampton)
        hampton_cards = [p for p in result['players'] if p['name'] == 'Hampton']
        self.assertEqual(len(hampton_cards), 2)
        self.assertEqual(hampton_cards[0]['rating'], '87')
        self.assertEqual(hampton_cards[0]['position'], 'GK')
        
    def test_empty_and_invalid_html(self):
        """Prüft das Verhalten bei leerem oder fehlerhaftem HTML."""
        empty_res = parse_transfer_list_html("")
        self.assertEqual(empty_res['total_count'], 0)
        self.assertEqual(empty_res['unique_count'], 0)
        self.assertEqual(empty_res['players'], [])
        self.assertEqual(empty_res['grouped'], [])
        
        invalid_res = parse_transfer_list_html("<div>Keine Transferliste</div>")
        self.assertEqual(invalid_res['total_count'], 0)
        self.assertEqual(invalid_res['unique_count'], 0)

    def test_active_and_sold_items_ignored(self):
        """Prüft dass aktive und bereits verkaufte Karten nicht als abgelaufen gezählt werden."""
        active_html = """
        <section class="ut-sectioned-item-list-view">
            <header class="ut-section-header-view"><h2 class="title">Available Items</h2></header>
            <ul class="itemList">
                <li class="listFUTItem has-auction-data">
                    <div class="name">Mbappe</div>
                    <div class="rating">91</div>
                    <div class="position">ST</div>
                    <div class="auction-state"><span class="time">59m 30s</span></div>
                </li>
            </ul>
        </section>
        <section class="ut-sectioned-item-list-view">
            <header class="ut-section-header-view"><h2 class="title">Sold Items</h2><button class="btn-standard section-header-btn mini primary">Clear Sold</button></header>
            <ul class="itemList">
                <li class="listFUTItem has-auction-data won">
                    <div class="name">Haaland</div>
                    <div class="rating">91</div>
                    <div class="position">ST</div>
                </li>
            </ul>
        </section>
        """
        res = parse_transfer_list_html(active_html)
        self.assertEqual(res['total_count'], 0)
        self.assertEqual(res['players'], [])


if __name__ == '__main__':
    unittest.main()
