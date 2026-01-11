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

        # State
        self.camera_running = False
        self.current_frame = None
        self.selected_card = None
        self.search_results = []

        # Setup UI
        self.setup_ui()

        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        """Setup the user interface"""
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

        self.start_camera_btn = ttk.Button(controls_frame, text="Start Camera",
                                           command=self.toggle_camera)
        self.start_camera_btn.grid(row=0, column=0, padx=5)

        self.capture_btn = ttk.Button(controls_frame, text="Capture & Scan",
                                      command=self.capture_and_scan, state=tk.DISABLED)
        self.capture_btn.grid(row=0, column=1, padx=5)

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

        Args:
            image: Captured image
        """
        try:
            # Detect card region
            self.root.after(0, self.update_status, "Detecting card...", "blue")
            card_region = self.camera.detect_card_region(image)

            # Extract just the name region (top 25% of card)
            name_region = self.camera.extract_name_region(card_region)

            # Enhance image
            enhanced = self.camera.enhance_image(name_region)

            # Preprocess for OCR (improved preprocessing)
            self.root.after(0, self.update_status, "Extracting text...", "blue")
            preprocessed = self.camera.preprocess_card_image(enhanced)

            # Extract text (with better Tesseract config)
            text = self.ocr.extract_text(preprocessed)
            print(f"OCR extracted text: '{text}'")

            if not text:
                self.root.after(0, self.update_status, "No text detected", "orange")
                self.root.after(0, messagebox.showwarning, "Warning",
                              "Could not extract text from the image. Try adjusting the card position.")
                return

            # Extract card info
            card_info = self.ocr.extract_pokemon_info(text)
            card_name = card_info.get('name')

            if not card_name:
                self.root.after(0, self.update_status, "Could not identify card name", "orange")
                self.root.after(0, messagebox.showwarning, "Warning",
                              f"Could not identify card name. OCR Text:\n{text[:200]}")
                return

            # Search API
            self.root.after(0, self.update_status, f"Searching for: {card_name}", "blue")
            self._search_api(card_name)

        except Exception as e:
            self.root.after(0, self.update_status, f"Error: {str(e)}", "red")
            self.root.after(0, messagebox.showerror, "Error", f"An error occurred: {str(e)}")

    def manual_search(self):
        """Perform manual search using the search entry"""
        card_name = self.search_entry.get().strip()
        if not card_name:
            messagebox.showwarning("Warning", "Please enter a card name")
            return

        self.update_status(f"Searching for: {card_name}", "blue")

        # Search in background thread
        thread = threading.Thread(target=self._search_api, args=(card_name,))
        thread.daemon = True
        thread.start()

    def _search_api(self, card_name: str):
        """
        Search for card using API (runs in background thread)

        Args:
            card_name: Name of the card to search
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
                return

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
