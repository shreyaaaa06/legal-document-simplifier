#ocr.py
import pytesseract
from PIL import Image
import cv2
import numpy as np
import os

class OCRProcessor:
    def __init__(self):
        # Configure tesseract path if needed (Windows)
        pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'
        pass
    
    def extract_text_from_image(self, image_path):
        """Extract text from image using OCR"""
        try:
            # Open and preprocess image
            image = Image.open(image_path)
            
            # Convert to OpenCV format for preprocessing
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Preprocess image for better OCR
            processed_image = self._preprocess_image(cv_image)
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(processed_image, config='--psm 6')
            
            return text.strip()
        
        except Exception as e:
            raise Exception(f"OCR failed: {str(e)}")
    
    def _preprocess_image(self, image):
        """Preprocess image for better OCR results"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Remove noise
        denoised = cv2.medianBlur(gray, 5)
        
        # Threshold the image
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    def is_image_file(self, filename):
        """Check if file is a supported image format"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        return any(filename.lower().endswith(ext) for ext in image_extensions)