#!/usr/bin/env python3
"""
Diagnostic Tool for Pokemon Card Scanner
Checks OCR setup, learning system, and API connectivity
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from learning_system import LearningSystem
from tcg_api import TCGAPIClient
import pytesseract

def check_tesseract():
    """Check if Tesseract OCR is installed and working"""
    print("\n" + "="*60)
    print("Checking Tesseract OCR Installation")
    print("="*60)
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✓ Tesseract installed: version {version}")
        return True
    except Exception as e:
        print(f"✗ Tesseract not found: {e}")
        print("\nPlease install Tesseract OCR:")
        print("  - Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        print("  - Linux: sudo apt-get install tesseract-ocr")
        print("  - Mac: brew install tesseract")
        return False

def check_learning_system():
    """Check learning system status"""
    print("\n" + "="*60)
    print("Checking Learning System")
    print("="*60)
    try:
        learning = LearningSystem()
        stats = learning.get_statistics()

        print(f"✓ Learning system initialized")
        print(f"  - Cached cards: {stats['total_cached_cards']}")
        print(f"  - Total scans: {stats['total_scans']}")
        print(f"  - Success rate: {stats['success_rate']}%")
        print(f"  - Learned patterns: {stats['learned_patterns']}")
        print(f"  - User corrections: {stats['user_corrections']}")

        if stats['total_cached_cards'] == 0:
            print("\n💡 Recommendation: Build the card cache!")
            print("   Go to 'Learning > Build Card Cache' in the app")
            print("   This will enable fuzzy matching for better accuracy")

        return True
    except Exception as e:
        print(f"✗ Learning system error: {e}")
        return False

def check_api():
    """Check Pokemon TCG API connectivity"""
    print("\n" + "="*60)
    print("Checking Pokemon TCG API")
    print("="*60)
    try:
        api = TCGAPIClient()
        print("Searching for test card (Pikachu)...")
        cards = api.search_card_by_name("Pikachu")
        if cards:
            print(f"✓ API working - found {len(cards)} Pikachu cards")
            return True
        else:
            print("⚠ API responded but no cards found")
            return False
    except Exception as e:
        print(f"✗ API error: {e}")
        print("\nPlease check:")
        print("  - Internet connection")
        print("  - Pokemon TCG API status: https://pokemontcg.io/")
        return False

def run_diagnostics():
    """Run all diagnostic checks"""
    print("\n" + "="*60)
    print("POKEMON CARD SCANNER DIAGNOSTICS")
    print("="*60)

    results = {
        'tesseract': check_tesseract(),
        'learning': check_learning_system(),
        'api': check_api()
    }

    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)

    all_passed = all(results.values())

    if all_passed:
        print("✓ All checks passed! Scanner should work properly.")
    else:
        print("⚠ Some checks failed. Please fix the issues above.")

    print("\nComponent Status:")
    for component, passed in results.items():
        status = "✓ OK" if passed else "✗ FAILED"
        print(f"  {component.capitalize():15} {status}")

    if not results['tesseract']:
        print("\n⚠ CRITICAL: Tesseract is required for OCR!")
        print("  Install it before using the scanner.")

    if not results['api']:
        print("\n⚠ WARNING: API not accessible")
        print("  Scanner won't be able to search for cards.")

    print()
    return all_passed

if __name__ == "__main__":
    success = run_diagnostics()
    sys.exit(0 if success else 1)
