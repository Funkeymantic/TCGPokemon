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
import cv2
from typing import List, Dict, Optional, Tuple


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

            tesseract_found = False
            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    print(f"✓ Tesseract found at: {path}")
                    tesseract_found = True
                    break

            if not tesseract_found:
                print("⚠ Tesseract not found in common locations.")
                print("  Please install from: https://github.com/UB-Mannheim/tesseract/wiki")
                print(f"  Checked paths: {possible_paths}")

    def find_card_contour(self, image: np.ndarray) -> Tuple[Optional[np.ndarray], float]:
        """
        Find the largest rectangular contour in the image (card edges)

        Args:
            image: Input image as numpy array

        Returns:
            Tuple of (corners, area) or (None, 0) if not found
        """
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()

            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Canny edge detection
            edges = cv2.Canny(blurred, 50, 200)

            # Dilate and erode to clean up edges
            kernel = np.ones((5, 5), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=2)
            edges = cv2.erode(edges, kernel, iterations=1)

            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Find biggest rectangular contour
            biggest_contour = None
            max_area = 0

            for contour in contours:
                area = cv2.contourArea(contour)

                # Filter small contours (at least 5000 pixels)
                if area > 5000:
                    # Approximate contour to polygon
                    perimeter = cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

                    # Check if it's a rectangle (4 corners)
                    if len(approx) == 4 and area > max_area:
                        biggest_contour = approx
                        max_area = area

            if biggest_contour is not None:
                # Convert from shape (4, 1, 2) to (4, 2)
                corners = biggest_contour.reshape(4, 2)
                return corners, max_area

            return None, 0

        except Exception as e:
            print(f"[OCR] Error finding card contour: {e}")
            return None, 0

    def reorder_corners(self, corners: np.ndarray) -> np.ndarray:
        """
        Reorder corners to [top-left, top-right, bottom-left, bottom-right]

        Args:
            corners: Array of 4 corner points

        Returns:
            Reordered corners array
        """
        # Reshape if needed
        if corners.shape == (4, 1, 2):
            corners = corners.reshape(4, 2)

        # Initialize ordered points
        ordered = np.zeros((4, 2), dtype=np.float32)

        # Sum and difference of coordinates
        s = corners.sum(axis=1)
        diff = np.diff(corners, axis=1)

        # Top-left has smallest sum
        ordered[0] = corners[np.argmin(s)]
        # Bottom-right has largest sum
        ordered[3] = corners[np.argmax(s)]
        # Top-right has smallest difference
        ordered[1] = corners[np.argmin(diff)]
        # Bottom-left has largest difference
        ordered[2] = corners[np.argmax(diff)]

        return ordered

    def apply_perspective_transform(self, image: np.ndarray, corners: np.ndarray,
                                   width: int = 500, height: int = 700) -> np.ndarray:
        """
        Apply perspective transformation to straighten card image

        Args:
            image: Input image
            corners: 4 corner points in order [top-left, top-right, bottom-left, bottom-right]
            width: Target width for transformed image
            height: Target height for transformed image

        Returns:
            Transformed image
        """
        # Reorder corners
        ordered_corners = self.reorder_corners(corners)

        # Destination points for perspective transform
        dst_points = np.array([
            [0, 0],
            [width - 1, 0],
            [0, height - 1],
            [width - 1, height - 1]
        ], dtype=np.float32)

        # Calculate perspective transform matrix
        matrix = cv2.getPerspectiveTransform(ordered_corners, dst_points)

        # Apply transformation
        warped = cv2.warpPerspective(image, matrix, (width, height))

        return warped

    def preprocess_card_image(self, image: np.ndarray, debug: bool = False) -> Tuple[np.ndarray, bool]:
        """
        Preprocess card image by detecting edges and applying perspective transformation

        Args:
            image: Input image as numpy array
            debug: If True, print debug information

        Returns:
            Tuple of (processed_image, was_transformed)
            - processed_image: The transformed image (or original if transformation failed)
            - was_transformed: True if perspective transformation was applied
        """
        try:
            # Find card contour
            corners, area = self.find_card_contour(image)

            if corners is not None and area > 10000:  # Minimum area threshold
                if debug:
                    print(f"[OCR] Card detected! Area: {area:.0f} pixels")

                # Calculate appropriate size based on aspect ratio
                # Pokemon cards are approximately 2.5" x 3.5" (aspect ratio ~0.714)
                height = 700
                width = int(height * 0.714)

                # Apply perspective transformation
                transformed = self.apply_perspective_transform(image, corners, width, height)

                if debug:
                    print(f"[OCR] Applied perspective transformation ({width}x{height})")

                return transformed, True
            else:
                if debug:
                    print("[OCR] No card contour found, using original image")
                return image, False

        except Exception as e:
            print(f"[OCR] Error in preprocessing: {e}")
            return image, False

    def extract_text(self, image: np.ndarray, use_preprocessing: bool = True) -> str:
        """
        Extract all text from an image

        Args:
            image: Image as numpy array
            use_preprocessing: If True, apply perspective transformation before OCR

        Returns:
            Extracted text as string
        """
        try:
            # Apply perspective transformation if enabled
            processed_image = image
            if use_preprocessing:
                processed_image, was_transformed = self.preprocess_card_image(image, debug=True)
                if was_transformed:
                    print("[OCR] ✓ Card straightened with perspective transformation")

            # Convert to PIL Image if needed
            if isinstance(processed_image, np.ndarray):
                pil_image = Image.fromarray(processed_image)
            else:
                pil_image = processed_image

            # Try multiple PSM modes for better results
            # PSM 6: Assume a single uniform block of text
            # PSM 11: Sparse text. Find as much text as possible in no particular order
            # PSM 3: Fully automatic page segmentation

            best_text = ""
            max_length = 0

            for psm in [11, 6, 3]:
                try:
                    text = pytesseract.image_to_string(
                        pil_image,
                        config=f'--psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789- '
                    )
                    # Keep the longest/best result
                    if len(text.strip()) > max_length:
                        best_text = text
                        max_length = len(text.strip())
                except:
                    continue

            return best_text.strip()
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

        # Try multiple strategies to extract the card name
        candidates = []

        # Strategy 1: First meaningful line (most common)
        for line in lines[:7]:  # Check first 7 lines
            line = line.strip()
            # Remove common OCR artifacts
            cleaned = re.sub(r'[^a-zA-Z0-9\s\-\'\.]', '', line)
            cleaned = cleaned.strip()

            # Card name should be at least 2 characters (more lenient)
            if len(cleaned) >= 2:
                # Check if it's mostly alphabetic (card names)
                alpha_ratio = sum(c.isalpha() for c in cleaned) / len(cleaned) if len(cleaned) > 0 else 0
                if alpha_ratio > 0.4:  # Lower threshold - was 0.5
                    candidates.append((cleaned, alpha_ratio, 1))  # (name, alpha_ratio, priority)

        # Strategy 2: Longest alphabetic sequence
        all_words = ' '.join(lines).split()
        for word in all_words:
            cleaned = re.sub(r'[^a-zA-Z0-9\s\-\']', '', word).strip()
            if len(cleaned) >= 3:
                alpha_ratio = sum(c.isalpha() for c in cleaned) / len(cleaned) if len(cleaned) > 0 else 0
                if alpha_ratio > 0.6:
                    candidates.append((cleaned, alpha_ratio, 2))

        # Strategy 3: Look for capitalized words (Pokemon names are often capitalized)
        for line in lines[:10]:
            words = line.split()
            for word in words:
                if word and word[0].isupper() and len(word) >= 3:
                    cleaned = re.sub(r'[^a-zA-Z0-9\-\']', '', word).strip()
                    if len(cleaned) >= 3:
                        alpha_ratio = sum(c.isalpha() for c in cleaned) / len(cleaned) if len(cleaned) > 0 else 0
                        candidates.append((cleaned, alpha_ratio, 3))

        # Return the best candidate (prioritize by priority, then alpha_ratio, then length)
        if candidates:
            # Sort by: priority (lower is better), then alpha_ratio (higher is better), then length
            candidates.sort(key=lambda x: (x[2], -x[1], -len(x[0])))
            best_name = candidates[0][0]
            print(f"[OCR] Extracted card name: '{best_name}' (from {len(candidates)} candidates)")
            return best_name

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
