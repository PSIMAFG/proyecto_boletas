# modules/ocr_extraction.py (Simplificado y Robusto)
"""
Módulo OCR simplificado pero robusto
Versión 3.1 - Combina lo mejor del código original con mejoras
"""
import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from pypdf import PdfReader
from pathlib import Path
import re
import sys
from typing import Tuple, List, Optional
from concurrent.futures import ThreadPoolExecutor

sys.path.append(str(Path(__file__).parent.parent))
from config import *
from modules.utils import *

# Configurar Tesseract
_TESS_CMD = detect_tesseract_cmd()
if _TESS_CMD:
    pytesseract.pytesseract.tesseract_cmd = _TESS_CMD

POPPLER_BIN_DIR = detect_poppler_bin()


class ImagePreprocessor:
    """Preprocesamiento de imágenes simplificado"""
    
    @staticmethod
    def correct_orientation(img: np.ndarray) -> np.ndarray:
        """Corrige orientación si es necesario"""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            pil_img = Image.fromarray(gray)
            osd = pytesseract.image_to_osd(pil_img, config="--psm 0")
            
            rotation = re.search(r'Rotate:\s+(\d+)', osd)
            if rotation:
                angle = int(rotation.group(1))
                if angle == 90:
                    return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                elif angle == 180:
                    return cv2.rotate(img, cv2.ROTATE_180)
                elif angle == 270:
                    return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        except Exception:
            pass
        
        return img
    
    @staticmethod
    def unsharp_mask(gray: np.ndarray, amount: float = 1.5, sigma: float = 1.0) -> np.ndarray:
        """Aplica unsharp mask para mejorar nitidez"""
        blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=sigma)
        return cv2.addWeighted(gray, amount, blur, -(amount - 1), 0)
    
    @staticmethod
    def apply_gamma(gray: np.ndarray, gamma: float = 0.7) -> np.ndarray:
        """Ajusta gamma para aclarar/oscurecer"""
        normalized = np.clip(gray, 0, 255).astype(np.float32) / 255.0
        corrected = np.power(normalized, gamma)
        return np.clip(corrected * 255.0, 0, 255).astype(np.uint8)


def _enhance_for_text_pil(img: Image.Image) -> Image.Image:
    """
    Mejora suave para texto (CLAHE si hay OpenCV, si no PIL).
    Evita binarizados agresivos que borren trazos finos.
    """
    if not isinstance(img, Image.Image):
        img = Image.fromarray(img)

    # Con OpenCV (mejor)
    try:
        import cv2, numpy as np
        arr = np.array(img.convert("RGB"))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        gray = cv2.bilateralFilter(gray, d=5, sigmaColor=50, sigmaSpace=50)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        eq = clahe.apply(gray)
        th = cv2.adaptiveThreshold(eq, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 10)
        kernel = np.ones((2, 2), np.uint8)
        th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
        return Image.fromarray(th)
    except Exception:
        # Solo PIL (fallback)
        pil = img.convert("RGB")
        pil = ImageOps.autocontrast(pil)
        pil = pil.filter(ImageFilter.MedianFilter(size=3))
        g = pil.convert("L")
        arr = np.array(g)
        thr = (arr > 180).astype("uint8") * 255
        return Image.fromarray(thr)


def _tesseract_simple(img: Image.Image, psm: int = 6, oem: int = 1, lang: str = "spa") -> str:
    config = f"--oem {oem} --psm {psm}"
    try:
        return pytesseract.image_to_string(img, lang=lang, config=config)
    except Exception:
        return ""


def ocr_two_passes(image) -> str:
    """
    1) Pasada sin binarizar agresivo (gris + autocontrast).
    2) Pasada con mejora (CLAHE/threshold suave).
    Se elige el texto con mejor 'puntaje' semántico para boletas.
    """
    pil = image if isinstance(image, Image.Image) else Image.fromarray(image)
    # Pasada 1 (gris, sin binarizar fuerte)
    txt1 = _tesseract_simple(ImageOps.autocontrast(pil.convert("L")), psm=6, oem=1)
    # Pasada 2 (mejorada)
    txt2 = _tesseract_simple(_enhance_for_text_pil(pil), psm=6, oem=1)

    def score(t: str) -> int:
        s = 0
        if re.search(r'(?i)total\s+honorarios', t): s += 2
        if re.search(r'(?i)\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b', t): s += 1
        if re.search(r'(?<!\d)(\d{3}\.\d{3}|\d{6,7})(?!\d)', t): s += 1  # 1.446.896 o 1085172
        if re.search(r'(?i)\bD\.?A\b|\bdecreto\b', t): s += 1
        return s

    return txt1 if score(txt1) >= score(txt2) else txt2

class OCRExtractorOptimized:
    """Extractor OCR optimizado con múltiples variantes"""
    
    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.cache = {}
        
        # Detectar idiomas disponibles
        try:
            langs_available = set(pytesseract.get_languages(config=''))
            if 'spa' in langs_available:
                self.ocr_lang = 'spa'
            elif 'eng' in langs_available:
                self.ocr_lang = 'eng'
            else:
                self.ocr_lang = ''
        except Exception:
            self.ocr_lang = ''
    
    def preprocess_variants(self, gray: np.ndarray) -> List[Tuple[str, np.ndarray]]:
        """Genera variantes de preprocesamiento"""
        variants = []
        
        # 1. Otsu básico con mejoras
        try:
            enhanced = cv2.convertScaleAbs(gray, alpha=1.2, beta=10)
            sharp = self.preprocessor.unsharp_mask(enhanced, 1.5, 1.0)
            _, otsu = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            otsu = cv2.morphologyEx(otsu, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
            variants.append(("otsu", otsu))
        except Exception:
            pass
        
        # 2. CLAHE + Otsu (bueno para iluminación variable)
        try:
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            cl = clahe.apply(gray)
            sharp = self.preprocessor.unsharp_mask(cl, 1.6, 1.0)
            _, otsu = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            otsu = cv2.morphologyEx(otsu, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
            variants.append(("clahe_otsu", otsu))
        except Exception:
            pass
        
        # 3. Gamma correction + Otsu (para documentos oscuros)
        try:
            gamma_corrected = self.preprocessor.apply_gamma(gray, 0.7)
            sharp = self.preprocessor.unsharp_mask(gamma_corrected, 1.7, 1.0)
            _, otsu = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            variants.append(("gamma_otsu", otsu))
        except Exception:
            pass
        
        # 4. Adaptive Gaussian (robusto para fondos variables)
        try:
            enhanced = cv2.convertScaleAbs(gray, alpha=1.3, beta=5)
            adaptive = cv2.adaptiveThreshold(
                enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 35, 10
            )
            adaptive = cv2.morphologyEx(adaptive, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
            variants.append(("adaptive_gauss", adaptive))
        except Exception:
            pass
        
        return variants
    
    def ocr_image(self, img_bin: np.ndarray) -> Tuple[str, float]:
        """Ejecuta OCR con múltiples configuraciones"""
        import pandas as pd
        
        def try_ocr(image, psm):
            config = f"--oem 3 --psm {psm}"
            if self.ocr_lang:
                config += f" -l {self.ocr_lang}"
            
            try:
                df = pytesseract.image_to_data(
                    image, 
                    config=config, 
                    output_type=pytesseract.Output.DATAFRAME
                )
                
                if not isinstance(df, pd.DataFrame) or df.empty:
                    return "", 0.0
                
                # Filtrar y extraer texto
                valid_data = df[df['conf'] >= 0]
                texts = [str(t) for t in valid_data['text'].dropna() if str(t).strip()]
                
                if not texts:
                    return "", 0.0
                
                # Calcular confianza
                confidences = pd.to_numeric(valid_data['conf'], errors='coerce')
                confidences = confidences[confidences >= 0]
                avg_conf = float(confidences.mean() / 100) if not confidences.empty else 0.0
                
                return "\n".join(texts), avg_conf
                
            except Exception:
                return "", 0.0
        
        # Probar diferentes PSM (Page Segmentation Modes)
        best_text = ""
        best_conf = 0.0
        
        for psm in [6, 4, 11]:  # 6=bloque uniforme, 4=columna única, 11=sparse
            text, conf = try_ocr(img_bin, psm)
            
            if len(text.strip()) > len(best_text.strip()):
                best_text = text
                best_conf = conf
        
        # Si todo falla, intentar con imagen invertida
        if len(best_text.strip()) < 10:
            inverted = 255 - img_bin
            text, conf = try_ocr(inverted, 6)
            if len(text.strip()) > len(best_text.strip()):
                best_text = text
                best_conf = conf
        
        return best_text, best_conf
    
    def process_image_optimized(self, img: np.ndarray) -> Tuple[str, float, np.ndarray]:
        """Procesa una imagen con múltiples variantes"""
        # Corregir orientación
        img = self.preprocessor.correct_orientation(img)
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        
        # Generar variantes de preprocesamiento
        variants = self.preprocess_variants(gray)
        
        best_text = ""
        best_conf = 0.0
        best_img = None
        
        # Procesar cada variante
        for name, variant_img in variants:
            text, conf = self.ocr_image(variant_img)
            
            if not text:
                continue
            
            # Calcular score considerando calidad del texto
            digit_bonus = min(0.2, len(re.findall(r'\d', text)) * 0.005)
            keyword_bonus = 0.15 if re.search(r'honorarios?|boleta|total', text, re.IGNORECASE) else 0.0
            length_bonus = min(0.3, len(text) / 1000.0)
            
            score = conf + digit_bonus + keyword_bonus + length_bonus
            
            if score > best_conf or len(text) > len(best_text) * 1.5:
                best_text = text
                best_conf = conf
                best_img = variant_img
        
        return best_text, best_conf, best_img
    
    def extract_text_from_pdf_embedded(self, pdf_path: Path) -> str:
        """Extrae texto embebido SOLO de la primera página del PDF"""
        try:
            reader = PdfReader(str(pdf_path))
            if not reader.pages:
                return ""
            page = reader.pages[0]
            text = page.extract_text() or ""
            return re.sub(r'\s+', ' ', text).strip()
        except Exception:
            return ""

    def _pdf_first_page_to_image(self, pdf_path: Path, dpi: int = 600) -> Image.Image:
        """Convierte SOLO la primera página del PDF a imagen"""
        kwargs = {'dpi': dpi, 'first_page': 1, 'last_page': 1}
        if POPPLER_BIN_DIR:
            kwargs['poppler_path'] = POPPLER_BIN_DIR
            kwargs['use_pdftocairo'] = True
        # convert_from_path devuelve una lista; tomas el primer elemento
        return convert_from_path(str(pdf_path), **kwargs)[0]
    
    def _is_text_usable(self, text: str) -> bool:
        """Verifica si el texto extraído es utilizable"""
        if len(text) < 80:
            return False
        
        # Debe tener números y letras en proporción razonable
        has_numbers = len(re.findall(r'\d', text)) > 15
        has_letters = len(re.findall(r'[a-zA-ZáéíóúñÁÉÍÓÚÑ]', text)) > 50
        
        # Buscar palabras clave
        has_keywords = bool(re.search(r'boleta|honorarios|rut', text, re.IGNORECASE))
        
        return has_numbers and has_letters and has_keywords
    
    def _pdf_to_images(self, pdf_path: Path, dpi: int = 800) -> List[Image.Image]:
        """Convierte PDF a imágenes"""
        kwargs = {'dpi': dpi}
        
        if POPPLER_BIN_DIR:
            kwargs['poppler_path'] = POPPLER_BIN_DIR
            kwargs['use_pdftocairo'] = True
        
        return convert_from_path(str(pdf_path), **kwargs)
    
    def process_pdf_optimized(self, pdf_path: Path) -> Tuple[List[str], List[float], str]:
        """Procesa SOLO la primera página del PDF (600 DPI)"""
        # 1) Intentar texto embebido de la primera página
        embedded_text = self.extract_text_from_pdf_embedded(pdf_path)
        if embedded_text and self._is_text_usable(embedded_text):
            return [embedded_text], [0.99], ""

        # 2) Renderizar SOLO la primera página a 600 DPI
        page_img = self._pdf_first_page_to_image(pdf_path, dpi=600)

        # 3A) Pipeline actual (varias variantes con image_to_data)
        img_np = np.array(page_img)
        text_cv, conf_cv, best_img = self.process_image_optimized(img_np)

        # 3B) Doble pasada “suave” (string directo)
        text_two = ocr_two_passes(page_img)

        # 4) Elegir el mejor por heurística
        def quality(t: str, base: float = 0.0) -> float:
            if not t: 
                return -1.0
            q = base
            if re.search(r'(?i)total\s+honorarios', t): q += 0.6
            if re.search(r'(?<!\d)(\d{3}\.\d{3}|\d{6,7})(?!\d)', t): q += 0.4
            if re.search(r'(?i)\bD\.?A\b|\bdecreto\b', t): q += 0.2
            q += min(0.3, len(t) / 1200.0)  # recompensa por longitud razonable
            return q

        q_cv  = quality(text_cv, conf_cv)
        q_two = quality(text_two, 0.55)  # suele traer menos conf, le doy un piso

        if q_two > q_cv:
            # nos quedamos con el texto de doble pasada
            texts = [text_two]
            confidences = [max(0.55, conf_cv)]  # un piso razonable
            # preview: guarda la imagen mejorada de la doble pasada
            preview_path = self._save_preview(np.array(_enhance_for_text_pil(page_img)), pdf_path, page_idx=0)
        else:
            texts = [text_cv] if text_cv else []
            confidences = [conf_cv] if text_cv else []
            preview_path = self._save_preview(best_img, pdf_path, page_idx=0) if (text_cv and best_img is not None) else ""

        return texts, confidences, preview_path
    
    def _save_preview(self, image: np.ndarray, source_path: Path, page_idx: int) -> str:
        """Guarda imagen de preview"""
        try:
            # Usar la configuración global para el directorio de previews
            preview_dir = REVIEW_PREVIEW_DIR
            preview_dir.mkdir(exist_ok=True, parents=True)

            filename = f"{source_path.stem}_p{page_idx+1}.png"
            preview_path = preview_dir / filename

            cv2.imwrite(str(preview_path), image)
            return str(preview_path)
        except Exception as e:
            # Silenciar el error de preview, no debe detener el procesamiento
            return ""