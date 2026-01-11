"""
File Manager Module
Handles saving Pokemon card information to files
"""

import json
import os
from datetime import datetime
from typing import Dict, Any
import requests


class FileManager:
    """Manages saving card data to files"""

    def __init__(self, base_dir: str = "card_data"):
        """
        Initialize file manager

        Args:
            base_dir: Base directory for saving card data
        """
        self.base_dir = base_dir
        self._ensure_directory_exists(base_dir)

    def _ensure_directory_exists(self, directory: str):
        """
        Ensure a directory exists, create if it doesn't

        Args:
            directory: Directory path
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created directory: {directory}")

    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize a string to be used as a filename

        Args:
            name: Original name

        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        sanitized = name.replace(' ', '_')
        sanitized = ''.join(c for c in sanitized if c.isalnum() or c in ['_', '-'])
        return sanitized[:100]  # Limit length

    def save_card_data(self, card_info: Dict[str, Any], card_name: str) -> str:
        """
        Save complete card data to a JSON file

        Args:
            card_info: Dictionary with card information
            card_name: Name of the card (used for filename)

        Returns:
            Path to saved file
        """
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self._sanitize_filename(card_name)
        filename = f"{safe_name}_{timestamp}.json"
        filepath = os.path.join(self.base_dir, filename)

        # Add metadata
        card_info['_metadata'] = {
            'saved_at': datetime.now().isoformat(),
            'version': '1.0'
        }

        # Save to JSON file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(card_info, f, indent=2, ensure_ascii=False)
            print(f"✓ Card data saved to: {filepath}")
            return filepath
        except Exception as e:
            print(f"Error saving card data: {e}")
            return ""

    def save_basic_info(self, card_info: Dict[str, Any], card_name: str) -> str:
        """
        Save basic card information to a text file

        Args:
            card_info: Dictionary with card information
            card_name: Name of the card

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self._sanitize_filename(card_name)
        filename = f"{safe_name}_info_{timestamp}.txt"
        filepath = os.path.join(self.base_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Pokemon Card Information\n")
                f.write(f"=" * 50 + "\n\n")
                f.write(f"Card Name: {card_info.get('name', 'N/A')}\n")
                f.write(f"ID: {card_info.get('id', 'N/A')}\n")
                f.write(f"Supertype: {card_info.get('supertype', 'N/A')}\n")
                f.write(f"HP: {card_info.get('hp', 'N/A')}\n")
                f.write(f"Types: {', '.join(card_info.get('types', []))}\n")
                f.write(f"Rarity: {card_info.get('rarity', 'N/A')}\n")
                f.write(f"Set: {card_info.get('set', {}).get('name', 'N/A')}\n")
                f.write(f"Card Number: {card_info.get('number', 'N/A')}\n")
                f.write(f"Artist: {card_info.get('artist', 'N/A')}\n\n")

                # Abilities
                if card_info.get('abilities'):
                    f.write(f"Abilities:\n")
                    for ability in card_info['abilities']:
                        f.write(f"  - {ability['name']} ({ability['type']})\n")
                        f.write(f"    {ability['text']}\n")
                    f.write("\n")

                # Attacks
                if card_info.get('attacks'):
                    f.write(f"Attacks:\n")
                    for attack in card_info['attacks']:
                        f.write(f"  - {attack['name']}\n")
                        f.write(f"    Cost: {', '.join(attack.get('cost', []))}\n")
                        f.write(f"    Damage: {attack.get('damage', 'N/A')}\n")
                        if attack.get('text'):
                            f.write(f"    Effect: {attack['text']}\n")
                    f.write("\n")

                # Weaknesses and Resistances
                if card_info.get('weaknesses'):
                    f.write(f"Weaknesses: ")
                    f.write(", ".join([f"{w['type']} {w['value']}" for w in card_info['weaknesses']]))
                    f.write("\n")

                if card_info.get('resistances'):
                    f.write(f"Resistances: ")
                    f.write(", ".join([f"{r['type']} {r['value']}" for r in card_info['resistances']]))
                    f.write("\n")

                f.write(f"\nRetreat Cost: {len(card_info.get('retreat_cost', []))} energy\n")

            print(f"✓ Basic info saved to: {filepath}")
            return filepath
        except Exception as e:
            print(f"Error saving basic info: {e}")
            return ""

    def save_pricing_info(self, card_info: Dict[str, Any], card_name: str) -> str:
        """
        Save pricing information to a separate file

        Args:
            card_info: Dictionary with card information
            card_name: Name of the card

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self._sanitize_filename(card_name)
        filename = f"{safe_name}_pricing_{timestamp}.txt"
        filepath = os.path.join(self.base_dir, filename)

        pricing = card_info.get('pricing', {})

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Pokemon Card Pricing Information\n")
                f.write(f"=" * 50 + "\n\n")
                f.write(f"Card: {card_info.get('name', 'N/A')}\n")
                f.write(f"Set: {card_info.get('set', {}).get('name', 'N/A')}\n")
                f.write(f"Rarity: {card_info.get('rarity', 'N/A')}\n\n")

                # TCGPlayer pricing (USD)
                tcg = pricing.get('tcgplayer', {})
                if tcg and tcg.get('prices'):
                    f.write(f"TCGPlayer Prices (USD):\n")
                    f.write(f"-" * 40 + "\n")

                    if 'normal' in tcg['prices']:
                        normal = tcg['prices']['normal']
                        f.write(f"  Normal:\n")
                        f.write(f"    Low: ${normal.get('low', 'N/A')}\n")
                        f.write(f"    Mid: ${normal.get('mid', 'N/A')}\n")
                        f.write(f"    High: ${normal.get('high', 'N/A')}\n")
                        f.write(f"    Market: ${normal.get('market', 'N/A')}\n")

                    if 'holofoil' in tcg['prices']:
                        holo = tcg['prices']['holofoil']
                        f.write(f"  Holofoil:\n")
                        f.write(f"    Low: ${holo.get('low', 'N/A')}\n")
                        f.write(f"    Mid: ${holo.get('mid', 'N/A')}\n")
                        f.write(f"    High: ${holo.get('high', 'N/A')}\n")
                        f.write(f"    Market: ${holo.get('market', 'N/A')}\n")

                    if tcg.get('url'):
                        f.write(f"\n  TCGPlayer URL: {tcg['url']}\n")

                    f.write("\n")

                # Cardmarket pricing (EUR)
                cm = pricing.get('cardmarket', {})
                if cm and cm.get('prices'):
                    f.write(f"Cardmarket Prices (EUR):\n")
                    f.write(f"-" * 40 + "\n")
                    prices = cm['prices']
                    f.write(f"  Average Sell: €{prices.get('average_sell_price', 'N/A')}\n")
                    f.write(f"  Low Price: €{prices.get('low_price', 'N/A')}\n")
                    f.write(f"  Trend Price: €{prices.get('trend_price', 'N/A')}\n")
                    f.write(f"  Suggested Price: €{prices.get('suggested_price', 'N/A')}\n")

                    if cm.get('url'):
                        f.write(f"\n  Cardmarket URL: {cm['url']}\n")

                f.write(f"\nPricing retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            print(f"✓ Pricing info saved to: {filepath}")
            return filepath
        except Exception as e:
            print(f"Error saving pricing info: {e}")
            return ""

    def save_card_image(self, image_url: str, card_name: str, image_type: str = "large") -> str:
        """
        Download and save card image from URL

        Args:
            image_url: URL of the card image
            card_name: Name of the card
            image_type: Type of image (small/large)

        Returns:
            Path to saved image file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self._sanitize_filename(card_name)
        filename = f"{safe_name}_{image_type}_{timestamp}.png"
        filepath = os.path.join(self.base_dir, filename)

        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

            print(f"✓ Card image saved to: {filepath}")
            return filepath
        except Exception as e:
            print(f"Error saving card image: {e}")
            return ""

    def save_all_card_info(self, card_info: Dict[str, Any]) -> Dict[str, str]:
        """
        Save all card information in separate files

        Args:
            card_info: Complete card information dictionary

        Returns:
            Dictionary with paths to all saved files
        """
        card_name = card_info.get('name', 'unknown_card')
        saved_files = {}

        # Save complete JSON
        saved_files['json'] = self.save_card_data(card_info, card_name)

        # Save basic info
        saved_files['basic_info'] = self.save_basic_info(card_info, card_name)

        # Save pricing
        saved_files['pricing'] = self.save_pricing_info(card_info, card_name)

        # Save images
        images = card_info.get('images', {})
        if images.get('large'):
            saved_files['image_large'] = self.save_card_image(
                images['large'], card_name, 'large'
            )
        if images.get('small'):
            saved_files['image_small'] = self.save_card_image(
                images['small'], card_name, 'small'
            )

        return saved_files

    def list_saved_cards(self) -> list:
        """
        List all saved card files

        Returns:
            List of saved file paths
        """
        try:
            files = os.listdir(self.base_dir)
            return sorted([os.path.join(self.base_dir, f) for f in files])
        except Exception as e:
            print(f"Error listing saved cards: {e}")
            return []
