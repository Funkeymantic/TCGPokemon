"""
Camera Capture Module
Handles camera access and image capture for Pokemon card scanning
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict
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

    @staticmethod
    def list_available_cameras(max_test: int = 10) -> List[Dict]:
        """
        List all available cameras with their names

        Args:
            max_test: Maximum number of camera indices to test (default: 10)

        Returns:
            List of dictionaries with 'index' and 'name' keys
        """
        available_cameras = []

        for i in range(max_test):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # Try to get camera name/description
                name = CameraCapture._get_camera_name(i, cap)
                available_cameras.append({
                    'index': i,
                    'name': name
                })
                cap.release()

        return available_cameras

    @staticmethod
    def _get_camera_name(index: int, cap: cv2.VideoCapture) -> str:
        """
        Get a descriptive name for a camera

        Args:
            index: Camera index
            cap: OpenCV VideoCapture object

        Returns:
            Descriptive camera name
        """
        # Try to get backend name
        backend = cap.getBackendName() if hasattr(cap, 'getBackendName') else None

        # Get basic camera properties to help identify it
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

        # Try platform-specific methods to get camera name
        try:
            import platform
            if platform.system() == 'Windows':
                # On Windows, try to get camera name from registry/WMI
                camera_name = CameraCapture._get_windows_camera_name(index)
                if camera_name:
                    return camera_name
        except:
            pass

        # Build descriptive name based on what we know
        if index == 0:
            return f"Camera 0 - Built-in ({int(width)}x{int(height)})"
        else:
            return f"Camera {index} - External ({int(width)}x{int(height)})"

    @staticmethod
    def _get_windows_camera_name(index: int) -> Optional[str]:
        """
        Get camera name on Windows using WMI

        Args:
            index: Camera index

        Returns:
            Camera name or None if not found
        """
        try:
            import subprocess
            # Use PowerShell to get camera names
            cmd = 'powershell "Get-PnpDevice -Class Camera | Select-Object -Property FriendlyName | Format-Table -HideTableHeaders"'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=2)

            if result.returncode == 0:
                lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                if 0 <= index < len(lines):
                    return lines[index]
        except:
            pass

        return None

    def switch_camera(self, camera_index: int) -> bool:
        """
        Switch to a different camera

        Args:
            camera_index: Index of the new camera

        Returns:
            True if switch was successful, False otherwise
        """
        was_running = self.is_running

        # Stop current camera
        if was_running:
            self.stop()

        # Update camera index
        self.camera_index = camera_index

        # Restart if it was running
        if was_running:
            return self.start()

        return True

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

        # Increase contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Denoise first
        denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)

        # Apply bilateral filter to preserve edges while smoothing
        bilateral = cv2.bilateralFilter(denoised, 9, 75, 75)

        # Sharpen the image
        kernel_sharpen = np.array([[-1, -1, -1],
                                   [-1,  9, -1],
                                   [-1, -1, -1]])
        sharpened = cv2.filter2D(bilateral, -1, kernel_sharpen)

        # Apply Otsu's thresholding for better text separation
        _, thresh = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Dilate slightly to make text thicker and more readable
        kernel = np.ones((2, 2), np.uint8)
        dilated = cv2.dilate(thresh, kernel, iterations=1)

        return dilated

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

    def extract_name_region(self, image: np.ndarray) -> np.ndarray:
        """
        Extract the top portion of the card where the name typically appears

        Args:
            image: Full card image

        Returns:
            Cropped region with card name
        """
        height, width = image.shape[:2]
        # Card name is typically in the top 25% of the card
        name_region = image[0:int(height * 0.25), 0:width]
        return name_region

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
