"""
OCR Processor Module
Handles text extraction from Pokemon card images using Tesseract OCR
"""

import re
import os
import platform
import pytesseract
from PIL import Image
import numpy as np
from typing import List, Dict, Optional


class OCRProcessor:
    """Processes images to extract text using OCR"""

    def __init__(self):
        """Initialize the OCR processor"""
        # Auto-configure Tesseract path for Windows
        if platform.system() == 'Windows':
            # Common Tesseract installation paths on Windows
            possible_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    print(f"✓ Tesseract found at: {path}")
                    break

    def extract_text(self, image: np.ndarray) -> str:
        """
        Extract all text from an image

        Args:
            image: Image as numpy array

        Returns:
            Extracted text as string
        """
        try:
            # Convert to PIL Image if needed
            if isinstance(image, np.ndarray):
                pil_image = Image.fromarray(image)
            else:
                pil_image = image

            # Use pytesseract to extract text
            text = pytesseract.image_to_string(pil_image, config='--psm 6')
            return text.strip()
        except Exception as e:
            print(f"Error extracting text: {e}")
            return ""

    def extract_card_name(self, text: str) -> Optional[str]:
        """
        Extract the Pokemon card name from OCR text

        Args:
            text: OCR extracted text

        Returns:
            Card name or None if not found
        """
        # Split text into lines
        lines = text.strip().split('\n')

        # The card name is typically one of the first lines
        # and is usually capitalized
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            # Remove common OCR artifacts
            cleaned = re.sub(r'[^a-zA-Z0-9\s\-\'\.]', '', line)
            cleaned = cleaned.strip()

            # Card name should be at least 3 characters
            if len(cleaned) >= 3:
                # Check if it's mostly alphabetic (card names)
                alpha_ratio = sum(c.isalpha() for c in cleaned) / len(cleaned)
                if alpha_ratio > 0.5:
                    return cleaned

        return None

    def extract_hp(self, text: str) -> Optional[str]:
        """
        Extract HP value from OCR text

        Args:
            text: OCR extracted text

        Returns:
            HP value as string or None if not found
        """
        # Look for HP pattern: "HP" followed by digits
        hp_pattern = r'HP\s*(\d+)'
        match = re.search(hp_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def extract_pokemon_info(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract various Pokemon information from OCR text

        Args:
            text: OCR extracted text

        Returns:
            Dictionary with extracted information
        """
        info = {
            'name': self.extract_card_name(text),
            'hp': self.extract_hp(text),
            'type': self.extract_type(text),
            'rarity': self.extract_rarity(text),
        }
        return info

    def extract_type(self, text: str) -> Optional[str]:
        """
        Extract Pokemon type from OCR text

        Args:
            text: OCR extracted text

        Returns:
            Pokemon type or None if not found
        """
        # Common Pokemon types
        types = [
            'Grass', 'Fire', 'Water', 'Lightning', 'Psychic',
            'Fighting', 'Darkness', 'Metal', 'Dragon', 'Fairy',
            'Colorless'
        ]

        for poke_type in types:
            if poke_type.lower() in text.lower():
                return poke_type

        return None

    def extract_rarity(self, text: str) -> Optional[str]:
        """
        Extract card rarity from OCR text

        Args:
            text: OCR extracted text

        Returns:
            Rarity or None if not found
        """
        # Common rarities
        rarities = [
            'Common', 'Uncommon', 'Rare', 'Rare Holo', 'Rare Ultra',
            'Rare Secret', 'Promo', 'Amazing Rare', 'Rare Rainbow'
        ]

        text_lower = text.lower()
        for rarity in rarities:
            if rarity.lower() in text_lower:
                return rarity

        return None

    def clean_text(self, text: str) -> str:
        """
        Clean OCR text by removing common artifacts and errors

        Args:
            text: Raw OCR text

        Returns:
            Cleaned text
        """
        # Remove multiple spaces
        cleaned = re.sub(r'\s+', ' ', text)

        # Remove special characters that are likely OCR errors
        cleaned = re.sub(r'[|@#$%^&*()_+=\[\]{};:<>?/\\]', '', cleaned)

        # Fix common OCR mistakes
        replacements = {
            '0': 'O',  # Zero to O in text
            'l': 'I',  # lowercase L to uppercase I
            '5': 'S',  # 5 to S in text (context dependent)
        }

        return cleaned.strip()

    def find_best_match(self, ocr_name: str, candidate_names: List[str]) -> Optional[str]:
        """
        Find the best matching card name from candidates

        Args:
            ocr_name: Name extracted from OCR
            candidate_names: List of possible card names from API

        Returns:
            Best matching name or None
        """
        if not ocr_name or not candidate_names:
            return None

        ocr_lower = ocr_name.lower().strip()

        # Exact match
        for name in candidate_names:
            if name.lower() == ocr_lower:
                return name

        # Partial match (OCR name in candidate)
        for name in candidate_names:
            if ocr_lower in name.lower() or name.lower() in ocr_lower:
                return name

        # Fuzzy match - check word overlap
        ocr_words = set(ocr_lower.split())
        best_match = None
        best_score = 0

        for name in candidate_names:
            name_words = set(name.lower().split())
            common_words = ocr_words & name_words
            score = len(common_words)

            if score > best_score:
                best_score = score
                best_match = name

        if best_score > 0:
            return best_match

        return None

    def extract_set_info(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract set information from card text

        Args:
            text: OCR extracted text

        Returns:
            Dictionary with set information
        """
        info = {
            'set_number': None,
            'set_code': None,
        }

        # Look for card number pattern (e.g., "25/102")
        number_pattern = r'(\d+)\s*/\s*(\d+)'
        match = re.search(number_pattern, text)
        if match:
            info['set_number'] = f"{match.group(1)}/{match.group(2)}"

        return info
