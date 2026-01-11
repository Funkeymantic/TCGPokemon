"""
Camera Capture Module
Handles camera access and image capture for Pokemon card scanning
"""

import cv2
import numpy as np
from typing import Optional, Tuple
from PIL import Image


class CameraCapture:
    """Handles camera operations for card scanning"""

    def __init__(self, camera_index: int = 0):
        """
        Initialize camera capture

        Args:
            camera_index: Index of the camera to use (default: 0)
        """
        self.camera_index = camera_index
        self.cap = None
        self.is_running = False

    def start(self) -> bool:
        """
        Start the camera capture

        Returns:
            True if camera started successfully, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                print("Error: Could not open camera")
                return False

            # Set camera properties for better quality
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)

            self.is_running = True
            print("✓ Camera started successfully")
            return True
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False

    def stop(self):
        """Stop the camera capture and release resources"""
        if self.cap:
            self.cap.release()
            self.is_running = False
            print("✓ Camera stopped")

    def read_frame(self) -> Optional[np.ndarray]:
        """
        Read a single frame from the camera

        Returns:
            Frame as numpy array or None if failed
        """
        if not self.is_running or not self.cap:
            return None

        ret, frame = self.cap.read()
        if ret:
            return frame
        return None

    def capture_image(self) -> Optional[np.ndarray]:
        """
        Capture a single image from the camera

        Returns:
            Captured image as numpy array or None if failed
        """
        frame = self.read_frame()
        if frame is not None:
            print("✓ Image captured")
        return frame

    def preprocess_card_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess the card image for better OCR results

        Args:
            image: Input image as numpy array

        Returns:
            Preprocessed image
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply adaptive thresholding for better text contrast
        processed = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Denoise
        denoised = cv2.fastNlMeansDenoising(processed, None, 10, 7, 21)

        return denoised

    def detect_card_region(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect and extract the card region from the image

        Args:
            image: Input image as numpy array

        Returns:
            Cropped card region or original image if detection fails
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Edge detection
            edges = cv2.Canny(blurred, 50, 150)

            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                return image

            # Find the largest contour (assumed to be the card)
            largest_contour = max(contours, key=cv2.contourArea)

            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(largest_contour)

            # Check if the contour is large enough to be a card
            image_area = image.shape[0] * image.shape[1]
            contour_area = w * h

            if contour_area > image_area * 0.1:  # Card should be at least 10% of image
                # Add some padding
                padding = 10
                x = max(0, x - padding)
                y = max(0, y - padding)
                w = min(image.shape[1] - x, w + 2 * padding)
                h = min(image.shape[0] - y, h + 2 * padding)

                # Crop the card region
                card_region = image[y:y+h, x:x+w]
                return card_region

            return image
        except Exception as e:
            print(f"Error detecting card region: {e}")
            return image

    def enhance_image(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance image quality for better OCR

        Args:
            image: Input image as numpy array

        Returns:
            Enhanced image
        """
        # Increase contrast
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

        # Sharpen
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)

        return sharpened

    def save_image(self, image: np.ndarray, filepath: str) -> bool:
        """
        Save image to file

        Args:
            image: Image to save
            filepath: Path to save the image

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            cv2.imwrite(filepath, image)
            print(f"✓ Image saved to {filepath}")
            return True
        except Exception as e:
            print(f"Error saving image: {e}")
            return False

    def get_pil_image(self, cv_image: np.ndarray) -> Image.Image:
        """
        Convert OpenCV image to PIL Image

        Args:
            cv_image: OpenCV image (BGR)

        Returns:
            PIL Image (RGB)
        """
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb_image)

    def draw_overlay_text(self, image: np.ndarray, text: str,
                         position: Tuple[int, int] = (10, 30),
                         font_scale: float = 1.0,
                         color: Tuple[int, int, int] = (0, 255, 0),
                         thickness: int = 2) -> np.ndarray:
        """
        Draw text overlay on image

        Args:
            image: Image to draw on
            text: Text to display
            position: (x, y) position of text
            font_scale: Font size scale
            color: Text color (BGR)
            thickness: Text thickness

        Returns:
            Image with text overlay
        """
        overlay = image.copy()
        cv2.putText(overlay, text, position, cv2.FONT_HERSHEY_SIMPLEX,
                   font_scale, color, thickness, cv2.LINE_AA)
        return overlay
