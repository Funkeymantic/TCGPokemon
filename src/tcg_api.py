"""
Pokemon TCG API Integration Module
Handles all interactions with the Pokemon TCG API
"""

import os
import time
from typing import Optional, List, Dict, Any
from pokemontcgsdk import Card, RestClient
from dotenv import load_dotenv


class TCGAPIClient:
    """Client for interacting with the Pokemon TCG API"""

    def __init__(self):
        """Initialize the API client with optional API key"""
        load_dotenv()
        api_key = os.getenv('POKEMONTCG_IO_API_KEY')

        if api_key:
            RestClient.configure(api_key)
            print("✓ API key configured")
        else:
            print("⚠ No API key found. Using default rate limits.")

    def search_card_by_name(self, card_name: str, set_name: Optional[str] = None, max_retries: int = 3) -> List[Card]:
        """
        Search for cards by name and optionally by set

        Args:
            card_name: Name of the Pokemon card
            set_name: Optional set name to narrow search
            max_retries: Maximum number of retries on timeout (default: 3)

        Returns:
            List of matching Card objects
        """
        query = f'name:"{card_name}"'
        if set_name:
            query += f' set.name:"{set_name}"'

        for attempt in range(max_retries):
            try:
                print(f"Searching API with query: {query} (attempt {attempt + 1}/{max_retries})")
                cards = Card.where(q=query)
                print(f"API returned response, converting to list...")

                # Convert to list to handle SDK response properly
                cards_list = list(cards) if cards else []
                print(f"Found {len(cards_list)} cards")
                return cards_list
            except Exception as e:
                # Better error handling for bytes/string errors
                try:
                    error_msg = str(e)
                except:
                    error_msg = repr(e)

                # Check if it's a timeout or server error
                is_timeout = '504' in error_msg or 'timeout' in error_msg.lower()

                if is_timeout and attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"API timeout. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"Error searching for card: {error_msg}")
                    import traceback
                    traceback.print_exc()
                    return []

        return []

    def search_card_fuzzy(self, card_name: str, max_retries: int = 3) -> List[Card]:
        """
        Fuzzy search for cards (partial name matching)

        Args:
            card_name: Partial or full name of the Pokemon card
            max_retries: Maximum number of retries on timeout (default: 3)

        Returns:
            List of matching Card objects
        """
        query = f'name:{card_name}*'

        for attempt in range(max_retries):
            try:
                print(f"Fuzzy searching API with query: {query} (attempt {attempt + 1}/{max_retries})")
                cards = Card.where(q=query, pageSize=20)
                print(f"API returned response, converting to list...")

                # Convert to list to handle SDK response properly
                cards_list = list(cards) if cards else []
                print(f"Found {len(cards_list)} cards")
                return cards_list
            except Exception as e:
                # Better error handling for bytes/string errors
                try:
                    error_msg = str(e)
                except:
                    error_msg = repr(e)

                # Check if it's a timeout or server error
                is_timeout = '504' in error_msg or 'timeout' in error_msg.lower() or '400' in error_msg

                if is_timeout and attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"API error. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"Error in fuzzy search: {error_msg}")
                    import traceback
                    traceback.print_exc()
                    return []

        return []

    def get_card_by_id(self, card_id: str) -> Optional[Card]:
        """
        Get a specific card by its unique ID

        Args:
            card_id: Unique card identifier (e.g., 'xy1-1')

        Returns:
            Card object or None if not found
        """
        try:
            card = Card.find(card_id)
            return card
        except Exception as e:
            print(f"Error getting card by ID: {e}")
            return None

    def extract_card_info(self, card: Card) -> Dict[str, Any]:
        """
        Extract comprehensive information from a Card object

        Args:
            card: Card object from the API

        Returns:
            Dictionary with all card information
        """
        info = {
            'id': card.id,
            'name': card.name,
            'supertype': card.supertype,
            'subtypes': card.subtypes if hasattr(card, 'subtypes') else [],
            'hp': card.hp if hasattr(card, 'hp') else None,
            'types': card.types if hasattr(card, 'types') else [],
            'evolves_from': card.evolvesFrom if hasattr(card, 'evolvesFrom') else None,
            'abilities': [],
            'attacks': [],
            'weaknesses': [],
            'resistances': [],
            'retreat_cost': card.retreatCost if hasattr(card, 'retreatCost') else [],
            'number': card.number if hasattr(card, 'number') else None,
            'artist': card.artist if hasattr(card, 'artist') else None,
            'rarity': card.rarity if hasattr(card, 'rarity') else None,
            'flavor_text': card.flavorText if hasattr(card, 'flavorText') else None,
            'set': {
                'name': card.set.name if hasattr(card, 'set') else None,
                'series': card.set.series if hasattr(card, 'set') else None,
                'release_date': card.set.releaseDate if hasattr(card, 'set') else None,
            },
            'images': {
                'small': card.images.small if hasattr(card, 'images') else None,
                'large': card.images.large if hasattr(card, 'images') else None,
            },
            'pricing': self._extract_pricing(card),
            'legalities': {},
            'regulation_mark': card.regulationMark if hasattr(card, 'regulationMark') else None,
        }

        # Extract abilities
        if hasattr(card, 'abilities') and card.abilities:
            for ability in card.abilities:
                info['abilities'].append({
                    'name': ability.name,
                    'text': ability.text,
                    'type': ability.type,
                })

        # Extract attacks
        if hasattr(card, 'attacks') and card.attacks:
            for attack in card.attacks:
                info['attacks'].append({
                    'name': attack.name,
                    'cost': attack.cost if hasattr(attack, 'cost') else [],
                    'damage': attack.damage if hasattr(attack, 'damage') else None,
                    'text': attack.text if hasattr(attack, 'text') else None,
                })

        # Extract weaknesses
        if hasattr(card, 'weaknesses') and card.weaknesses:
            for weakness in card.weaknesses:
                info['weaknesses'].append({
                    'type': weakness.type,
                    'value': weakness.value,
                })

        # Extract resistances
        if hasattr(card, 'resistances') and card.resistances:
            for resistance in card.resistances:
                info['resistances'].append({
                    'type': resistance.type,
                    'value': resistance.value,
                })

        # Extract legalities
        if hasattr(card, 'legalities'):
            info['legalities'] = {
                'standard': card.legalities.standard if hasattr(card.legalities, 'standard') else None,
                'expanded': card.legalities.expanded if hasattr(card.legalities, 'expanded') else None,
                'unlimited': card.legalities.unlimited if hasattr(card.legalities, 'unlimited') else None,
            }

        return info

    def _extract_pricing(self, card: Card) -> Dict[str, Any]:
        """
        Extract pricing information from a card

        Args:
            card: Card object from the API

        Returns:
            Dictionary with pricing information
        """
        pricing = {
            'tcgplayer': {},
            'cardmarket': {},
        }

        # TCGPlayer pricing (USD)
        if hasattr(card, 'tcgplayer') and card.tcgplayer:
            tcg = card.tcgplayer
            pricing['tcgplayer'] = {
                'url': tcg.url if hasattr(tcg, 'url') else None,
                'updated_at': tcg.updatedAt if hasattr(tcg, 'updatedAt') else None,
                'prices': {}
            }

            if hasattr(tcg, 'prices') and tcg.prices:
                if hasattr(tcg.prices, 'normal'):
                    pricing['tcgplayer']['prices']['normal'] = {
                        'low': tcg.prices.normal.low if hasattr(tcg.prices.normal, 'low') else None,
                        'mid': tcg.prices.normal.mid if hasattr(tcg.prices.normal, 'mid') else None,
                        'high': tcg.prices.normal.high if hasattr(tcg.prices.normal, 'high') else None,
                        'market': tcg.prices.normal.market if hasattr(tcg.prices.normal, 'market') else None,
                    }
                if hasattr(tcg.prices, 'holofoil'):
                    pricing['tcgplayer']['prices']['holofoil'] = {
                        'low': tcg.prices.holofoil.low if hasattr(tcg.prices.holofoil, 'low') else None,
                        'mid': tcg.prices.holofoil.mid if hasattr(tcg.prices.holofoil, 'mid') else None,
                        'high': tcg.prices.holofoil.high if hasattr(tcg.prices.holofoil, 'high') else None,
                        'market': tcg.prices.holofoil.market if hasattr(tcg.prices.holofoil, 'market') else None,
                    }

        # Cardmarket pricing (EUR)
        if hasattr(card, 'cardmarket') and card.cardmarket:
            cm = card.cardmarket
            pricing['cardmarket'] = {
                'url': cm.url if hasattr(cm, 'url') else None,
                'updated_at': cm.updatedAt if hasattr(cm, 'updatedAt') else None,
                'prices': {}
            }

            if hasattr(cm, 'prices'):
                pricing['cardmarket']['prices'] = {
                    'average_sell_price': cm.prices.averageSellPrice if hasattr(cm.prices, 'averageSellPrice') else None,
                    'low_price': cm.prices.lowPrice if hasattr(cm.prices, 'lowPrice') else None,
                    'trend_price': cm.prices.trendPrice if hasattr(cm.prices, 'trendPrice') else None,
                    'german_pro_low': cm.prices.germanProLow if hasattr(cm.prices, 'germanProLow') else None,
                    'suggested_price': cm.prices.suggestedPrice if hasattr(cm.prices, 'suggestedPrice') else None,
                }

        return pricing
