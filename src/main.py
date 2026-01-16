"""
Pokemon Card Scanner - Main Application
A GUI application for scanning Pokemon cards and retrieving information from the TCG API
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import cv2
from PIL import Image, ImageTk
import threading
import requests
from io import BytesIO
from typing import Optional, List

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from camera_capture import CameraCapture
from ocr_processor import OCRProcessor
from tcg_api import TCGAPIClient
from card_display import CardDisplay
from file_manager import FileManager
from learning_system import LearningSystem
from image_hash_matcher import ImageHashMatcher
from verification_dialog import show_verification_dialog


class PokemonCardScannerApp:
    """Main application for Pokemon card scanning"""

    def __init__(self, root):
        """
        Initialize the application

        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("Pokemon Card Scanner")
        self.root.geometry("1400x900")

        # Initialize components
        self.camera = CameraCapture()
        self.ocr = OCRProcessor()
        self.api = TCGAPIClient()
        self.file_manager = FileManager()
        self.learning = LearningSystem()
        self.image_matcher = ImageHashMatcher()

        # State
        self.camera_running = False
        self.current_frame = None
        self.selected_card = None
        self.search_results = []
        self.last_ocr_text = None  # Track last OCR text for corrections
        self.last_captured_image = None  # Track last captured image for verification

        # Setup UI
        self.setup_ui()

        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        """Setup the user interface"""
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Learning menu
        learning_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Learning", menu=learning_menu)
        learning_menu.add_command(label="View Statistics", command=self.show_statistics)
        learning_menu.add_command(label="Build Card Cache", command=self.build_card_cache)
        learning_menu.add_separator()
        learning_menu.add_command(label="Download Card Images", command=self.download_card_images)
        learning_menu.add_command(label="Image Hash Statistics", command=self.show_image_hash_stats)
        learning_menu.add_separator()
        learning_menu.add_command(label="Correct Last Scan", command=self.show_correction_dialog)

        # Main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(1, weight=1)

        # Left panel - Camera and controls
        left_panel = ttk.Frame(main_container)
        left_panel.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        # Camera view
        camera_label = ttk.Label(left_panel, text="Camera View", font=('Arial', 12, 'bold'))
        camera_label.pack(pady=(0, 5))

        self.camera_canvas = tk.Canvas(left_panel, width=640, height=360, bg='black')
        self.camera_canvas.pack()

        # Camera controls
        controls_frame = ttk.Frame(left_panel)
        controls_frame.pack(pady=10)

        # Camera selection dropdown
        camera_select_frame = ttk.Frame(controls_frame)
        camera_select_frame.grid(row=0, column=0, columnspan=3, pady=(0, 5))

        ttk.Label(camera_select_frame, text="Camera:").pack(side=tk.LEFT, padx=(0, 5))
        self.camera_var = tk.StringVar()
        self.camera_dropdown = ttk.Combobox(camera_select_frame, textvariable=self.camera_var,
                                           width=15, state='readonly')
        self.camera_dropdown.pack(side=tk.LEFT, padx=(0, 5))
        self.camera_dropdown.bind('<<ComboboxSelected>>', self.on_camera_changed)

        ttk.Button(camera_select_frame, text="Refresh", width=8,
                  command=self.refresh_cameras).pack(side=tk.LEFT)

        # Camera control buttons
        self.start_camera_btn = ttk.Button(controls_frame, text="Start Camera",
                                           command=self.toggle_camera)
        self.start_camera_btn.grid(row=1, column=0, padx=5, pady=(5, 0))

        self.capture_btn = ttk.Button(controls_frame, text="Capture & Scan",
                                      command=self.capture_and_scan, state=tk.DISABLED)
        self.capture_btn.grid(row=1, column=1, padx=5, pady=(5, 0))

        # Manual search
        search_frame = ttk.LabelFrame(left_panel, text="Manual Search", padding="10")
        search_frame.pack(pady=10, fill=tk.X)

        ttk.Label(search_frame, text="Card Name:").grid(row=0, column=0, sticky=tk.W)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.grid(row=0, column=1, padx=5)
        self.search_entry.bind('<Return>', lambda e: self.manual_search())

        self.search_btn = ttk.Button(search_frame, text="Search",
                                     command=self.manual_search)
        self.search_btn.grid(row=0, column=2, padx=5)

        # Status
        self.status_label = ttk.Label(left_panel, text="Status: Ready",
                                      font=('Arial', 10), foreground='green')
        self.status_label.pack(pady=5)

        # Right panel - Results
        right_panel = ttk.Frame(main_container)
        right_panel.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(2, weight=1)  # Results listbox row
        right_panel.rowconfigure(4, weight=1)  # Card info row

        # Search results
        results_label = ttk.Label(right_panel, text="Search Results",
                                  font=('Arial', 12, 'bold'))
        results_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        # Filter box for results
        filter_frame = ttk.Frame(right_panel)
        filter_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.filter_entry = ttk.Entry(filter_frame, width=30)
        self.filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.filter_entry.bind('<KeyRelease>', self.filter_results)

        clear_filter_btn = ttk.Button(filter_frame, text="Clear", width=8,
                                      command=self.clear_filter)
        clear_filter_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Results listbox
        results_frame = ttk.Frame(right_panel)
        results_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        self.results_listbox = tk.Listbox(results_frame, height=10, font=('Courier', 10))
        self.results_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.results_listbox.bind('<<ListboxSelect>>', self.on_result_select)

        results_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL,
                                         command=self.results_listbox.yview)
        results_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.results_listbox.config(yscrollcommand=results_scrollbar.set)

        # Card information display
        info_label = ttk.Label(right_panel, text="Card Information",
                              font=('Arial', 12, 'bold'))
        info_label.grid(row=3, column=0, sticky=tk.W, pady=(10, 5))

        # Container for image and text side by side
        info_container = ttk.Frame(right_panel)
        info_container.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        info_container.columnconfigure(1, weight=1)
        info_container.rowconfigure(0, weight=1)

        # Card image display
        self.card_image_label = ttk.Label(info_container, text="")
        self.card_image_label.grid(row=0, column=0, sticky=(tk.N, tk.W), padx=(0, 10))

        # Card text information
        self.info_text = scrolledtext.ScrolledText(info_container, height=25,
                                                   font=('Courier', 9), wrap=tk.WORD)
        self.info_text.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Action buttons
        action_frame = ttk.Frame(right_panel)
        action_frame.grid(row=5, column=0, pady=10)

        self.save_btn = ttk.Button(action_frame, text="Save Card Data",
                                   command=self.save_card_data, state=tk.DISABLED)
        self.save_btn.grid(row=0, column=0, padx=5)

        self.clear_btn = ttk.Button(action_frame, text="Clear Results",
                                    command=self.clear_results)
        self.clear_btn.grid(row=0, column=1, padx=5)

        # Populate camera dropdown after all UI elements are created
        self.refresh_cameras()

    def toggle_camera(self):
        """Start or stop the camera"""
        if not self.camera_running:
            if self.camera.start():
                self.camera_running = True
                self.start_camera_btn.config(text="Stop Camera")
                self.capture_btn.config(state=tk.NORMAL)
                self.update_status("Camera started", "green")
                self.update_camera_feed()
            else:
                self.update_status("Failed to start camera", "red")
                messagebox.showerror("Error", "Could not start camera. Please check if a camera is connected.")
        else:
            self.camera.stop()
            self.camera_running = False
            self.start_camera_btn.config(text="Start Camera")
            self.capture_btn.config(state=tk.DISABLED)
            self.camera_canvas.delete("all")
            self.update_status("Camera stopped", "orange")

    def refresh_cameras(self):
        """Refresh the list of available cameras"""
        self.update_status("Detecting cameras...", "blue")
        available = CameraCapture.list_available_cameras()

        if available:
            camera_options = [f"Camera {i}" for i in available]
            self.camera_dropdown['values'] = camera_options

            # Select current camera or first available
            if self.camera.camera_index in available:
                self.camera_var.set(f"Camera {self.camera.camera_index}")
            else:
                self.camera_var.set(camera_options[0])
                self.camera.camera_index = available[0]

            self.update_status(f"Found {len(available)} camera(s)", "green")
        else:
            self.camera_dropdown['values'] = ["No cameras found"]
            self.camera_var.set("No cameras found")
            self.update_status("No cameras detected", "red")

    def on_camera_changed(self, event):
        """Handle camera selection change"""
        selected = self.camera_var.get()

        if "Camera" not in selected:
            return

        # Extract camera index from "Camera X"
        try:
            camera_index = int(selected.split()[-1])

            if camera_index != self.camera.camera_index:
                self.update_status(f"Switching to Camera {camera_index}...", "blue")

                if self.camera.switch_camera(camera_index):
                    self.update_status(f"Switched to Camera {camera_index}", "green")
                else:
                    self.update_status(f"Failed to switch camera", "red")
                    messagebox.showerror("Error", f"Could not switch to Camera {camera_index}")

        except (ValueError, IndexError) as e:
            print(f"Error parsing camera index: {e}")

    def update_camera_feed(self):
        """Update the camera feed in the canvas"""
        if self.camera_running:
            frame = self.camera.read_frame()
            if frame is not None:
                self.current_frame = frame
                # Convert to RGB for display
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Resize to fit canvas (16:9 aspect ratio)
                rgb_frame = cv2.resize(rgb_frame, (640, 360))
                # Convert to PIL Image
                img = Image.fromarray(rgb_frame)
                # Convert to ImageTk
                imgtk = ImageTk.PhotoImage(image=img)
                # Update canvas
                self.camera_canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
                self.camera_canvas.imgtk = imgtk  # Keep a reference

            # Schedule next update
            self.root.after(30, self.update_camera_feed)

    def capture_and_scan(self):
        """Capture image from camera and scan for card"""
        if not self.camera_running:
            return

        self.update_status("Capturing image...", "blue")

        # Capture image
        captured_frame = self.camera.capture_image()
        if captured_frame is None:
            self.update_status("Failed to capture image", "red")
            return

        # Process in background thread
        thread = threading.Thread(target=self._process_captured_image,
                                 args=(captured_frame,))
        thread.daemon = True
        thread.start()

    def _process_captured_image(self, image):
        """
        Process captured image (runs in background thread)
        Uses both OCR and image hash matching, then shows verification dialog

        Args:
            image: Captured image
        """
        try:
            # Save image for verification
            self.last_captured_image = image.copy()

            # Detect card region
            self.root.after(0, self.update_status, "Detecting card...", "blue")
            card_region = self.camera.detect_card_region(image)

            # Extract just the name region (top 25% of card)
            name_region = self.camera.extract_name_region(card_region)

            # Enhance image
            enhanced = self.camera.enhance_image(name_region)

            # Preprocess for OCR (improved preprocessing)
            self.root.after(0, self.update_status, "Extracting text (OCR)...", "blue")
            preprocessed = self.camera.preprocess_card_image(enhanced)

            # Extract text (with better Tesseract config)
            text = self.ocr.extract_text(preprocessed)
            print(f"\n{'='*60}")
            print(f"[OCR] Raw extracted text:")
            print(f"{text}")
            print(f"{'='*60}\n")
            self.last_ocr_text = text  # Save for potential corrections

            # Extract card info
            card_info = self.ocr.extract_pokemon_info(text)
            card_name = card_info.get('name')
            print(f"[Main] Extracted card name from OCR: '{card_name}'")

            # Try to improve card name using learning system
            if not card_name:
                # Check learned patterns
                learned_name = self.learning.get_learned_card_name(text)
                if learned_name:
                    card_name = learned_name
                    print(f"[Main] Using learned pattern: {card_name}")

            # Try fuzzy matching with cached cards
            if not card_name:
                cache_size = self.learning.get_cache_size()
                if cache_size > 0:
                    print(f"[Main] Trying fuzzy match with cache size: {cache_size}")
                    matches = self.learning.fuzzy_match_card_name(text, threshold=0.3)
                    if matches:
                        card_name = matches[0][0]
                        confidence = matches[0][1]
                        print(f"[Main] Using fuzzy match: {card_name} ({confidence*100:.0f}%)")

            # Try image hash matching
            self.root.after(0, self.update_status, "Matching image hash...", "blue")
            image_match = self.image_matcher.match_card_image(card_region, threshold=15)

            if image_match:
                print(f"[Main] Image match found: {image_match['name']} ({image_match['confidence']:.1f}%)")

            # Show verification dialog
            self.root.after(0, self.update_status, "Review detection results", "blue")
            self.root.after(0, self._show_verification_dialog,
                          card_region, text or "", card_name, image_match)

        except Exception as e:
            self.root.after(0, self.update_status, f"Error: {str(e)}", "red")
            self.root.after(0, messagebox.showerror, "Error", f"An error occurred: {str(e)}")

    def _show_verification_dialog(self, image, ocr_text, ocr_card_name, image_match):
        """
        Show verification dialog with detection results

        Args:
            image: Captured card image
            ocr_text: Full OCR text
            ocr_card_name: Card name extracted from OCR
            image_match: Image hash match results
        """
        show_verification_dialog(
            self.root,
            image,
            ocr_text,
            ocr_card_name,
            image_match,
            on_confirm=self._on_verification_confirm,
            on_correct=self._on_verification_correct,
            on_retry=self._on_verification_retry
        )

    def _on_verification_confirm(self, card_name: str, method: str):
        """
        Handle confirmation from verification dialog

        Args:
            card_name: Confirmed card name
            method: Detection method used ('ocr' or 'image_hash')
        """
        print(f"[Main] Verification confirmed: {card_name} (method: {method})")
        self.update_status(f"Searching for: {card_name}", "blue")

        # Record scan stats
        self.learning.record_scan_stat(method, card_name, True)

        # Search API
        threading.Thread(target=self._search_api,
                        args=(card_name,),
                        kwargs={'ocr_text': self.last_ocr_text},
                        daemon=True).start()

    def _on_verification_correct(self):
        """Handle manual correction request from verification dialog"""
        print("[Main] Manual correction requested")
        self.show_correction_dialog()

    def _on_verification_retry(self):
        """Handle retry request from verification dialog"""
        print("[Main] Retry capture requested")
        self.update_status("Ready to capture again", "green")

    def manual_search(self):
        """Perform manual search using the search entry"""
        card_name = self.search_entry.get().strip()
        if not card_name:
            messagebox.showwarning("Warning", "Please enter a card name")
            return

        self.update_status(f"Searching for: {card_name}", "blue")
        self.last_ocr_text = None  # Clear OCR text for manual searches

        # Search in background thread
        thread = threading.Thread(target=self._search_api, args=(card_name,))
        thread.daemon = True
        thread.start()

    def _search_api(self, card_name: str, ocr_text: str = None):
        """
        Search for card using API (runs in background thread)

        Args:
            card_name: Name of the card to search
            ocr_text: Optional OCR text that was used to extract the card name
        """
        try:
            # Try exact search first
            cards = self.api.search_card_by_name(card_name)

            # If no exact match, try fuzzy search
            if not cards:
                cards = self.api.search_card_fuzzy(card_name)

            if not cards:
                self.root.after(0, self.update_status, "No cards found", "orange")
                self.root.after(0, messagebox.showinfo, "No Results",
                              f"No cards found for '{card_name}'")
                # Record failed search
                scan_type = 'ocr' if ocr_text else 'manual'
                self.learning.record_scan_stat(scan_type, card_name, False)
                return

            # Cache the found cards
            cards_info = [self.api.extract_card_info(card) for card in cards]
            self.learning.cache_multiple_cards(cards_info)

            # If OCR was used, record the pattern
            if ocr_text and cards:
                first_card_name = cards[0].name
                self.learning.record_ocr_pattern(ocr_text, first_card_name, True)

            # Record successful search
            scan_type = 'ocr' if ocr_text else 'manual'
            self.learning.record_scan_stat(scan_type, card_name, True)

            # Update UI with results
            self.root.after(0, self._display_search_results, cards)

        except Exception as e:
            # Handle bytes error messages from SDK
            error_msg = str(e) if not isinstance(e, bytes) else e.decode('utf-8', errors='replace')
            # If str(e) fails, get a simpler error message
            try:
                error_display = str(e)
            except:
                error_display = f"{type(e).__name__}: {repr(e)}"

            self.root.after(0, self.update_status, f"API Error", "red")
            self.root.after(0, messagebox.showerror, "API Error",
                          f"Error searching API. Please check your internet connection.\n\nTechnical details: {error_display}")

    def _display_search_results(self, cards: List):
        """
        Display search results in the listbox

        Args:
            cards: List of Card objects from API
        """
        self.search_results = cards
        self.results_listbox.delete(0, tk.END)

        for card in cards:
            display_text = f"{card.name} - {card.set.name if hasattr(card, 'set') else 'Unknown'} ({card.id})"
            self.results_listbox.insert(tk.END, display_text)

        self.update_status(f"Found {len(cards)} card(s)", "green")

        # Auto-select first result if only one
        if len(cards) == 1:
            self.results_listbox.selection_set(0)
            self.on_result_select(None)

    def on_result_select(self, event):
        """Handle selection of a search result"""
        selection = self.results_listbox.curselection()
        if not selection:
            return

        # Get the display text and find matching card
        display_text = self.results_listbox.get(selection[0])

        # Find the actual card object from search results
        card = None
        for c in self.search_results:
            card_display = f"{c.name} - {c.set.name if hasattr(c, 'set') else 'Unknown'} ({c.id})"
            if card_display == display_text:
                card = c
                break

        if not card:
            return

        # Extract card information
        card_info = self.api.extract_card_info(card)
        self.selected_card = card_info

        # Display card information
        display_text = CardDisplay.format_card_info(card_info)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, display_text)

        # Download and display card image
        self.display_card_image(card_info)

        # Enable save button
        self.save_btn.config(state=tk.NORMAL)

        self.update_status(f"Displaying: {card_info['name']}", "green")

    def display_card_image(self, card_info):
        """Download and display the card image"""
        try:
            image_url = card_info.get('images', {}).get('small')
            if not image_url:
                self.card_image_label.config(image='', text="No image available")
                return

            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            # Convert to PIL Image
            image_data = BytesIO(response.content)
            pil_image = Image.open(image_data)

            # Resize to fit nicely (max height 400px)
            max_height = 400
            aspect_ratio = pil_image.width / pil_image.height
            new_height = max_height
            new_width = int(max_height * aspect_ratio)
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)

            # Update label
            self.card_image_label.config(image=photo, text="")
            self.card_image_label.image = photo  # Keep a reference

        except Exception as e:
            print(f"Error loading card image: {e}")
            self.card_image_label.config(image='', text="Image load failed")

    def save_card_data(self):
        """Save the currently selected card data"""
        if not self.selected_card:
            messagebox.showwarning("Warning", "No card selected")
            return

        try:
            # Save all card information
            saved_files = self.file_manager.save_all_card_info(self.selected_card)

            # Show success message
            file_list = "\n".join([f"- {os.path.basename(path)}" for path in saved_files.values() if path])
            messagebox.showinfo("Success",
                              f"Card data saved successfully!\n\nFiles created:\n{file_list}")

            self.update_status("Card data saved", "green")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save card data: {str(e)}")
            self.update_status(f"Save error: {str(e)}", "red")

    def clear_results(self):
        """Clear all results and reset the UI"""
        self.results_listbox.delete(0, tk.END)
        self.info_text.delete(1.0, tk.END)
        self.search_results = []
        self.selected_card = None
        self.save_btn.config(state=tk.DISABLED)
        self.filter_entry.delete(0, tk.END)
        self.update_status("Results cleared", "orange")

    def filter_results(self, event=None):
        """Filter the search results based on filter text"""
        if not self.search_results:
            return

        filter_text = self.filter_entry.get().lower()

        # Clear current listbox
        self.results_listbox.delete(0, tk.END)

        # Rebuild listbox with filtered results
        for card in self.search_results:
            display_text = f"{card.name} - {card.set.name if hasattr(card, 'set') else 'Unknown'} ({card.id})"

            # Check if filter matches
            if filter_text in display_text.lower():
                self.results_listbox.insert(tk.END, display_text)

    def clear_filter(self):
        """Clear the filter and show all results"""
        self.filter_entry.delete(0, tk.END)
        self.filter_results()

    def update_status(self, message: str, color: str = "black"):
        """
        Update the status label

        Args:
            message: Status message
            color: Color of the text
        """
        self.status_label.config(text=f"Status: {message}", foreground=color)

    def show_statistics(self):
        """Show learning system statistics"""
        stats_text = self.learning.export_statistics()

        # Create statistics window
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Learning System Statistics")
        stats_window.geometry("400x300")

        # Statistics text
        stats_display = scrolledtext.ScrolledText(stats_window, height=15, font=('Courier', 10))
        stats_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        stats_display.insert(1.0, stats_text)
        stats_display.config(state=tk.DISABLED)

        # Close button
        close_btn = ttk.Button(stats_window, text="Close", command=stats_window.destroy)
        close_btn.pack(pady=5)

    def build_card_cache(self):
        """Build card cache by fetching popular cards from API"""
        if not messagebox.askyesno("Build Card Cache",
                                   "This will fetch and cache Pokemon cards from the API to improve fuzzy matching.\n\n"
                                   "This may take a minute. Continue?"):
            return

        self.update_status("Building card cache...", "blue")

        def _build_cache():
            try:
                # Fetch some cards to populate cache
                # We'll search for common Pokemon names
                common_pokemon = [
                    "Pikachu", "Charizard", "Mewtwo", "Blastoise", "Venusaur",
                    "Gengar", "Dragonite", "Snorlax", "Eevee", "Gyarados",
                    "Alakazam", "Machamp", "Arcanine", "Lapras", "Articuno",
                    "Zapdos", "Moltres", "Mew", "Lugia", "Ho-Oh"
                ]

                cached_count = 0
                for pokemon in common_pokemon:
                    try:
                        cards = self.api.search_card_by_name(pokemon)
                        if cards:
                            cards_info = [self.api.extract_card_info(card) for card in cards[:10]]  # Limit to 10 per name
                            self.learning.cache_multiple_cards(cards_info)
                            cached_count += len(cards_info)
                    except:
                        pass  # Skip errors for individual Pokemon

                self.root.after(0, self.update_status, f"Cache built: {cached_count} cards", "green")
                self.root.after(0, messagebox.showinfo, "Success",
                              f"Successfully cached {cached_count} cards!\n\n"
                              f"The scanner will now use fuzzy matching to improve accuracy.")

            except Exception as e:
                self.root.after(0, self.update_status, "Cache build failed", "red")
                self.root.after(0, messagebox.showerror, "Error",
                              f"Failed to build cache: {str(e)}")

        # Run in background
        thread = threading.Thread(target=_build_cache)
        thread.daemon = True
        thread.start()

    def download_card_images(self):
        """Download all Pokemon card images and build perceptual hash database"""
        stats = self.image_matcher.get_database_stats()
        existing = stats.get('downloaded_cards', 0)

        message = (f"This will download Pokemon card images from the API and create "
                  f"a perceptual hash database for image-based matching.\n\n")

        if existing > 0:
            message += f"Current database: {existing} cards\n\n"

        message += ("This process may take 30-60 minutes for all cards.\n"
                   "You can limit the number of cards to download.\n\n"
                   "Continue?")

        if not messagebox.askyesno("Download Card Images", message):
            return

        # Ask for limit
        limit_dialog = tk.Toplevel(self.root)
        limit_dialog.title("Download Limit")
        limit_dialog.geometry("350x150")
        limit_dialog.transient(self.root)
        limit_dialog.grab_set()

        ttk.Label(limit_dialog, text="Number of cards to download:",
                 font=('Arial', 10)).pack(pady=(20, 5))

        limit_var = tk.StringVar(value="500")
        limit_entry = ttk.Entry(limit_dialog, textvariable=limit_var, width=15)
        limit_entry.pack(pady=5)

        ttk.Label(limit_dialog, text="(0 = download all cards)",
                 font=('Arial', 9), foreground='gray').pack()

        def start_download():
            try:
                max_cards = int(limit_var.get())
            except:
                max_cards = 500

            limit_dialog.destroy()
            self._start_card_download(max_cards)

        ttk.Button(limit_dialog, text="Start Download",
                  command=start_download).pack(pady=10)

        # Center dialog
        limit_dialog.update_idletasks()
        x = (limit_dialog.winfo_screenwidth() // 2) - (350 // 2)
        y = (limit_dialog.winfo_screenheight() // 2) - (150 // 2)
        limit_dialog.geometry(f"+{x}+{y}")

    def _start_card_download(self, max_cards: int):
        """Start downloading cards in background with progress"""
        # Create progress dialog
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Downloading Cards")
        progress_window.geometry("500x200")
        progress_window.transient(self.root)

        ttk.Label(progress_window, text="Downloading Pokemon Card Images",
                 font=('Arial', 12, 'bold')).pack(pady=10)

        progress_var = tk.StringVar(value="Initializing...")
        progress_label = ttk.Label(progress_window, textvariable=progress_var,
                                   font=('Arial', 10))
        progress_label.pack(pady=5)

        progress_bar = ttk.Progressbar(progress_window, length=400, mode='determinate')
        progress_bar.pack(pady=20)

        card_label = ttk.Label(progress_window, text="", font=('Arial', 9),
                              foreground='gray')
        card_label.pack()

        # Center window
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (200 // 2)
        progress_window.geometry(f"+{x}+{y}")

        self.update_status("Downloading card images...", "blue")

        def progress_callback(current, total, card_name):
            progress = int((current / total) * 100)
            progress_var.set(f"Progress: {current}/{total} cards ({progress}%)")
            progress_bar['value'] = progress
            card_label.config(text=f"Current: {card_name}")

        def download_thread():
            try:
                downloaded = self.image_matcher.download_all_cards(
                    max_cards=max_cards,
                    callback=lambda c, t, n: self.root.after(0, progress_callback, c, t, n)
                )

                self.root.after(0, progress_window.destroy)
                self.root.after(0, self.update_status,
                              f"Downloaded {downloaded} cards", "green")
                self.root.after(0, messagebox.showinfo, "Success",
                              f"Successfully downloaded and hashed {downloaded} cards!\n\n"
                              f"The scanner will now use image matching for better accuracy.")

            except Exception as e:
                self.root.after(0, progress_window.destroy)
                self.root.after(0, self.update_status, "Download failed", "red")
                self.root.after(0, messagebox.showerror, "Error",
                              f"Failed to download cards: {str(e)}")

        thread = threading.Thread(target=download_thread)
        thread.daemon = True
        thread.start()

    def show_image_hash_stats(self):
        """Show image hash database statistics"""
        stats = self.image_matcher.get_database_stats()

        total = stats.get('total_cards', 0)
        downloaded = stats.get('downloaded_cards', 0)
        sets = stats.get('total_sets', 0)
        db_path = stats.get('database_path', 'Unknown')

        message = f"""Image Hash Database Statistics:

Total Cards: {total}
Downloaded Cards: {downloaded}
Total Sets: {sets}

Database Path: {db_path}

Status: {'✓ Ready' if downloaded > 0 else '❌ No cards downloaded'}
"""

        if downloaded == 0:
            message += "\n💡 Use 'Download Card Images' to build the database."

        messagebox.showinfo("Image Hash Statistics", message)

    def show_correction_dialog(self):
        """Show dialog to correct the last OCR scan"""
        if not self.last_ocr_text:
            messagebox.showinfo("No Scan to Correct",
                              "No recent OCR scan to correct. Scan a card first.")
            return

        # Create correction dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Correct OCR Scan")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # OCR text display
        ttk.Label(dialog, text="OCR Text:", font=('Arial', 10, 'bold')).pack(pady=(10, 5))
        ocr_display = scrolledtext.ScrolledText(dialog, height=5, font=('Courier', 9))
        ocr_display.pack(fill=tk.X, padx=10, pady=5)
        ocr_display.insert(1.0, self.last_ocr_text)
        ocr_display.config(state=tk.DISABLED)

        # Correction input
        ttk.Label(dialog, text="Correct Card Name:", font=('Arial', 10, 'bold')).pack(pady=(10, 5))
        correction_entry = ttk.Entry(dialog, width=40, font=('Arial', 10))
        correction_entry.pack(padx=10, pady=5)
        correction_entry.focus()

        # Suggestion from fuzzy matching
        if self.learning.get_cache_size() > 0:
            matches = self.learning.fuzzy_match_card_name(self.last_ocr_text, threshold=0.3)
            if matches:
                ttk.Label(dialog, text="Suggestions:", font=('Arial', 9)).pack(pady=(10, 5))

                suggestions_frame = ttk.Frame(dialog)
                suggestions_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

                suggestions_list = tk.Listbox(suggestions_frame, height=5)
                suggestions_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

                scrollbar = ttk.Scrollbar(suggestions_frame, orient=tk.VERTICAL,
                                        command=suggestions_list.yview)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                suggestions_list.config(yscrollcommand=scrollbar.set)

                for name, score in matches[:10]:
                    suggestions_list.insert(tk.END, f"{name} ({score*100:.0f}%)")

                def use_suggestion(event=None):
                    selection = suggestions_list.curselection()
                    if selection:
                        text = suggestions_list.get(selection[0])
                        card_name = text.split(' (')[0]  # Extract name before score
                        correction_entry.delete(0, tk.END)
                        correction_entry.insert(0, card_name)

                suggestions_list.bind('<Double-Button-1>', use_suggestion)

        def submit_correction():
            corrected_name = correction_entry.get().strip()
            if not corrected_name:
                messagebox.showwarning("Invalid", "Please enter a card name")
                return

            # Record the correction
            self.learning.record_user_correction(self.last_ocr_text, corrected_name)
            self.learning.record_scan_stat('correction', corrected_name, True)

            messagebox.showinfo("Success",
                              f"Correction recorded!\n\nThe system will now recognize:\n"
                              f"'{self.last_ocr_text[:50]}...'\n\nas: {corrected_name}")

            dialog.destroy()

            # Optionally search for the corrected card
            if messagebox.askyesno("Search", "Would you like to search for this card?"):
                self.search_entry.delete(0, tk.END)
                self.search_entry.insert(0, corrected_name)
                self.manual_search()

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        submit_btn = ttk.Button(button_frame, text="Submit Correction",
                               command=submit_correction)
        submit_btn.grid(row=0, column=0, padx=5)

        cancel_btn = ttk.Button(button_frame, text="Cancel",
                               command=dialog.destroy)
        cancel_btn.grid(row=0, column=1, padx=5)

        # Bind Enter key
        correction_entry.bind('<Return>', lambda e: submit_correction())

    def on_closing(self):
        """Handle window closing"""
        if self.camera_running:
            self.camera.stop()
        self.root.destroy()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = PokemonCardScannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
