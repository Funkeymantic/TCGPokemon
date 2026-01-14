"""
Verification Dialog Module
Shows captured card details and allows user to verify/correct before searching
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
from typing import Optional, Callable, Dict


class VerificationDialog:
    """Dialog for verifying captured card information before searching"""

    def __init__(self, parent, image: np.ndarray, ocr_text: str,
                 ocr_card_name: Optional[str],
                 image_match: Optional[Dict],
                 on_confirm: Callable,
                 on_correct: Callable,
                 on_retry: Callable):
        """
        Initialize verification dialog

        Args:
            parent: Parent window
            image: Captured card image
            ocr_text: Full OCR extracted text
            ocr_card_name: Extracted card name from OCR
            image_match: Dictionary with image hash match results
            on_confirm: Callback when user confirms
            on_correct: Callback when user wants to manually correct
            on_retry: Callback when user wants to retry capture
        """
        self.parent = parent
        self.image = image
        self.ocr_text = ocr_text
        self.ocr_card_name = ocr_card_name
        self.image_match = image_match
        self.on_confirm = on_confirm
        self.on_correct = on_correct
        self.on_retry = on_retry

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Verify Card Detection")
        self.dialog.geometry("900x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (700 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the verification dialog UI"""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Card Detection Results",
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))

        # Content area (horizontal split)
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Left side - Image preview
        left_frame = ttk.LabelFrame(content_frame, text="Captured Image", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.image_canvas = tk.Canvas(left_frame, width=400, height=500, bg='white')
        self.image_canvas.pack()

        # Display captured image
        self._display_image()

        # Right side - Detection results
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # OCR Results section
        ocr_frame = ttk.LabelFrame(right_frame, text="OCR Detection", padding="10")
        ocr_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        ttk.Label(ocr_frame, text="Detected Card Name:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)

        self.ocr_name_label = ttk.Label(ocr_frame, text=self.ocr_card_name or "❌ No card name detected",
                                       font=('Arial', 11),
                                       foreground='green' if self.ocr_card_name else 'red')
        self.ocr_name_label.pack(anchor=tk.W, pady=(5, 10))

        ttk.Label(ocr_frame, text="Full OCR Text:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)

        ocr_text_frame = ttk.Frame(ocr_frame)
        ocr_text_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        ocr_scrollbar = ttk.Scrollbar(ocr_text_frame)
        ocr_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.ocr_text_widget = tk.Text(ocr_text_frame, height=6, wrap=tk.WORD,
                                       yscrollcommand=ocr_scrollbar.set,
                                       font=('Courier', 9))
        self.ocr_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ocr_scrollbar.config(command=self.ocr_text_widget.yview)

        self.ocr_text_widget.insert('1.0', self.ocr_text or "No text extracted")
        self.ocr_text_widget.config(state=tk.DISABLED)

        # Image Match Results section
        match_frame = ttk.LabelFrame(right_frame, text="Image Hash Match", padding="10")
        match_frame.pack(fill=tk.BOTH, expand=False)

        if self.image_match:
            # Match found
            ttk.Label(match_frame, text="✓ Match Found!", font=('Arial', 10, 'bold'),
                     foreground='green').pack(anchor=tk.W)

            info_text = f"""
Card Name: {self.image_match.get('name', 'Unknown')}
Set: {self.image_match.get('set_name', 'Unknown')}
Number: {self.image_match.get('number', 'Unknown')}
Rarity: {self.image_match.get('rarity', 'Unknown')}

Confidence: {self.image_match.get('confidence', 0):.1f}%
Hash Distance: {self.image_match.get('distance', 0)}
            """.strip()

            match_info = ttk.Label(match_frame, text=info_text, font=('Arial', 9),
                                  justify=tk.LEFT)
            match_info.pack(anchor=tk.W, pady=(5, 0))
        else:
            # No match
            ttk.Label(match_frame, text="❌ No image match found", font=('Arial', 10, 'bold'),
                     foreground='red').pack(anchor=tk.W)

            ttk.Label(match_frame, text="Try downloading card images first\n(Learning > Download Card Images)",
                     font=('Arial', 9), foreground='gray').pack(anchor=tk.W, pady=(5, 0))

        # Recommendation section
        recommendation_frame = ttk.Frame(right_frame)
        recommendation_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Separator(recommendation_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 10))

        ttk.Label(recommendation_frame, text="Recommendation:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)

        recommendation = self._get_recommendation()
        rec_label = ttk.Label(recommendation_frame, text=recommendation,
                             font=('Arial', 9), wraplength=350)
        rec_label.pack(anchor=tk.W, pady=(5, 0))

        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))

        ttk.Button(button_frame, text="✓ Confirm & Search",
                  command=self._handle_confirm, style='Accent.TButton',
                  width=20).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="✏️ Manual Correction",
                  command=self._handle_correct,
                  width=20).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="🔄 Retry Capture",
                  command=self._handle_retry,
                  width=20).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="❌ Cancel",
                  command=self.dialog.destroy,
                  width=15).pack(side=tk.LEFT, padx=5)

        # Keyboard shortcuts
        self.dialog.bind('<Return>', lambda e: self._handle_confirm())
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())

    def _display_image(self):
        """Display the captured image in the canvas"""
        try:
            # Convert BGR to RGB
            if len(self.image.shape) == 3 and self.image.shape[2] == 3:
                image_rgb = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = self.image

            # Convert to PIL Image
            pil_image = Image.fromarray(image_rgb)

            # Resize to fit canvas while maintaining aspect ratio
            canvas_width = 400
            canvas_height = 500

            img_width, img_height = pil_image.size
            ratio = min(canvas_width / img_width, canvas_height / img_height)
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)

            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert to PhotoImage and display
            photo = ImageTk.PhotoImage(pil_image)
            self.image_canvas.create_image(canvas_width // 2, canvas_height // 2,
                                          anchor=tk.CENTER, image=photo)
            self.image_canvas.image = photo  # Keep reference

        except Exception as e:
            print(f"[VerificationDialog] Error displaying image: {e}")

    def _get_recommendation(self) -> str:
        """Get recommendation text based on detection results"""
        if self.image_match and self.image_match.get('confidence', 0) > 80:
            return "✓ High confidence match! Click 'Confirm & Search' to proceed."

        elif self.image_match and self.image_match.get('confidence', 0) > 50:
            return "⚠ Moderate confidence match. Verify the card name is correct before confirming."

        elif self.ocr_card_name:
            return "ℹ Using OCR detection. The card name may need manual correction if not accurate."

        else:
            return "❌ No reliable detection. Please use 'Manual Correction' to enter the card name."

    def _handle_confirm(self):
        """Handle confirm button click"""
        # Determine which card name to use
        if self.image_match and self.image_match.get('confidence', 0) > 50:
            card_name = self.image_match.get('name')
            method = 'image_hash'
        elif self.ocr_card_name:
            card_name = self.ocr_card_name
            method = 'ocr'
        else:
            messagebox.showwarning("No Detection",
                                  "No card detected. Please use Manual Correction or Retry Capture.")
            return

        self.dialog.destroy()
        self.on_confirm(card_name, method)

    def _handle_correct(self):
        """Handle manual correction button click"""
        self.dialog.destroy()
        self.on_correct()

    def _handle_retry(self):
        """Handle retry button click"""
        self.dialog.destroy()
        self.on_retry()


def show_verification_dialog(parent, image: np.ndarray, ocr_text: str,
                            ocr_card_name: Optional[str],
                            image_match: Optional[Dict],
                            on_confirm: Callable,
                            on_correct: Callable,
                            on_retry: Callable):
    """
    Show verification dialog

    Args:
        parent: Parent window
        image: Captured card image
        ocr_text: Full OCR text
        ocr_card_name: Extracted card name
        image_match: Image hash match results
        on_confirm: Callback(card_name, method) when confirmed
        on_correct: Callback when manual correction requested
        on_retry: Callback when retry requested
    """
    VerificationDialog(parent, image, ocr_text, ocr_card_name, image_match,
                      on_confirm, on_correct, on_retry)
