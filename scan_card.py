#!/usr/bin/env python3
"""
Simple command-line interface for Pokemon card scanning
"""

import sys
import os
import cv2

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from camera_capture import CameraCapture
from ocr_processor import OCRProcessor
from tcg_api import TCGAPIClient
from card_display import CardDisplay
from file_manager import FileManager


def main():
    """Main CLI function"""
    print("=" * 70)
    print("Pokemon Card Scanner - Command Line Interface")
    print("=" * 70)

    # Initialize components
    print("\n📷 Initializing camera...")
    camera = CameraCapture()

    print("🔍 Initializing OCR...")
    ocr = OCRProcessor()

    print("🌐 Connecting to Pokemon TCG API...")
    api = TCGAPIClient()

    print("💾 Setting up file manager...")
    file_manager = FileManager()

    print("\n✓ All systems ready!\n")

    # Start camera
    if not camera.start():
        print("❌ Failed to start camera. Exiting.")
        return

    print("Camera started. Press SPACE to capture, 'q' to quit, 's' to search manually.")

    try:
        while True:
            frame = camera.read_frame()
            if frame is None:
                continue

            # Display frame
            display_frame = cv2.resize(frame, (800, 600))
            cv2.putText(display_frame, "Press SPACE to capture | 'q' to quit | 's' to search",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Pokemon Card Scanner', display_frame)

            key = cv2.waitKey(1) & 0xFF

            # Quit
            if key == ord('q'):
                break

            # Manual search
            elif key == ord('s'):
                cv2.destroyAllWindows()
                card_name = input("\nEnter card name to search: ").strip()
                if card_name:
                    search_and_display(api, card_name, file_manager)
                if not camera.start():
                    break
                continue

            # Capture and process
            elif key == ord(' '):
                print("\n" + "=" * 70)
                print("📸 Capturing image...")

                captured = camera.capture_image()
                if captured is None:
                    print("❌ Failed to capture image")
                    continue

                # Detect card
                print("🔍 Detecting card region...")
                card_region = camera.detect_card_region(captured)

                # Enhance
                print("✨ Enhancing image...")
                enhanced = camera.enhance_image(card_region)

                # OCR
                print("📝 Extracting text with OCR...")
                preprocessed = camera.preprocess_card_image(enhanced)
                text = ocr.extract_text(preprocessed)

                if not text:
                    print("⚠️  No text detected. Try adjusting card position.")
                    continue

                print(f"\n📄 Extracted text:\n{text[:200]}...\n")

                # Extract card info
                card_info = ocr.extract_pokemon_info(text)
                card_name = card_info.get('name')

                if not card_name:
                    print("⚠️  Could not identify card name from OCR.")
                    manual = input("Enter card name manually (or press Enter to skip): ").strip()
                    if manual:
                        card_name = manual
                    else:
                        continue

                print(f"🔎 Searching for: {card_name}")

                # Search API
                search_and_display(api, card_name, file_manager)

    finally:
        camera.stop()
        cv2.destroyAllWindows()
        print("\n👋 Goodbye!")


def search_and_display(api: TCGAPIClient, card_name: str, file_manager: FileManager):
    """
    Search for card and display results

    Args:
        api: API client
        card_name: Name to search
        file_manager: File manager for saving
    """
    # Search
    cards = api.search_card_by_name(card_name)
    if not cards:
        cards = api.search_card_fuzzy(card_name)

    if not cards:
        print(f"❌ No cards found for '{card_name}'")
        return

    print(f"\n✓ Found {len(cards)} card(s)!")
    print(CardDisplay.format_search_results(cards, max_display=10))

    # Select card
    if len(cards) == 1:
        selected_index = 0
        print(f"\n→ Auto-selecting the only result")
    else:
        try:
            selected_index = int(input("\nEnter card number to view (1-{0}): ".format(len(cards)))) - 1
            if selected_index < 0 or selected_index >= len(cards):
                print("Invalid selection")
                return
        except (ValueError, EOFError):
            print("Invalid input")
            return

    # Get card info
    selected_card = cards[selected_index]
    card_info = api.extract_card_info(selected_card)

    # Display
    print("\n" + CardDisplay.format_card_info(card_info))

    # Ask to save
    save = input("\n💾 Save card data? (y/n): ").strip().lower()
    if save == 'y':
        saved_files = file_manager.save_all_card_info(card_info)
        print(f"\n✓ Card data saved!")
        for file_type, filepath in saved_files.items():
            if filepath:
                print(f"  - {file_type}: {filepath}")


if __name__ == "__main__":
    main()
