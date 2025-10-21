# modules/ocr_extraction.py (Versión Corregida)
"""
Módulo de extracción OCR optimizado y corregido
Versión 3.1 - Con correcciones para preview y mejoras en precisión
"""
import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from pypdf import PdfReader
from pathlib import Path
import re
import sys
from typing import Tuple, List, Optional, Dict
import hashlib
import os

sys.path.append(str(Path(__file__).parent.parent))
from config import *
from modules.utils import *

# Configurar Tesseract
_TESS_CMD = detect_tesseract_cmd()
if _TESS_CMD:
    pytesseract.pytesseract.tesseract_cmd = _TESS_CMD

# Detectar Poppler
POPPLER_BIN_DIR = detect_poppler_bin()

# Configuración optimizada de OCR - MÁS SIMPLE
OCR_CONFIG = {
    'spa': '--oem 3 --psm 6 -l spa',
    'eng': '--oem 3 --psm 6 -l eng',
}


class ImagePreprocessor:
    """Clase dedicada al preprocesamiento de imágenes - SIMPLIFICADA"""
    
    @staticmethod
    def auto_rotate(image: np.ndarray) -> np.ndarray:
        """Detecta y corrige la rotación automáticamente"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
            
            if lines is not None and len(lines) > 5:
                angles = []
                for line in lines[:20]:
                    rho, theta = line[0]
                    angle = theta * 180 / np.pi - 90
                    if -45 < angle < 45:
                        angles.append(angle)
                
                if angles:
                    median_angle = np.median(angles)
                    if abs(median_angle) > 1.0:  # Solo rotar si el ángulo es significativo
                        h, w = image.shape[:2]
                        center = (w // 2, h // 2)
                        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                        return cv2.warpAffine(image, M, (w, h), 
                                            flags=cv2.INTER_CUBIC,
                                            borderMode=cv2.BORDER_REPLICATE,
                                            borderValue=(255, 255, 255))
        except Exception:
            pass
        return image
    
    @staticmethod
    def enhance_text(image: np.ndarray) -> np.ndarray:
        """Mejora el texto usando técnicas básicas"""
        try:
            # Convertir a PIL para usar sus filtros
            pil_image = Image.fromarray(image)
            
            # Aumentar nitidez
            enhancer = ImageEnhance.Sharpness(pil_image)
            pil_image = enhancer.enhance(1.5)
            
            # Aumentar contraste
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(1.3)
            
            return np.array(pil_image)
        except Exception:
            return image


class OCRExtractorOptimized:
    """Extractor OCR optimizado con mejoras"""
    
    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.cache = {}
        self.confidence_threshold = 0.40  # REDUCIDO de 0.60
        
        # Asegurar que existe el directorio de previews
        REVIEW_PREVIEW_DIR.mkdir(exist_ok=True, parents=True)
    
    def preprocess_simple(self, image: np.ndarray) -> Dict[str, np.ndarray]:
        """Genera solo 3 variantes principales de preprocesamiento"""
        variants = {}
        
        # Auto-rotar primero
        image = self.preprocessor.auto_rotate(image)
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Variante 1: CLAHE + Otsu (mejor para la mayoría de documentos)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        cl1 = clahe.apply(gray)
        _, otsu1 = cv2.threshold(cl1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants['clahe_otsu'] = otsu1
        
        # Variante 2: Threshold adaptativo
        enhanced = self.preprocessor.enhance_text(gray)
        adaptive = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 21, 10)
        variants['adaptive'] = adaptive
        
        # Variante 3: Otsu simple (para documentos limpios)
        _, otsu_simple = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants['otsu_simple'] = otsu_simple
        
        return variants
    
    def ocr_simple(self, image: np.ndarray, config: str = 'spa') -> Tuple[str, float]:
        """OCR simplificado con una sola configuración"""
        try:
            # OCR con datos detallados
            data = pytesseract.image_to_data(
                image, 
                config=OCR_CONFIG.get(config, OCR_CONFIG['spa']),
                output_type=pytesseract.Output.DICT
            )
            
            # Filtrar palabras con confianza aceptable
            words = []
            confidences = []
            
            for i, conf in enumerate(data['conf']):
                if int(conf) > 20:  # Umbral MÁS BAJO
                    word = data['text'][i].strip()
                    if word:
                        words.append(word)
                        confidences.append(int(conf))
            
            if words:
                text = ' '.join(words)
                avg_conf = np.mean(confidences) / 100.0 if confidences else 0.0
                return text, avg_conf
            
        except Exception as e:
            print(f"Error en OCR: {e}")
        
        return "", 0.0
    
    def process_image_optimized(self, image: np.ndarray) -> Tuple[str, float, np.ndarray]:
        """Procesa una imagen con el pipeline simplificado"""
        # Generar variantes de preprocesamiento
        variants = self.preprocess_simple(image)
        
        best_text = ""
        best_confidence = 0.0
        best_variant = None
        
        # Procesar cada variante
        for variant_name, variant_img in variants.items():
            text, conf = self.ocr_simple(variant_img)
            
            if conf > best_confidence:
                best_text = text
                best_confidence = conf
                best_variant = variant_img
        
        # Si no se obtuvo nada bueno, intentar con la imagen original
        if best_confidence < 0.3:
            text, conf = self.ocr_simple(image)
            if conf > best_confidence:
                best_text = text
                best_confidence = conf
                best_variant = image
        
        return best_text, best_confidence, best_variant
    
    def process_pdf_optimized(self, pdf_path: Path) -> Tuple[List[str], List[float], str]:
        """Procesa un PDF de manera optimizada"""
        # Primero intentar extraer texto embebido
        embedded_text = self.extract_text_from_pdf_embedded(pdf_path)
        
        if embedded_text and self._is_text_usable(embedded_text):
            preview_path = self._create_text_preview(pdf_path, embedded_text)
            return [embedded_text], [0.95], preview_path
        
        # Convertir PDF a imágenes
        try:
            pages = self._pdf_to_images_optimized(pdf_path)
        except Exception as e:
            print(f"Error convirtiendo PDF a imágenes: {e}")
            return [], [], ""
        
        texts = []
        confidences = []
        preview_path = ""
        
        for idx, page_img in enumerate(pages):
            # Convertir PIL a numpy
            img_np = np.array(page_img)
            
            # Procesar con pipeline optimizado
            text, conf, best_img = self.process_image_optimized(img_np)
            
            if text:
                texts.append(text)
                confidences.append(conf)
                
                # Guardar preview de la primera página
                if idx == 0 and best_img is not None:
                    preview_path = self._save_preview(best_img, pdf_path, idx)
        
        return texts, confidences, preview_path
    
    def extract_text_from_pdf_embedded(self, pdf_path: Path) -> str:
        """Extrae texto embebido de manera robusta"""
        try:
            reader = PdfReader(str(pdf_path))
            texts = []
            
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text = re.sub(r'\s+', ' ', text)
                    text = text.strip()
                    texts.append(text)
            
            return '\n'.join(texts)
        except Exception as e:
            print(f"Error extrayendo texto embebido: {e}")
            return ""
    
    def _is_text_usable(self, text: str) -> bool:
        """Verifica si el texto extraído es utilizable"""
        if len(text) < 50:  # REDUCIDO de 100
            return False
        
        # Verificar presencia de campos clave - más flexible
        has_rut = bool(re.search(r'\d{1,2}[\.\-]?\d{3}[\.\-]?\d{3}[\.\-]?[\dkK]', text))
        has_boleta = bool(re.search(r'boleta|honorario', text, re.IGNORECASE))
        has_numbers = len(re.findall(r'\d', text)) > 10  # REDUCIDO de 20
        
        return (has_rut or has_boleta) and has_numbers
    
    def _pdf_to_images_optimized(self, pdf_path: Path, dpi: int = 250) -> List[Image.Image]:
        """Convierte PDF a imágenes con DPI óptimo"""
        kwargs = {
            'dpi': dpi,  # Reducido de 300
            'fmt': 'png',
            'grayscale': False
        }
        
        if POPPLER_BIN_DIR:
            kwargs['poppler_path'] = POPPLER_BIN_DIR
            
        try:
            return convert_from_path(str(pdf_path), **kwargs)
        except Exception as e:
            print(f"Error en conversión PDF: {e}")
            # Intentar sin poppler_path
            kwargs.pop('poppler_path', None)
            return convert_from_path(str(pdf_path), **kwargs)
    
    def _save_preview(self, image: np.ndarray, source_path: Path, page_idx: int) -> str:
        """Guarda una imagen de preview - CORREGIDO"""
        try:
            # Asegurar que el directorio existe
            preview_dir = REVIEW_PREVIEW_DIR
            preview_dir.mkdir(exist_ok=True, parents=True)
            
            # Crear nombre de archivo único
            filename = f"{source_path.stem}_p{page_idx+1}_preview.png"
            preview_path = preview_dir / filename
            
            # Asegurar que la imagen es del tipo correcto
            if image is None:
                return ""
                
            # Si la imagen es float, convertir a uint8
            if image.dtype == np.float32 or image.dtype == np.float64:
                image = (image * 255).astype(np.uint8)
            
            # Guardar la imagen
            success = cv2.imwrite(str(preview_path), image)
            
            if success:
                print(f"Preview guardado: {preview_path}")
                return str(preview_path)
            else:
                print(f"Error guardando preview en {preview_path}")
                return ""
                
        except Exception as e:
            print(f"Error guardando preview: {e}")
            return ""
    
    def _create_text_preview(self, pdf_path: Path, text: str) -> str:
        """Crea una imagen de preview para texto embebido"""
        try:
            # Crear una imagen con el texto
            preview_dir = REVIEW_PREVIEW_DIR
            preview_dir.mkdir(exist_ok=True, parents=True)
            
            filename = f"{pdf_path.stem}_text_preview.png"
            preview_path = preview_dir / filename
            
            # Crear imagen blanca con texto
            img = Image.new('RGB', (800, 1000), color='white')
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            
            # Usar fuente por defecto
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except:
                font = ImageFont.load_default()
            
            # Dibujar texto (primeras 2000 caracteres)
            preview_text = text[:2000] if len(text) > 2000 else text
            draw.text((10, 10), preview_text, fill='black', font=font)
            
            img.save(str(preview_path))
            return str(preview_path)
            
        except Exception as e:
            print(f"Error creando preview de texto: {e}")
            return ""