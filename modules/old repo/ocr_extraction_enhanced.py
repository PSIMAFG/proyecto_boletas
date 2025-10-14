# SPDX-License-Identifier: BUSL-1.1
# © 2025 Matías A. Fernández

# modules/ocr_extraction_enhanced.py
"""
Módulo de extracción OCR mejorado con soporte para PaddleOCR y Tesseract
Incluye gestión de versiones y detección automática de orientación
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
import time
import json
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import hashlib

sys.path.append(str(Path(__file__).parent.parent))

from config import *
from modules.utils import *

class PaddleOCRWrapper:
    """Wrapper para PaddleOCR con manejo de errores"""
    
    def __init__(self):
        self.ocr = None
        self._init_paddle()
    
    def _init_paddle(self):
        """Inicializa PaddleOCR con configuración optimizada"""
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                **PADDLE_CONFIG,
                rec_model_dir=None,  # Usar modelo por defecto
                det_model_dir=None,
                cls_model_dir=None,
                use_space_char=True,
                drop_score=0.5
            )
            print("PaddleOCR inicializado correctamente")
        except ImportError:
            print("PaddleOCR no está instalado. Instalar con: pip install paddlepaddle paddleocr")
            self.ocr = None
        except Exception as e:
            print(f"Error inicializando PaddleOCR: {e}")
            self.ocr = None
    
    def is_available(self) -> bool:
        """Verifica si PaddleOCR está disponible"""
        return self.ocr is not None
    
    def detect_and_recognize(self, img: np.ndarray, timeout: int = PADDLE_TIMEOUT) -> Tuple[str, float]:
        """
        Detecta y reconoce texto con PaddleOCR
        Returns: (texto, confianza)
        """
        if not self.is_available():
            return "", 0.0
        
        try:
            # Usar ThreadPoolExecutor para timeout
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._run_paddle_ocr, img)
                result = future.result(timeout=timeout)
                return result
        except TimeoutError:
            print(f"PaddleOCR timeout después de {timeout} segundos")
            return "", 0.0
        except Exception as e:
            print(f"Error en PaddleOCR: {e}")
            return "", 0.0
    
    def _run_paddle_ocr(self, img: np.ndarray) -> Tuple[str, float]:
        """Ejecuta PaddleOCR en la imagen"""
        try:
            result = self.ocr.ocr(img, cls=True)
            
            if not result or not result[0]:
                return "", 0.0
            
            texts = []
            confidences = []
            
            for line in result[0]:
                if line and len(line) > 1:
                    text = line[1][0] if isinstance(line[1], tuple) else str(line[1])
                    conf = line[1][1] if isinstance(line[1], tuple) and len(line[1]) > 1 else 0.5
                    texts.append(text)
                    confidences.append(conf)
            
            full_text = "\n".join(texts)
            avg_conf = np.mean(confidences) if confidences else 0.0
            
            return full_text, float(avg_conf)
            
        except Exception as e:
            print(f"Error procesando con PaddleOCR: {e}")
            return "", 0.0

class ImageVersionManager:
    """Gestiona las diferentes versiones de imágenes procesadas"""
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.versions_dir = VERSIONS_DIR / self.base_path.stem
        self.versions_dir.mkdir(exist_ok=True, parents=True)
        self.versions = {}
        self.metadata = {}
    
    def save_version(self, img: np.ndarray, version_name: str, metadata: Dict = None) -> str:
        """Guarda una versión de la imagen"""
        filename = f"{self.base_path.stem}_{version_name}_{self._get_hash(img)[:8]}.png"
        path = self.versions_dir / filename
        
        try:
            cv2.imwrite(str(path), img)
            
            # Guardar metadata
            if metadata:
                self.metadata[version_name] = metadata
                meta_path = self.versions_dir / f"{self.base_path.stem}_metadata.json"
                with open(meta_path, 'w') as f:
                    json.dump(self.metadata, f, indent=2)
            
            self.versions[version_name] = str(path)
            return str(path)
        except Exception as e:
            print(f"Error guardando versión {version_name}: {e}")
            return ""
    
    def _get_hash(self, img: np.ndarray) -> str:
        """Genera un hash único para la imagen"""
        return hashlib.md5(img.tobytes()).hexdigest()
    
    def get_all_versions(self) -> Dict[str, str]:
        """Retorna todas las versiones guardadas"""
        return self.versions.copy()
    
    def get_best_version(self) -> Optional[str]:
        """Retorna la mejor versión basada en metadata"""
        if not self.metadata:
            return None
        
        # Buscar la versión con mejor confianza
        best_version = max(self.metadata.items(), 
                          key=lambda x: x[1].get('confidence', 0))
        return self.versions.get(best_version[0])

class EnhancedOCRExtractor:
    """Extractor OCR mejorado con múltiples motores y gestión de versiones"""
    
    def __init__(self, engine: OCREngine = OCREngine.AUTO):
        self.engine = engine
        self.tesseract_cmd = detect_tesseract_cmd()
        self.poppler_bin = detect_poppler_bin()
        
        # Configurar Tesseract si está disponible
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            try:
                self.tesseract_langs = set(pytesseract.get_languages(config=''))
                self.ocr_lang = 'spa' if 'spa' in self.tesseract_langs else 'eng'
            except:
                self.tesseract_langs = set()
                self.ocr_lang = ''
        else:
            self.tesseract_langs = set()
            self.ocr_lang = ''
        
        # Inicializar PaddleOCR
        self.paddle = PaddleOCRWrapper()
        
        # Gestor de versiones
        self.version_manager = None
    
    def detect_orientation_paddle(self, img: np.ndarray) -> int:
        """Detecta la orientación usando PaddleOCR"""
        if not self.paddle.is_available():
            return 0
        
        best_angle = 0
        best_score = 0
        
        for angle in ROTATION_ANGLES:
            if angle == 0:
                test_img = img.copy()
            else:
                test_img = self.rotate_image(img, angle)
            
            # Probar un área pequeña para velocidad
            h, w = test_img.shape[:2]
            sample = test_img[h//4:3*h//4, w//4:3*w//4]
            
            text, conf = self.paddle.detect_and_recognize(sample, timeout=5)
            
            # Calcular score basado en confianza y cantidad de texto
            score = conf * min(1.0, len(text) / 100)
            
            if score > best_score:
                best_score = score
                best_angle = angle
        
        return best_angle
    
    def rotate_image(self, img: np.ndarray, angle: int) -> np.ndarray:
        """Rota la imagen por el ángulo especificado"""
        if angle == 0:
            return img
        elif angle == 90:
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(img, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return img
    
    def correct_orientation_tesseract(self, img: np.ndarray) -> np.ndarray:
        """Corrige la orientación usando Tesseract OSD"""
        if not self.tesseract_cmd:
            return img
        
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            pil_img = Image.fromarray(gray)
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(pytesseract.image_to_osd, pil_img, config="--psm 0")
                osd = future.result(timeout=10)
            
            m = re.search(r'Rotate:\s+(\d+)', osd)
            if m:
                angle = int(m.group(1))
                return self.rotate_image(img, angle)
            
        except Exception as e:
            print(f"Error en detección de orientación Tesseract: {e}")
        
        return img
    
    def auto_correct_orientation(self, img: np.ndarray) -> np.ndarray:
        """Corrige automáticamente la orientación usando el mejor método disponible"""
        if not AUTO_ROTATION:
            return img
        
        # Intentar primero con PaddleOCR si está disponible
        if self.paddle.is_available():
            angle = self.detect_orientation_paddle(img)
            if angle != 0:
                print(f"Rotación detectada con PaddleOCR: {angle}°")
                return self.rotate_image(img, angle)
        
        # Fallback a Tesseract
        if self.tesseract_cmd:
            return self.correct_orientation_tesseract(img)
        
        return img
    
    def preprocess_variants(self, img: np.ndarray) -> List[Tuple[str, np.ndarray]]:
        """Genera variantes de preprocesamiento más conservadoras"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
        variants = []
        
        # 1. Original (sin modificación)
        variants.append(("original", gray))
        
        # 2. Mejora de contraste suave
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        variants.append(("enhanced", enhanced))
        
        # 3. Binarización Otsu
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(("otsu", otsu))
        
        # 4. Binarización adaptativa (más suave)
        adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY, 21, 11)
        variants.append(("adaptive", adaptive))
        
        # 5. Denoising
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        variants.append(("denoised", denoised))
        
        return variants
    
    def ocr_with_tesseract(self, img: np.ndarray, timeout: int = TESSERACT_TIMEOUT) -> Tuple[str, float, str]:
        """
        OCR con Tesseract con timeout
        Returns: (texto, confianza, variante_usada)
        """
        if not self.tesseract_cmd:
            return "", 0.0, "none"
        
        best_text = ""
        best_conf = 0.0
        best_variant = "none"
        
        # Generar variantes
        variants = self.preprocess_variants(img)
        
        for variant_name, variant_img in variants:
            try:
                # Guardar versión si está habilitado
                if SAVE_ALL_VERSIONS and self.version_manager:
                    self.version_manager.save_version(
                        variant_img, 
                        f"tesseract_{variant_name}",
                        {"engine": "tesseract", "variant": variant_name}
                    )
                
                # OCR con timeout
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._run_tesseract, variant_img)
                    text, conf = future.result(timeout=timeout)
                
                # Evaluar calidad
                if self._evaluate_text_quality(text, conf) > self._evaluate_text_quality(best_text, best_conf):
                    best_text = text
                    best_conf = conf
                    best_variant = variant_name
                
            except TimeoutError:
                print(f"Tesseract timeout en variante {variant_name}")
                continue
            except Exception as e:
                print(f"Error en Tesseract variante {variant_name}: {e}")
                continue
        
        return best_text, best_conf, best_variant
    
    def _run_tesseract(self, img: np.ndarray) -> Tuple[str, float]:
        """Ejecuta Tesseract OCR"""
        import pandas as pd
        
        config = f"--oem 3 --psm 6"
        if self.ocr_lang:
            config += f" -l {self.ocr_lang}"
        
        # Obtener texto y confianza
        df = pytesseract.image_to_data(img, config=config, output_type=pytesseract.Output.DATAFRAME)
        
        if not isinstance(df, pd.DataFrame) or df.empty:
            return "", 0.0
        
        texts = [str(t) for t in df['text'].dropna() if str(t).strip()]
        conf = pd.to_numeric(df['conf'], errors='coerce')
        conf = conf[conf >= 0]
        conf_mean = float(conf.mean()) / 100 if not conf.empty else 0.0
        
        return "\n".join(texts), conf_mean
    
    def ocr_with_paddle(self, img: np.ndarray) -> Tuple[str, float, str]:
        """
        OCR con PaddleOCR
        Returns: (texto, confianza, variante_usada)
        """
        if not self.paddle.is_available():
            return "", 0.0, "none"
        
        best_text = ""
        best_conf = 0.0
        best_variant = "none"
        
        # Para PaddleOCR, usar menos variantes (funciona mejor con imágenes naturales)
        variants = [
            ("original", img),
            ("enhanced", self._enhance_for_paddle(img))
        ]
        
        for variant_name, variant_img in variants:
            try:
                # Guardar versión si está habilitado
                if SAVE_ALL_VERSIONS and self.version_manager:
                    self.version_manager.save_version(
                        variant_img,
                        f"paddle_{variant_name}",
                        {"engine": "paddle", "variant": variant_name}
                    )
                
                text, conf = self.paddle.detect_and_recognize(variant_img)
                
                # Evaluar calidad
                if self._evaluate_text_quality(text, conf) > self._evaluate_text_quality(best_text, best_conf):
                    best_text = text
                    best_conf = conf
                    best_variant = variant_name
                    
            except Exception as e:
                print(f"Error en PaddleOCR variante {variant_name}: {e}")
                continue
        
        return best_text, best_conf, best_variant
    
    def _enhance_for_paddle(self, img: np.ndarray) -> np.ndarray:
        """Mejora la imagen específicamente para PaddleOCR"""
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        
        # PaddleOCR funciona mejor con imágenes más nítidas
        # Aplicar sharpening suave
        kernel = np.array([[0,-1,0], [-1,5,-1], [0,-1,0]])
        sharpened = cv2.filter2D(img, -1, kernel)
        
        # Ajustar brillo y contraste
        alpha = 1.2  # Contraste
        beta = 10    # Brillo
        adjusted = cv2.convertScaleAbs(sharpened, alpha=alpha, beta=beta)
        
        return adjusted
    
    def _evaluate_text_quality(self, text: str, conf: float) -> float:
        """Evalúa la calidad del texto extraído"""
        if not text:
            return 0.0
        
        # Factores de calidad
        text_len = min(1.0, len(text) / 1000)  # Normalizar longitud
        
        # Buscar palabras clave importantes
        keywords_score = 0
        keywords = ['boleta', 'honorarios', 'rut', 'total', 'fecha', 'monto']
        for kw in keywords:
            if kw in text.lower():
                keywords_score += 0.1
        
        # Proporción de caracteres alfabéticos
        alpha_ratio = len(re.findall(r'[a-zA-ZáéíóúñÁÉÍÓÚÑ]', text)) / max(1, len(text))
        
        # Score final
        return conf * 0.5 + text_len * 0.2 + keywords_score * 0.2 + alpha_ratio * 0.1
    
    def process_image_multi_engine(self, img_path: Path) -> Dict:
        """
        Procesa una imagen usando múltiples motores según configuración
        """
        # Inicializar gestor de versiones
        self.version_manager = ImageVersionManager(img_path)
        
        # Leer imagen
        img = cv2.imread(str(img_path))
        if img is None:
            raise RuntimeError(f"No se pudo leer la imagen: {img_path}")
        
        # Corregir orientación
        img = self.auto_correct_orientation(img)
        
        # Guardar imagen corregida
        if SAVE_ALL_VERSIONS:
            self.version_manager.save_version(img, "corrected", {"rotation": "auto"})
        
        results = {}
        
        if self.engine == OCREngine.TESSERACT:
            text, conf, variant = self.ocr_with_tesseract(img)
            results['tesseract'] = {'text': text, 'confidence': conf, 'variant': variant}
            
        elif self.engine == OCREngine.PADDLEOCR:
            text, conf, variant = self.ocr_with_paddle(img)
            results['paddle'] = {'text': text, 'confidence': conf, 'variant': variant}
            
        elif self.engine == OCREngine.AUTO:
            # Intentar Tesseract primero
            text_tess, conf_tess, var_tess = self.ocr_with_tesseract(img)
            results['tesseract'] = {'text': text_tess, 'confidence': conf_tess, 'variant': var_tess}
            
            # Si Tesseract falla o tiene baja confianza, intentar PaddleOCR
            if conf_tess < 0.5 or len(text_tess) < 50:
                print(f"Tesseract confianza baja ({conf_tess:.2f}), intentando PaddleOCR...")
                text_paddle, conf_paddle, var_paddle = self.ocr_with_paddle(img)
                results['paddle'] = {'text': text_paddle, 'confidence': conf_paddle, 'variant': var_paddle}
        
        # Seleccionar mejor resultado
        best_engine = max(results.keys(), key=lambda k: results[k]['confidence'])
        best_result = results[best_engine]
        
        return {
            'text': best_result['text'],
            'confidence': best_result['confidence'],
            'engine': best_engine,
            'variant': best_result['variant'],
            'all_results': results,
            'versions': self.version_manager.get_all_versions()
        }
    
    def process_pdf_multi_engine(self, pdf_path: Path) -> Dict:
        """Procesa un PDF con múltiples motores"""
        # Primero intentar extraer texto embebido
        embedded_text = self.extract_text_from_pdf_embedded(pdf_path)
        
        if embedded_text and self.check_if_text_is_readable(embedded_text):
            return {
                'texts': [embedded_text],
                'confidences': [0.99],
                'engine': 'embedded',
                'pages': 1,
                'versions': {}
            }
        
        # Convertir PDF a imágenes
        kwargs = dict(dpi=OCR_DPI)
        if self.poppler_bin:
            kwargs['poppler_path'] = self.poppler_bin
            kwargs['use_pdftocairo'] = True
        
        pages = convert_from_path(str(pdf_path), **kwargs)
        
        all_texts = []
        all_confs = []
        all_versions = {}
        
        for idx, page in enumerate(pages):
            # Crear path temporal para la página
            temp_path = VERSIONS_DIR / f"{pdf_path.stem}_page_{idx+1}.png"
            page.save(temp_path)
            
            # Procesar con multi-engine
            result = self.process_image_multi_engine(temp_path)
            
            all_texts.append(result['text'])
            all_confs.append(result['confidence'])
            all_versions[f'page_{idx+1}'] = result['versions']
        
        return {
            'texts': all_texts,
            'confidences': all_confs,
            'engine': self.engine.value,
            'pages': len(pages),
            'versions': all_versions
        }
    
    def extract_text_from_pdf_embedded(self, pdf_path: Path) -> str:
        """Extrae texto embebido de un PDF"""
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
    
    def check_if_text_is_readable(self, text: str) -> bool:
        """Verifica si el texto es legible"""
        if not text or len(text) < 50:
            return False
        
        # Contar caracteres
        alpha_count = len(re.findall(r'[a-zA-ZáéíóúñÁÉÍÓÚÑ]', text))
        digit_count = len(re.findall(r'\d', text))
        special_count = len(re.findall(r'[^\w\s]', text))
        total_chars = len(text.replace(' ', '').replace('\n', ''))
        
        if total_chars == 0:
            return False
        
        # Proporción de caracteres legibles
        legible_ratio = (alpha_count + digit_count) / total_chars
        
        # Si hay muchos caracteres especiales, el texto está corrupto
        if legible_ratio < 0.7 or special_count / total_chars > 0.4:
            return False
        
        # Buscar palabras comunes
        words = text.lower().split()
        common_words = {'de', 'el', 'la', 'en', 'y', 'a', 'por', 'con', 'para', 
                       'boleta', 'honorarios', 'rut', 'fecha', 'monto', 'total'}
        found_common = sum(1 for word in words if word in common_words)
        
        return found_common >= 2 or legible_ratio > 0.85

