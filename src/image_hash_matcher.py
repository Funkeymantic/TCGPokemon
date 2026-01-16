"""
Image Hash Matcher Module
Downloads Pokemon card images and creates perceptual hash database for image-based matching
Inspired by NolanAmblard/Pokemon-Card-Scanner and pokemon-card-recognizer
"""

import os
import sqlite3
import requests
import numpy as np
import cv2
from PIL import Image
from io import BytesIO
from typing import List, Tuple, Optional, Dict
import imagehash
import threading
from pokemontcgsdk import Card


class ImageHashMatcher:
    """Matches cards using perceptual image hashing"""

    def __init__(self, db_path: str = "card_data/image_hashes.db"):
        """
        Initialize the image hash matcher

        Args:
            db_path: Path to SQLite database for storing hashes
        """
        self.db_path = db_path
        self.lock = threading.Lock()

        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize the SQLite database for storing image hashes"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create table for card hashes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS card_hashes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    set_name TEXT,
                    set_code TEXT,
                    number TEXT,
                    rarity TEXT,
                    image_url TEXT,

                    -- Multiple hash types for better accuracy
                    average_hash TEXT,
                    perceptual_hash TEXT,
                    difference_hash TEXT,
                    wavelet_hash TEXT,

                    -- Rotated versions for orientation handling
                    avg_hash_90 TEXT,
                    avg_hash_180 TEXT,
                    avg_hash_270 TEXT,

                    phash_90 TEXT,
                    phash_180 TEXT,
                    phash_270 TEXT,

                    downloaded INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create index for faster lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_card_name ON card_hashes(name)
            ''')

            conn.commit()
            print("[ImageHash] Database initialized")

    def download_all_cards(self, max_cards: int = 0, callback=None) -> int:
        """
        Download all Pokemon cards from the API and compute their hashes

        Args:
            max_cards: Maximum number of cards to download (0 = all)
            callback: Optional callback function(current, total, card_name) for progress

        Returns:
            Number of cards downloaded
        """
        print("[ImageHash] Starting card download from Pokemon TCG API...")

        try:
            # Get all cards from API using pokemontcgsdk
            all_cards = []
            page = 1
            page_size = 250

            while True:
                print(f"[ImageHash] Fetching page {page}...")

                try:
                    # Use Card.where() with pagination
                    cards = Card.where(page=page, pageSize=page_size)
                    cards_list = list(cards) if cards else []

                    if not cards_list:
                        print("[ImageHash] No more cards to fetch")
                        break

                    all_cards.extend(cards_list)
                    print(f"[ImageHash] Retrieved {len(all_cards)} cards so far...")

                    page += 1

                    # Limit if requested
                    if max_cards > 0 and len(all_cards) >= max_cards:
                        all_cards = all_cards[:max_cards]
                        print(f"[ImageHash] Reached limit of {max_cards} cards")
                        break

                except Exception as e:
                    print(f"[ImageHash] Error fetching page {page}: {e}")
                    break

            print(f"[ImageHash] Total cards to process: {len(all_cards)}")

            # Download and hash each card
            downloaded = 0
            for idx, card in enumerate(all_cards, 1):
                try:
                    # Get card name - Card objects have .name attribute
                    card_name = card.name if hasattr(card, 'name') else 'Unknown'

                    if callback:
                        callback(idx, len(all_cards), card_name)

                    if self._download_and_hash_card(card):
                        downloaded += 1

                    if idx % 100 == 0:
                        print(f"[ImageHash] Progress: {idx}/{len(all_cards)} cards processed")

                except Exception as e:
                    card_name = card.name if hasattr(card, 'name') else 'Unknown'
                    print(f"[ImageHash] Error processing card {card_name}: {e}")
                    continue

            print(f"[ImageHash] ✓ Downloaded and hashed {downloaded} cards")
            return downloaded

        except Exception as e:
            print(f"[ImageHash] Error downloading cards: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def _download_and_hash_card(self, card) -> bool:
        """
        Download a single card image and compute its hashes

        Args:
            card: Card object from pokemontcgsdk

        Returns:
            True if successful, False otherwise
        """
        try:
            # Card objects have attributes, not dict methods
            card_id = card.id if hasattr(card, 'id') else None
            card_name = card.name if hasattr(card, 'name') else 'Unknown'

            if not card_id:
                print(f"[ImageHash] No card ID for {card_name}")
                return False

            # Get images from card object
            images = card.images if hasattr(card, 'images') else None
            if not images:
                print(f"[ImageHash] No images for {card_name}")
                return False

            # Get high-res image URL
            image_url = getattr(images, 'large', None) or getattr(images, 'small', None)
            if not image_url:
                print(f"[ImageHash] No image URL for {card_name}")
                return False

            # Check if already in database
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT id FROM card_hashes WHERE id = ?', (card_id,))
                    if cursor.fetchone():
                        return True  # Already have this card

            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            # Load image
            image = Image.open(BytesIO(response.content))

            # Compute hashes
            hashes = self._compute_all_hashes(image)

            # Store in database
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()

                    # Get set info from card object
                    set_obj = card.set if hasattr(card, 'set') else None
                    set_name = getattr(set_obj, 'name', None) if set_obj else None
                    set_id = getattr(set_obj, 'id', None) if set_obj else None

                    card_number = card.number if hasattr(card, 'number') else None
                    card_rarity = card.rarity if hasattr(card, 'rarity') else None

                    cursor.execute('''
                        INSERT OR REPLACE INTO card_hashes
                        (id, name, set_name, set_code, number, rarity, image_url,
                         average_hash, perceptual_hash, difference_hash, wavelet_hash,
                         avg_hash_90, avg_hash_180, avg_hash_270,
                         phash_90, phash_180, phash_270,
                         downloaded)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        card_id,
                        card_name,
                        set_name,
                        set_id,
                        card_number,
                        card_rarity,
                        image_url,
                        str(hashes['avg_hash']),
                        str(hashes['p_hash']),
                        str(hashes['d_hash']),
                        str(hashes['w_hash']),
                        str(hashes['avg_hash_90']),
                        str(hashes['avg_hash_180']),
                        str(hashes['avg_hash_270']),
                        str(hashes['phash_90']),
                        str(hashes['phash_180']),
                        str(hashes['phash_270']),
                        1
                    ))

                    conn.commit()

            return True

        except Exception as e:
            print(f"[ImageHash] Error downloading/hashing {card.get('name', 'Unknown')}: {e}")
            return False

    def _compute_all_hashes(self, image: Image.Image) -> Dict[str, imagehash.ImageHash]:
        """
        Compute all hash types for an image including rotations

        Args:
            image: PIL Image object

        Returns:
            Dictionary of hash types and their values
        """
        hashes = {}

        # Original orientation
        hashes['avg_hash'] = imagehash.average_hash(image)
        hashes['p_hash'] = imagehash.phash(image)
        hashes['d_hash'] = imagehash.dhash(image)
        hashes['w_hash'] = imagehash.whash(image)

        # Rotated versions (for handling card orientation)
        image_90 = image.rotate(90, expand=True)
        image_180 = image.rotate(180, expand=True)
        image_270 = image.rotate(270, expand=True)

        hashes['avg_hash_90'] = imagehash.average_hash(image_90)
        hashes['avg_hash_180'] = imagehash.average_hash(image_180)
        hashes['avg_hash_270'] = imagehash.average_hash(image_270)

        hashes['phash_90'] = imagehash.phash(image_90)
        hashes['phash_180'] = imagehash.phash(image_180)
        hashes['phash_270'] = imagehash.phash(image_270)

        return hashes

    def match_card_image(self, image: np.ndarray, threshold: int = 15) -> Optional[Dict]:
        """
        Match a captured card image against the hash database

        Args:
            image: Card image as numpy array (from camera/OCR)
            threshold: Maximum hash distance for a match (lower = more strict)

        Returns:
            Dictionary with matched card info and confidence, or None if no match
        """
        try:
            # Convert numpy array to PIL Image
            if isinstance(image, np.ndarray):
                if len(image.shape) == 2:  # Grayscale
                    pil_image = Image.fromarray(image)
                else:  # Color
                    # Convert BGR to RGB if needed
                    if image.shape[2] == 3:
                        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                        pil_image = Image.fromarray(image_rgb)
                    else:
                        pil_image = Image.fromarray(image)
            else:
                pil_image = image

            # Compute hashes for the captured image
            captured_hashes = self._compute_all_hashes(pil_image)

            # Search database for matches
            best_match = None
            best_distance = float('inf')

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM card_hashes WHERE downloaded = 1')

                for row in cursor.fetchall():
                    # Calculate distances for all hash types
                    distances = []

                    # Average hash distances (including rotations)
                    if row[7]:  # average_hash
                        distances.append(captured_hashes['avg_hash'] - imagehash.hex_to_hash(row[7]))
                    if row[11]:  # avg_hash_90
                        distances.append(captured_hashes['avg_hash'] - imagehash.hex_to_hash(row[11]))
                    if row[12]:  # avg_hash_180
                        distances.append(captured_hashes['avg_hash'] - imagehash.hex_to_hash(row[12]))
                    if row[13]:  # avg_hash_270
                        distances.append(captured_hashes['avg_hash'] - imagehash.hex_to_hash(row[13]))

                    # Perceptual hash distances (including rotations)
                    if row[8]:  # perceptual_hash
                        distances.append(captured_hashes['p_hash'] - imagehash.hex_to_hash(row[8]))
                    if row[14]:  # phash_90
                        distances.append(captured_hashes['p_hash'] - imagehash.hex_to_hash(row[14]))
                    if row[15]:  # phash_180
                        distances.append(captured_hashes['p_hash'] - imagehash.hex_to_hash(row[15]))
                    if row[16]:  # phash_270
                        distances.append(captured_hashes['p_hash'] - imagehash.hex_to_hash(row[16]))

                    # Difference hash
                    if row[9]:  # difference_hash
                        distances.append(captured_hashes['d_hash'] - imagehash.hex_to_hash(row[9]))

                    # Wavelet hash
                    if row[10]:  # wavelet_hash
                        distances.append(captured_hashes['w_hash'] - imagehash.hex_to_hash(row[10]))

                    # Take the minimum distance (best match across all hash types and rotations)
                    if distances:
                        min_distance = min(distances)

                        if min_distance < best_distance:
                            best_distance = min_distance
                            best_match = {
                                'id': row[0],
                                'name': row[1],
                                'set_name': row[2],
                                'set_code': row[3],
                                'number': row[4],
                                'rarity': row[5],
                                'image_url': row[6],
                                'distance': min_distance,
                                'confidence': max(0, 100 - (min_distance * 5))  # Convert distance to confidence %
                            }

            # Return match if below threshold
            if best_match and best_distance <= threshold:
                print(f"[ImageHash] ✓ Matched: {best_match['name']} (distance: {best_distance}, confidence: {best_match['confidence']:.1f}%)")
                return best_match

            print(f"[ImageHash] No match found (best distance: {best_distance})")
            return None

        except Exception as e:
            print(f"[ImageHash] Error matching image: {e}")
            return None

    def get_database_stats(self) -> Dict:
        """
        Get statistics about the hash database

        Returns:
            Dictionary with database statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('SELECT COUNT(*) FROM card_hashes')
                total_cards = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(*) FROM card_hashes WHERE downloaded = 1')
                downloaded_cards = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(DISTINCT set_code) FROM card_hashes')
                total_sets = cursor.fetchone()[0]

                return {
                    'total_cards': total_cards,
                    'downloaded_cards': downloaded_cards,
                    'total_sets': total_sets,
                    'database_path': self.db_path
                }

        except Exception as e:
            print(f"[ImageHash] Error getting stats: {e}")
            return {}

    def clear_database(self):
        """Clear all entries from the hash database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM card_hashes')
                conn.commit()
                print("[ImageHash] ✓ Database cleared")
        except Exception as e:
            print(f"[ImageHash] Error clearing database: {e}")
