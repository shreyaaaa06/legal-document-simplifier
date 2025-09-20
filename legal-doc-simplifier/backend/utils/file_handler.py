#file_handler.py
import os
import uuid
from werkzeug.utils import secure_filename
from docx import Document as DocxDocument
from PyPDF2 import PdfReader
from backend.utils.ocr import OCRProcessor

class FileHandler:
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        self.ocr_processor = OCRProcessor()
        self.allowed_extensions = {'pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif'}
    
    def is_allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def save_file(self, file):
        """Save uploaded file and return file path"""
        if not file or not self.is_allowed_file(file.filename):
            raise ValueError("Invalid file type")
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(self.upload_folder, unique_filename)
        
        # Ensure upload directory exists
        os.makedirs(self.upload_folder, exist_ok=True)
        
        # Save file
        file.save(file_path)
        return file_path
    
    def extract_text(self, file_path):
        """Extract text from various file formats"""
        file_extension = file_path.rsplit('.', 1)[1].lower()
        
        try:
            if file_extension == 'pdf':
                return self._extract_from_pdf(file_path)
            elif file_extension in ['docx', 'doc']:
                return self._extract_from_docx(file_path)
            elif file_extension in ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif']:
                return self._extract_from_image(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
        
        except Exception as e:
            raise Exception(f"Text extraction failed: {str(e)}")
    
    def _extract_from_pdf(self, file_path):
        """Extract text from PDF file"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            
            # If PDF text extraction failed, try OCR
            if not text.strip():
                text = self._extract_with_ocr_fallback(file_path)
            
            return text.strip()
        
        except Exception as e:
            # Fallback to OCR if PDF reading fails
            return self._extract_with_ocr_fallback(file_path)
    
    def _extract_from_docx(self, file_path):
        """Extract text from DOCX file"""
        doc = DocxDocument(file_path)
        text = ""
        
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    
    def _extract_from_image(self, file_path):
        """Extract text from image using OCR"""
        return self.ocr_processor.extract_text_from_image(file_path)
    
    def _extract_with_ocr_fallback(self, file_path):
        """Fallback OCR method for PDFs that can't be read directly"""
        try:
            # For now, just return empty string - would need PDF to image conversion
            # This could be implemented with pdf2image library
            return ""
        except:
            return ""
    
    def cleanup_file(self, file_path):
        """Delete uploaded file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Failed to cleanup file {file_path}: {str(e)}")
    
    def get_file_info(self, file_path):
        """Get file information"""
        if not os.path.exists(file_path):
            return None
        
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'extension': file_path.rsplit('.', 1)[1].lower() if '.' in file_path else None
        }