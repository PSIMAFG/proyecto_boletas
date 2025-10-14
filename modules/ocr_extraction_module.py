# modules/ocr_extraction.py
"""
Módulo de extracción OCR para boletas de honorarios
"""
import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from pypdf import PdfReader
from pathlib import Path
import re
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config import *
from modules.utils import *

# Configurar Tesseract
_TESS_CMD = detect_tesseract_cmd()
if _TESS_CMD:
    pytesseract.pytesseract.tesseract_cmd = _TESS_CMD
    print(f"Tesseract: {_TESS_CMD}")

# Detectar Poppler
POPPLER_BIN_DIR = detect_poppler_bin()
if POPPLER_BIN_DIR:
    print(f"Poppler/bin: {POPPLER_BIN_DIR}")

# Detectar idiomas OCR disponibles
try:
    _AVAIL_LANGS = set(pytesseract.get_languages(config=''))
except Exception:
    _AVAIL_LANGS = set()

if 'spa' in _AVAIL_LANGS:
    OCR_LANG = 'spa'
elif 'eng' in _AVAIL_LANGS:
    OCR_LANG = 'eng'
else:
    OCR_LANG = ''

print(f"Idiomas OCR: {OCR_LANG or '(por defecto)'}")

class OCRExtractor:
    """Clase principal para extracción OCR de boletas"""
    
    def __init__(self):
        self.tesseract_cmd = _TESS_CMD
        self.poppler_bin = POPPLER_BIN_DIR
        self.ocr_lang = OCR_LANG
        
    def correct_orientation(self, img: np.ndarray) -> np.ndarray:
        """Corrige la orientación de la imagen usando OSD de Tesseract"""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
            pil_img = Image.fromarray(gray)
            osd = pytesseract.image_to_osd(pil_img, config="--psm 0")
            m = re.search(r'Rotate:\s+(\d+)', osd)
            if m:
                rot = int(m.group(1)) % 360
                if rot == 90:
                    return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                elif rot == 180:
                    return cv2.rotate(img, cv2.ROTATE_180)
                elif rot == 270:
                    return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            return img
        except Exception:
            return img
    
    def unsharp(self, gray, amount=1.5, sigma=1.0):
        """Aplica máscara de enfoque"""
        blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=sigma)
        return cv2.addWeighted(gray, amount, blur, -(amount - 1), 0)
    
    def apply_gamma(self, gray, gamma=0.8):
        """Aplica corrección gamma (gamma < 1 aclara, gamma > 1 oscurece)"""
        g = np.clip(gray, 0, 255).astype(np.float32) / 255.0
        g = np.power(g, gamma)
        return np.clip(g*255.0, 0, 255).astype(np.uint8)
    
    def deskew_binary(self, bw: np.ndarray) -> np.ndarray:
        """Endereza una imagen binaria"""
        try:
            coords = cv2.findNonZero(255 - bw)
            if coords is None:
                return bw
            rect = cv2.minAreaRect(coords)
            angle = rect[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            (h, w) = bw.shape[:2]
            M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
            return cv2.warpAffine(bw, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        except Exception:
            return bw
    
    def base_gray(self, img: np.ndarray) -> np.ndarray:
        """Convierte a escala de grises y corrige orientación"""
        img = self.correct_orientation(img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
        return gray
    
    # Variantes de preprocesamiento
    def variant_otsu(self, gray):
        """Variante básica con OTSU"""
        g2 = cv2.convertScaleAbs(gray, alpha=1.2, beta=10)
        sharp = self.unsharp(g2, amount=1.5, sigma=1.0)
        bw = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        return self.deskew_binary(bw)
    
    def variant_clahe_otsu(self, gray):
        """Variante con CLAHE + OTSU"""
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        g2 = clahe.apply(gray)
        sharp = self.unsharp(g2, amount=1.6, sigma=1.0)
        bw = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        return self.deskew_binary(bw)
    
    def variant_blackhat_otsu(self, gray):
        """Variante con BlackHat + OTSU"""
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
        enh = cv2.add(gray, cv2.convertScaleAbs(blackhat, alpha=1.5))
        sharp = self.unsharp(enh, amount=1.6, sigma=1.2)
        bw = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        return self.deskew_binary(bw)
    
    def variant_gamma_otsu(self, gray):
        """Variante con corrección gamma"""
        g2 = self.apply_gamma(gray, gamma=0.7)  # aclara
        sharp = self.unsharp(g2, amount=1.7, sigma=1.0)
        bw = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        return self.deskew_binary(bw)
    
    def variant_adaptive_gauss(self, gray):
        """Variante con umbralización adaptativa gaussiana"""
        g2 = cv2.convertScaleAbs(gray, alpha=1.3, beta=5)
        bw = cv2.adaptiveThreshold(g2, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, blockSize=35, C=10)
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((2,2), np.uint8))
        return self.deskew_binary(bw)
    
    def variant_adaptive_mean(self, gray):
        """Variante con umbralización adaptativa por media"""
        g2 = cv2.convertScaleAbs(gray, alpha=1.3, beta=5)
        bw = cv2.adaptiveThreshold(g2, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, blockSize=33, C=8)
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((2,2), np.uint8))
        return self.deskew_binary(bw)
    
    def get_preprocessing_variants(self):
        """Retorna todas las variantes de preprocesamiento disponibles"""
        return [
            ("otsu", self.variant_otsu),
            ("clahe_otsu", self.variant_clahe_otsu),
            ("blackhat_otsu", self.variant_blackhat_otsu),
            ("gamma_otsu", self.variant_gamma_otsu),
            ("adapt_gauss", self.variant_adaptive_gauss),
            ("adapt_mean", self.variant_adaptive_mean),
        ]
    
    def image_to_text_and_conf(self, img_bin: np.ndarray):
        """Ejecuta OCR en una imagen binaria y retorna texto y confianza"""
        import pandas as pd
        
        def _ocr_df(im, psm):
            config = f"--oem 3 --psm {psm}"
            if self.ocr_lang:
                config += f" -l {self.ocr_lang}"
            df = pytesseract.image_to_data(im, config=config, output_type=pytesseract.Output.DATAFRAME)
            if not isinstance(df, pd.DataFrame) or df.empty:
                return "", 0.0
            texts = [str(t) for t in df['text'].dropna() if str(t).strip()]
            conf = pd.to_numeric(df['conf'], errors='coerce')
            conf = conf[conf >= 0]
            conf_mean = float(conf.mean()) / 100 if not conf.empty else 0.0
            return "\n".join(texts), conf_mean
        
        # Intenta diferentes configuraciones de PSM
        txt, c = _ocr_df(img_bin, 6)
        if len(txt.strip()) >= 10: 
            return txt, c
        
        # Intenta con imagen invertida
        inv = 255 - img_bin
        txt, c = _ocr_df(inv, 6)
        if len(txt.strip()) >= 10: 
            return txt, c
        
        # Otros PSM
        txt, c = _ocr_df(img_bin, 4)
        if len(txt.strip()) >= 10: 
            return txt, c
        
        txt, c = _ocr_df(img_bin, 11)
        if len(txt.strip()) >= 10: 
            return txt, c
        
        # Último intento con configuración básica
        config = "--oem 3 --psm 6"
        if self.ocr_lang:
            config += f" -l {self.ocr_lang}"
        txt2 = pytesseract.image_to_string(img_bin, config=config)
        if len(txt2.strip()) > len(txt.strip()):
            txt = txt2
        
        return txt, c
    
    def ocr_best_of_variants(self, img_cv, src_path: Path, page_idx: int = 0):
        """
        Prueba múltiples variantes de preprocesamiento y elige la mejor.
        Devuelve: (texto, confianza, best_bin, best_variant_name)
        """
        gray = self.base_gray(img_cv)
        best_score = -1e9
        best_txt, best_c, best_bin, best_name = "", 0.0, None, "none"
        
        for name, fn in self.get_preprocessing_variants():
            try:
                bin_img = fn(gray)
                save_debug(bin_img, src_path, page_idx, name)
                txt, c = self.image_to_text_and_conf(bin_img)
                txt_s = txt.strip()
                if not txt_s:
                    continue
                
                # Puntuar: confianza + cantidad de texto + bonus por palabras clave
                digit_bonus = min(0.3, 0.01 * len(re.findall(r'\d', txt_s)))
                kw_bonus = 0.2 if re.search(r'honorarios?|total\s+honor|monto\s+bruto', txt_s, re.IGNORECASE) else 0.0
                len_bonus = min(0.6, len(txt_s)/3000.0)
                score = c + digit_bonus + kw_bonus + len_bonus
                
                if score > best_score:
                    best_score = score
                    best_txt, best_c, best_bin, best_name = txt_s, c, bin_img, name
            except Exception:
                continue
        
        return best_txt, best_c, best_bin, best_name
    
    def save_preview_image(self, img_bin: np.ndarray, src_path: Path, page_idx: int, variant_name: str) -> str:
        """Guarda una imagen de preview para revisión manual"""
        fname = f"{src_path.stem}_p{page_idx+1}_{variant_name}.png"
        out = REVIEW_PREVIEW_DIR / fname
        try:
            cv2.imwrite(str(out), img_bin)
            return str(out)
        except Exception:
            return ""
    
    def pdf_to_images(self, pdf_path: Path, dpi=OCR_DPI):
        """Convierte un PDF a una lista de imágenes"""
        kwargs = dict(dpi=dpi)
        if self.poppler_bin:
            kwargs['poppler_path'] = self.poppler_bin
            kwargs['use_pdftocairo'] = True
        pages = convert_from_path(str(pdf_path), **kwargs)
        return pages
    
    def extract_text_from_pdf_embedded(self, pdf_path: Path) -> str:
        """Extrae texto embebido de un PDF (si existe)"""
        try:
            reader = PdfReader(str(pdf_path))
            texts = []
            for page in reader.pages:
                t = page.extract_text() or ""
                if t:
                    texts.append(t)
            return "\n".join(texts)
        except Exception:
            return ""
    
    def process_pdf_with_ocr(self, path: Path):
        """Procesa un PDF completo con OCR"""
        pages = self.pdf_to_images(path, dpi=OCR_DPI)
        page_texts = []
        page_confs = []
        first_preview_path = ""
        
        for idx, pg in enumerate(pages):
            img_cv = cv2.cvtColor(np.array(pg), cv2.COLOR_RGB2BGR)
            txt, c, best_bin, best_name = self.ocr_best_of_variants(img_cv, path, page_idx=idx)
            
            if idx == 0 and best_bin is not None:
                first_preview_path = self.save_preview_image(best_bin, path, page_idx=idx, variant_name=best_name)
            
            if txt:
                page_texts.append(txt)
                page_confs.append(float(c))
        
        return page_texts, page_confs, first_preview_path
    
    def process_image_with_ocr(self, path: Path):
        """Procesa una imagen con OCR"""
        img_cv = cv2.imread(str(path))
        if img_cv is None:
            raise RuntimeError("No se pudo abrir la imagen")
        
        txt, c, best_bin, best_name = self.ocr_best_of_variants(img_cv, path, page_idx=0)
        preview_path = ""
        
        if best_bin is not None:
            preview_path = self.save_preview_image(best_bin, path, page_idx=0, variant_name=best_name)
        
        return txt, c, preview_path
    
    def check_if_text_is_readable(self, text: str) -> bool:
        """
        Verifica si el texto extraído es legible o si necesita OCR.
        Un texto es considerado legible si tiene suficientes caracteres alfabéticos
        y números en proporción correcta.
        """
        if not text or len(text) < 50:
            return False
        
        # Contar caracteres alfabéticos y numéricos
        alpha_count = len(re.findall(r'[a-zA-ZáéíóúñÁÉÍÓÚÑ]', text))
        digit_count = len(re.findall(r'\d', text))
        special_count = len(re.findall(r'[^\w\s]', text))
        total_chars = len(text.replace(' ', '').replace('\n', ''))
        
        if total_chars == 0:
            return False
        
        # Proporción de caracteres legibles
        legible_ratio = (alpha_count + digit_count) / total_chars
        
        # Si hay muchos caracteres especiales o pocos legibles, el texto está corrupto
        if legible_ratio < 0.7 or special_count / total_chars > 0.4:
            return False
        
        # Verificar que hay palabras reconocibles
        words = text.lower().split()
        common_words = {'de', 'el', 'la', 'en', 'y', 'a', 'por', 'con', 'para', 
                       'boleta', 'honorarios', 'rut', 'fecha', 'monto', 'total'}
        found_common = sum(1 for word in words if word in common_words)
        
        return found_common >= 2 or legible_ratio > 0.85
