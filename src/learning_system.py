"""
Learning System for Pokemon Card Scanner
Caches card names, tracks OCR patterns, and learns from user corrections
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from difflib import SequenceMatcher
import threading


class LearningSystem:
    """Manages learning and improvement of card scanning accuracy"""

    def __init__(self, db_path: str = None):
        """
        Initialize the learning system

        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            # Default to data directory
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, 'learning.db')

        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Card names cache table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS card_cache (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    set_name TEXT,
                    set_id TEXT,
                    rarity TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, set_name)
                )
            ''')

            # OCR patterns table - tracks successful OCR extractions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ocr_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ocr_text TEXT NOT NULL,
                    actual_card_name TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    scan_count INTEGER DEFAULT 1,
                    success_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # User corrections table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ocr_text TEXT NOT NULL,
                    corrected_name TEXT NOT NULL,
                    card_id TEXT,
                    correction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Scan statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scan_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_type TEXT NOT NULL,  -- 'ocr', 'manual', 'correction'
                    card_name TEXT,
                    success BOOLEAN,
                    scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes for faster lookups
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_cache_name ON card_cache(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ocr_patterns_text ON ocr_patterns(ocr_text)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_corrections_ocr ON user_corrections(ocr_text)')

            conn.commit()

    def cache_card(self, card_info: Dict):
        """
        Cache a card's information for faster lookups

        Args:
            card_info: Dictionary containing card information
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO card_cache
                    (id, name, set_name, set_id, rarity, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    card_info.get('id'),
                    card_info.get('name'),
                    card_info.get('set', {}).get('name'),
                    card_info.get('set', {}).get('id'),
                    card_info.get('rarity'),
                    datetime.now()
                ))
                conn.commit()

    def cache_multiple_cards(self, cards: List[Dict]):
        """
        Cache multiple cards at once

        Args:
            cards: List of card info dictionaries
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for card_info in cards:
                    cursor.execute('''
                        INSERT OR REPLACE INTO card_cache
                        (id, name, set_name, set_id, rarity, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        card_info.get('id'),
                        card_info.get('name'),
                        card_info.get('set', {}).get('name'),
                        card_info.get('set', {}).get('id'),
                        card_info.get('rarity'),
                        datetime.now()
                    ))
                conn.commit()

    def get_cached_card_names(self) -> List[str]:
        """
        Get all cached card names

        Returns:
            List of card names
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT name FROM card_cache ORDER BY name')
            return [row[0] for row in cursor.fetchall()]

    def fuzzy_match_card_name(self, ocr_text: str, threshold: float = 0.6) -> List[Tuple[str, float]]:
        """
        Perform fuzzy matching against cached card names

        Args:
            ocr_text: Text extracted from OCR
            threshold: Minimum similarity threshold (0.0 to 1.0)

        Returns:
            List of (card_name, similarity_score) tuples, sorted by score
        """
        cached_names = self.get_cached_card_names()
        matches = []

        ocr_lower = ocr_text.lower().strip()

        for name in cached_names:
            name_lower = name.lower()

            # Calculate similarity
            similarity = SequenceMatcher(None, ocr_lower, name_lower).ratio()

            # Also check if OCR text is contained in the name
            if ocr_lower in name_lower or name_lower in ocr_lower:
                similarity = max(similarity, 0.7)

            if similarity >= threshold:
                matches.append((name, similarity))

        # Sort by similarity score (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:10]  # Return top 10 matches

    def record_ocr_pattern(self, ocr_text: str, actual_card_name: str, success: bool = True):
        """
        Record an OCR pattern for learning

        Args:
            ocr_text: Raw OCR text
            actual_card_name: The actual card name matched
            success: Whether the scan was successful
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if pattern exists
                cursor.execute('''
                    SELECT id, scan_count, success_count FROM ocr_patterns
                    WHERE ocr_text = ? AND actual_card_name = ?
                ''', (ocr_text, actual_card_name))

                existing = cursor.fetchone()

                if existing:
                    # Update existing pattern
                    pattern_id, scan_count, success_count = existing
                    new_scan_count = scan_count + 1
                    new_success_count = success_count + (1 if success else 0)
                    confidence = new_success_count / new_scan_count

                    cursor.execute('''
                        UPDATE ocr_patterns
                        SET scan_count = ?, success_count = ?, confidence = ?, last_used = ?
                        WHERE id = ?
                    ''', (new_scan_count, new_success_count, confidence, datetime.now(), pattern_id))
                else:
                    # Insert new pattern
                    confidence = 1.0 if success else 0.0
                    cursor.execute('''
                        INSERT INTO ocr_patterns
                        (ocr_text, actual_card_name, confidence, scan_count, success_count)
                        VALUES (?, ?, ?, 1, ?)
                    ''', (ocr_text, actual_card_name, confidence, 1 if success else 0))

                conn.commit()

    def get_learned_card_name(self, ocr_text: str) -> Optional[str]:
        """
        Get the most likely card name based on learned OCR patterns

        Args:
            ocr_text: OCR text to match

        Returns:
            Most likely card name or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Look for exact OCR text match
            cursor.execute('''
                SELECT actual_card_name, confidence
                FROM ocr_patterns
                WHERE ocr_text = ?
                ORDER BY confidence DESC, scan_count DESC
                LIMIT 1
            ''', (ocr_text,))

            result = cursor.fetchone()
            if result and result[1] > 0.5:  # Only return if confidence > 50%
                return result[0]

            # Try fuzzy matching with learned patterns
            cursor.execute('''
                SELECT DISTINCT actual_card_name, confidence
                FROM ocr_patterns
                WHERE confidence > 0.5
                ORDER BY confidence DESC, scan_count DESC
            ''')

            learned_names = cursor.fetchall()
            best_match = None
            best_score = 0.0

            ocr_lower = ocr_text.lower()
            for name, confidence in learned_names:
                similarity = SequenceMatcher(None, ocr_lower, name.lower()).ratio()
                score = similarity * confidence  # Weighted by confidence

                if score > best_score and score > 0.7:
                    best_score = score
                    best_match = name

            return best_match

    def record_user_correction(self, ocr_text: str, corrected_name: str, card_id: str = None):
        """
        Record a user correction to improve future scans

        Args:
            ocr_text: Original OCR text
            corrected_name: User-corrected card name
            card_id: Optional card ID
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Record the correction
                cursor.execute('''
                    INSERT INTO user_corrections (ocr_text, corrected_name, card_id)
                    VALUES (?, ?, ?)
                ''', (ocr_text, corrected_name, card_id))

                # Also update OCR patterns with high confidence
                cursor.execute('''
                    INSERT OR REPLACE INTO ocr_patterns
                    (ocr_text, actual_card_name, confidence, scan_count, success_count)
                    VALUES (?, ?, 1.0, 1, 1)
                ''', (ocr_text, corrected_name))

                conn.commit()

    def get_user_corrections(self, ocr_text: str) -> List[Tuple[str, str]]:
        """
        Get user corrections for similar OCR text

        Args:
            ocr_text: OCR text to match

        Returns:
            List of (corrected_name, card_id) tuples
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT corrected_name, card_id
                FROM user_corrections
                WHERE ocr_text = ?
                ORDER BY correction_date DESC
                LIMIT 5
            ''', (ocr_text,))
            return cursor.fetchall()

    def record_scan_stat(self, scan_type: str, card_name: str = None, success: bool = True):
        """
        Record scan statistics for analytics

        Args:
            scan_type: Type of scan ('ocr', 'manual', 'correction')
            card_name: Name of card scanned
            success: Whether scan was successful
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO scan_stats (scan_type, card_name, success)
                    VALUES (?, ?, ?)
                ''', (scan_type, card_name, success))
                conn.commit()

    def get_statistics(self) -> Dict:
        """
        Get overall statistics

        Returns:
            Dictionary with statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total cached cards
            cursor.execute('SELECT COUNT(*) FROM card_cache')
            total_cached = cursor.fetchone()[0]

            # Total scans
            cursor.execute('SELECT COUNT(*) FROM scan_stats')
            total_scans = cursor.fetchone()[0]

            # Successful scans
            cursor.execute('SELECT COUNT(*) FROM scan_stats WHERE success = 1')
            successful_scans = cursor.fetchone()[0]

            # Success rate
            success_rate = (successful_scans / total_scans * 100) if total_scans > 0 else 0

            # Total learned patterns
            cursor.execute('SELECT COUNT(*) FROM ocr_patterns')
            learned_patterns = cursor.fetchone()[0]

            # High confidence patterns
            cursor.execute('SELECT COUNT(*) FROM ocr_patterns WHERE confidence > 0.8')
            high_confidence = cursor.fetchone()[0]

            # User corrections
            cursor.execute('SELECT COUNT(*) FROM user_corrections')
            user_corrections = cursor.fetchone()[0]

            return {
                'total_cached_cards': total_cached,
                'total_scans': total_scans,
                'successful_scans': successful_scans,
                'success_rate': round(success_rate, 2),
                'learned_patterns': learned_patterns,
                'high_confidence_patterns': high_confidence,
                'user_corrections': user_corrections
            }

    def get_cache_size(self) -> int:
        """
        Get number of cached cards

        Returns:
            Number of cached cards
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM card_cache')
            return cursor.fetchone()[0]

    def clear_cache(self):
        """Clear the card cache (keeps learning data)"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM card_cache')
                conn.commit()

    def export_statistics(self) -> str:
        """
        Export statistics as formatted text

        Returns:
            Formatted statistics string
        """
        stats = self.get_statistics()

        output = "=== Learning System Statistics ===\n\n"
        output += f"Cached Cards: {stats['total_cached_cards']}\n"
        output += f"Total Scans: {stats['total_scans']}\n"
        output += f"Successful Scans: {stats['successful_scans']}\n"
        output += f"Success Rate: {stats['success_rate']}%\n"
        output += f"Learned OCR Patterns: {stats['learned_patterns']}\n"
        output += f"High Confidence Patterns: {stats['high_confidence_patterns']}\n"
        output += f"User Corrections: {stats['user_corrections']}\n"

        return output
