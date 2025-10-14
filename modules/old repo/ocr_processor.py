# ============================================================================
# modules/ocr_processor.py
# ============================================================================
"""
Procesador OCR multi-motor
"""
import cv2
import numpy as np
from pathlib import Path
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import PyPDF2
import os

from .config import Config
from .utils import find_tesseract, find_poppler

class OCRProcessor:
    """Procesador OCR con soporte para múltiples motores"""
    
    def __init__(self, config: Config):
        self.config = config
        self.engine = "auto"
        self.paddle_ocr = None
        
        # Configurar Tesseract
        tesseract_path = find_tesseract()
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Configurar Poppler
        self.poppler_path = find_poppler()
        
        # Inicializar PaddleOCR si está disponible
        if self.config.HAS_PADDLE:
            self.init_paddle()
    
    def init_paddle(self):
        """Inicializa PaddleOCR"""
        try:
            from paddleocr import PaddleOCR
            self.paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                lang='latin',
                use_gpu=False,
                show_log=False
            )
        except Exception as e:
            print(f"No se pudo inicializar PaddleOCR: {e}")
            self.paddle_ocr = None
    
    def set_engine(self, engine):
        """Configura el motor OCR a usar"""
        self.engine = engine
    
    def process_file(self, file_path):
        """Procesa un archivo con OCR"""
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.pdf':
            return self.process_pdf(file_path)
        else:
            return self.process_image(file_path)
    
    def process_pdf(self, pdf_path):
        """Procesa un archivo PDF"""
        # Primero intentar extraer texto embebido
        embedded_text = self.extract_embedded_text(pdf_path)
        if embedded_text and len(embedded_text) > 100:
            return {
                "text": embedded_text,
                "confidence": 0.99,
                "engine": "embedded"
            }
        
        # Si no hay texto embebido, convertir a imágenes y hacer OCR
        try:
            kwargs = {"dpi": self.config.OCR_DPI}
            if self.poppler_path:
                kwargs["poppler_path"] = self.poppler_path
            
            pages = convert_from_path(str(pdf_path), **kwargs)
            
            all_text = []
            all_confidence = []
            
            for page in pages:
                # Convertir PIL a OpenCV
                img = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
                result = self.process_image_data(img)
                
                if result:
                    all_text.append(result["text"])
                    all_confidence.append(result["confidence"])
            
            if all_text:
                return {
                    "text": "\n".join(all_text),
                    "confidence": np.mean(all_confidence) if all_confidence else 0,
                    "engine": result.get("engine", "unknown")
                }
                
        except Exception as e:
            print(f"Error procesando PDF: {e}")
        
        return None
    
    def process_image(self, image_path):
        """Procesa un archivo de imagen"""
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                return None
            
            return self.process_image_data(img)
            
        except Exception as e:
            print(f"Error procesando imagen: {e}")
            return None
    
    def process_image_data(self, img):
        """Procesa datos de imagen con el motor configurado"""
        if self.engine == "auto":
            # Intentar Tesseract primero, luego PaddleOCR
            result = self.ocr_with_tesseract(img)
            if not result or result["confidence"] < 0.5:
                if self.paddle_ocr:
                    paddle_result = self.ocr_with_paddle(img)
                    if paddle_result and paddle_result["confidence"] > result.get("confidence", 0):
                        result = paddle_result
            return result
            
        elif self.engine == "tesseract":
            return self.ocr_with_tesseract(img)
            
        elif self.engine == "paddle":
            if self.paddle_ocr:
                return self.ocr_with_paddle(img)
            else:
                return self.ocr_with_tesseract(img)
        
        return None
    
    def ocr_with_tesseract(self, img):
        """OCR usando Tesseract"""
        if not self.config.HAS_TESSERACT:
            return None
        
        try:
            # Preprocesar imagen
            processed = self.preprocess_image(img)
            
            # Configuración de Tesseract
            config = '--oem 3 --psm 6'
            if self.config.OCR_LANG:
                config += f' -l {self.config.OCR_LANG}'
            
            # Extraer texto
            text = pytesseract.image_to_string(processed, config=config)
            
            # Calcular confianza
            data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            confidence = np.mean(confidences) / 100 if confidences else 0
            
            return {
                "text": text,
                "confidence": confidence,
                "engine": "tesseract"
            }
            
        except Exception as e:
            print(f"Error en Tesseract: {e}")
            return None
    
    def ocr_with_paddle(self, img):
        """OCR usando PaddleOCR"""
        if not self.paddle_ocr:
            return None
        
        try:
            result = self.paddle_ocr.ocr(img, cls=True)
            
            if not result or not result[0]:
                return None
            
            texts = []
            confidences = []
            
            for line in result[0]:
                if line and len(line) > 1:
                    text = line[1][0]
                    conf = line[1][1] if len(line[1]) > 1 else 0.5
                    texts.append(text)
                    confidences.append(conf)
            
            return {
                "text": "\n".join(texts),
                "confidence": np.mean(confidences) if confidences else 0,
                "engine": "paddle"
            }
            
        except Exception as e:
            print(f"Error en PaddleOCR: {e}")
            return None
    
    def preprocess_image(self, img):
        """Preprocesa la imagen para mejorar el OCR"""
        # Convertir a escala de grises
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # Aplicar threshold
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Eliminar ruido
        denoised = cv2.medianBlur(binary, 3)
        
        return denoised
    
    def extract_embedded_text(self, pdf_path):
        """Extrae texto embebido de un PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            print(f"Error extrayendo texto embebido: {e}")
            return ""


