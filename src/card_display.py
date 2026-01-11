"""
Card Display Module
Handles displaying Pokemon card information in a formatted way
"""

from typing import Dict, Any, List


class CardDisplay:
    """Formats and displays Pokemon card information"""

    @staticmethod
    def format_card_info(card_info: Dict[str, Any]) -> str:
        """
        Format card information for display

        Args:
            card_info: Dictionary with card information

        Returns:
            Formatted string for display
        """
        lines = []
        lines.append("=" * 60)
        lines.append(f"  {card_info.get('name', 'Unknown Card').upper()}")
        lines.append("=" * 60)

        # Basic Info
        lines.append(f"\n📇 Basic Information:")
        lines.append(f"  ID: {card_info.get('id', 'N/A')}")
        lines.append(f"  Supertype: {card_info.get('supertype', 'N/A')}")

        if card_info.get('subtypes'):
            lines.append(f"  Subtypes: {', '.join(card_info['subtypes'])}")

        if card_info.get('hp'):
            lines.append(f"  HP: {card_info['hp']}")

        if card_info.get('types'):
            lines.append(f"  Types: {', '.join(card_info['types'])}")

        if card_info.get('evolves_from'):
            lines.append(f"  Evolves From: {card_info['evolves_from']}")

        # Set Info
        if card_info.get('set'):
            lines.append(f"\n📦 Set Information:")
            set_info = card_info['set']
            lines.append(f"  Set: {set_info.get('name', 'N/A')}")
            lines.append(f"  Series: {set_info.get('series', 'N/A')}")
            lines.append(f"  Card Number: {card_info.get('number', 'N/A')}")
            if set_info.get('release_date'):
                lines.append(f"  Release Date: {set_info['release_date']}")

        lines.append(f"  Rarity: {card_info.get('rarity', 'N/A')}")

        # Abilities
        if card_info.get('abilities'):
            lines.append(f"\n⚡ Abilities:")
            for ability in card_info['abilities']:
                lines.append(f"  • {ability['name']} ({ability['type']})")
                lines.append(f"    {ability['text']}")

        # Attacks
        if card_info.get('attacks'):
            lines.append(f"\n⚔️  Attacks:")
            for attack in card_info['attacks']:
                cost = ', '.join(attack.get('cost', []))
                damage = attack.get('damage', '')
                lines.append(f"  • {attack['name']} - {damage}")
                lines.append(f"    Cost: [{cost}]")
                if attack.get('text'):
                    lines.append(f"    {attack['text']}")

        # Weaknesses, Resistances, Retreat
        stats = []
        if card_info.get('weaknesses'):
            weak = ', '.join([f"{w['type']} {w['value']}" for w in card_info['weaknesses']])
            stats.append(f"  Weakness: {weak}")

        if card_info.get('resistances'):
            resist = ', '.join([f"{r['type']} {r['value']}" for r in card_info['resistances']])
            stats.append(f"  Resistance: {resist}")

        if card_info.get('retreat_cost'):
            retreat_count = len(card_info['retreat_cost'])
            stats.append(f"  Retreat Cost: {retreat_count} energy")

        if stats:
            lines.append(f"\n🛡️  Stats:")
            lines.extend(stats)

        # Pricing
        pricing = card_info.get('pricing', {})
        if CardDisplay._has_pricing(pricing):
            lines.append(f"\n💰 Pricing:")

            # TCGPlayer
            tcg = pricing.get('tcgplayer', {})
            if tcg and tcg.get('prices'):
                lines.append(f"  TCGPlayer (USD):")
                if 'normal' in tcg['prices']:
                    normal = tcg['prices']['normal']
                    if normal.get('market'):
                        lines.append(f"    Normal Market: ${normal['market']:.2f}")
                    if normal.get('low'):
                        lines.append(f"    Normal Low: ${normal['low']:.2f}")
                    if normal.get('high'):
                        lines.append(f"    Normal High: ${normal['high']:.2f}")

                if 'holofoil' in tcg['prices']:
                    holo = tcg['prices']['holofoil']
                    if holo.get('market'):
                        lines.append(f"    Holofoil Market: ${holo['market']:.2f}")
                    if holo.get('low'):
                        lines.append(f"    Holofoil Low: ${holo['low']:.2f}")
                    if holo.get('high'):
                        lines.append(f"    Holofoil High: ${holo['high']:.2f}")

            # Cardmarket
            cm = pricing.get('cardmarket', {})
            if cm and cm.get('prices'):
                lines.append(f"  Cardmarket (EUR):")
                prices = cm['prices']
                if prices.get('trend_price'):
                    lines.append(f"    Trend Price: €{prices['trend_price']:.2f}")
                if prices.get('average_sell_price'):
                    lines.append(f"    Average Sell: €{prices['average_sell_price']:.2f}")
                if prices.get('low_price'):
                    lines.append(f"    Low Price: €{prices['low_price']:.2f}")

        # Legalities
        if card_info.get('legalities'):
            legalities = card_info['legalities']
            legal_formats = []
            for format_name, status in legalities.items():
                if status:
                    legal_formats.append(f"{format_name.capitalize()}: {status}")

            if legal_formats:
                lines.append(f"\n⚖️  Legalities:")
                for legal in legal_formats:
                    lines.append(f"  {legal}")

        # Artist
        if card_info.get('artist'):
            lines.append(f"\n🎨 Artist: {card_info['artist']}")

        # Flavor Text
        if card_info.get('flavor_text'):
            lines.append(f"\n💭 Flavor Text:")
            lines.append(f"  \"{card_info['flavor_text']}\"")

        # Images
        if card_info.get('images'):
            lines.append(f"\n🖼️  Images:")
            images = card_info['images']
            if images.get('small'):
                lines.append(f"  Small: {images['small']}")
            if images.get('large'):
                lines.append(f"  Large: {images['large']}")

        lines.append("=" * 60)

        return '\n'.join(lines)

    @staticmethod
    def _has_pricing(pricing: Dict[str, Any]) -> bool:
        """
        Check if pricing information is available

        Args:
            pricing: Pricing dictionary

        Returns:
            True if pricing is available
        """
        if not pricing:
            return False

        tcg = pricing.get('tcgplayer', {})
        cm = pricing.get('cardmarket', {})

        return bool(tcg.get('prices') or cm.get('prices'))

    @staticmethod
    def format_card_list(cards: List[Dict[str, Any]]) -> str:
        """
        Format a list of cards for display

        Args:
            cards: List of card information dictionaries

        Returns:
            Formatted string
        """
        if not cards:
            return "No cards found."

        lines = [f"\nFound {len(cards)} card(s):\n"]
        lines.append("-" * 60)

        for i, card in enumerate(cards, 1):
            lines.append(f"{i}. {card.get('name', 'Unknown')}")
            lines.append(f"   ID: {card.get('id', 'N/A')}")
            lines.append(f"   Set: {card.get('set', {}).get('name', 'N/A')}")
            lines.append(f"   Rarity: {card.get('rarity', 'N/A')}")

            # Show quick price if available
            pricing = card.get('pricing', {})
            tcg = pricing.get('tcgplayer', {})
            if tcg.get('prices', {}).get('normal', {}).get('market'):
                price = tcg['prices']['normal']['market']
                lines.append(f"   Price: ${price:.2f}")

            lines.append("-" * 60)

        return '\n'.join(lines)

    @staticmethod
    def format_search_results(cards: List[Any], max_display: int = 10) -> str:
        """
        Format search results from API

        Args:
            cards: List of Card objects from API
            max_display: Maximum number of cards to display

        Returns:
            Formatted string
        """
        if not cards:
            return "No cards found."

        display_count = min(len(cards), max_display)
        lines = [f"\nFound {len(cards)} card(s), showing first {display_count}:\n"]
        lines.append("=" * 70)

        for i, card in enumerate(cards[:display_count], 1):
            lines.append(f"\n{i}. {card.name}")
            lines.append(f"   ID: {card.id}")

            if hasattr(card, 'set') and card.set:
                lines.append(f"   Set: {card.set.name}")

            if hasattr(card, 'rarity') and card.rarity:
                lines.append(f"   Rarity: {card.rarity}")

            if hasattr(card, 'hp') and card.hp:
                lines.append(f"   HP: {card.hp}")

            if hasattr(card, 'types') and card.types:
                lines.append(f"   Types: {', '.join(card.types)}")

        lines.append("\n" + "=" * 70)

        return '\n'.join(lines)

    @staticmethod
    def format_pricing_summary(card_info: Dict[str, Any]) -> str:
        """
        Format just the pricing information

        Args:
            card_info: Card information dictionary

        Returns:
            Formatted pricing string
        """
        lines = [f"\n💰 Pricing for {card_info.get('name', 'Unknown Card')}:"]
        lines.append("=" * 50)

        pricing = card_info.get('pricing', {})

        # TCGPlayer
        tcg = pricing.get('tcgplayer', {})
        if tcg and tcg.get('prices'):
            lines.append("\nTCGPlayer (USD):")
            if 'normal' in tcg['prices']:
                normal = tcg['prices']['normal']
                if normal.get('market'):
                    lines.append(f"  Market Price: ${normal['market']:.2f}")
            if 'holofoil' in tcg['prices']:
                holo = tcg['prices']['holofoil']
                if holo.get('market'):
                    lines.append(f"  Holofoil Market: ${holo['market']:.2f}")

        # Cardmarket
        cm = pricing.get('cardmarket', {})
        if cm and cm.get('prices'):
            lines.append("\nCardmarket (EUR):")
            prices = cm['prices']
            if prices.get('trend_price'):
                lines.append(f"  Trend Price: €{prices['trend_price']:.2f}")

        if not CardDisplay._has_pricing(pricing):
            lines.append("\nNo pricing information available.")

        lines.append("=" * 50)

        return '\n'.join(lines)
