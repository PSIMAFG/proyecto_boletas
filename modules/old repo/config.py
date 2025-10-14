# SPDX-License-Identifier: BUSL-1.1
# © 2025 Matías A. Fernández

# config.py
"""
Configuración global del sistema de procesamiento de boletas v3.0
Con soporte para múltiples motores OCR
"""
import os
from pathlib import Path
from enum import Enum

# Directorio base
BASE_DIR = Path(__file__).resolve().parent

# Directorios de trabajo
REVIEW_PREVIEW_DIR = BASE_DIR / "review_previews"
DEBUG_DIR = BASE_DIR / "debug_preproc"
EXPORT_DIR = BASE_DIR / "Export"
REGISTRO_DIR = BASE_DIR / "Registro"
VERSIONS_DIR = BASE_DIR / "image_versions"  # Nueva carpeta para versiones

# Crear directorios si no existen
for dir_path in [REVIEW_PREVIEW_DIR, EXPORT_DIR, REGISTRO_DIR, VERSIONS_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

# Control de hilos
os.environ.setdefault("OMP_THREAD_LIMIT", "1")
MAX_WORKERS = min(4, max(2, (os.cpu_count() or 4) - 2))  # Reducido para PaddleOCR

# Motor OCR
class OCREngine(Enum):
    TESSERACT = "tesseract"
    PADDLEOCR = "paddleocr"
    AUTO = "auto"  # Intenta Tesseract primero, luego PaddleOCR

DEFAULT_OCR_ENGINE = OCREngine.AUTO

# Configuración de PaddleOCR
PADDLE_CONFIG = {
    'use_angle_cls': True,  # Detección de ángulo
    'lang': 'latin',  # o 'ch' para chino
    'use_gpu': False,  # True si tienes GPU con CUDA
    'show_log': False,
    'det_db_thresh': 0.3,
    'det_db_box_thresh': 0.5,
    'det_db_unclip_ratio': 1.6,
    'use_mp': True,
    'total_process_num': MAX_WORKERS
}

# Configuración de debug
DEBUG_SAVE_PREPROC = False
SAVE_ALL_VERSIONS = True  # Guardar todas las versiones procesadas

# Extensiones de archivo soportadas
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

# Configuración de montos
MONTO_MIN = 10_000
MONTO_MAX = 2_000_000

# Configuración de OCR
OCR_DPI = 300  # Reducido de 350 para mejor velocidad
OCR_CONFIDENCE_THRESHOLD = 0.45
TESSERACT_TIMEOUT = 30  # Timeout en segundos para Tesseract
PADDLE_TIMEOUT = 20  # Timeout para PaddleOCR

# Expresiones regulares y patrones
import re

RUT_RE = re.compile(r'(\d{1,2}\.?\d{3}\.?\d{3}-[\dkK])')
RUT_ANCHOR_RE = re.compile(r'\bRUT\s*:?\s*([0-9]{1,2}\.?\d{3}\.?\d{3}-[\dkK])\b', re.IGNORECASE)

FOLIO_RE = re.compile(r'(?:\bN[°ºo\W]{0,3}\b|No\.?|Nro\.?|Folio)\s*[:#\-]?\s*([0-9]{1,7})', re.IGNORECASE)

FECHA_NUM_RE = re.compile(r'\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b')
FECHA_TEXT_RE = re.compile(r'\bFecha\s*:?\s*(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{2,4})\b', re.IGNORECASE)
FECHA_NUM_EMI_RE = re.compile(r'Fecha\s*/\s*Hora\s*Emisi[oó]n\s*:\s*(\d{1,2}/\d{1,2}/\d{2,4})', re.IGNORECASE)

MONTO_BRUTO_LABEL_RE = re.compile(
    r'(total\s+honorarios?|honorarios?\s*brutos?|monto\s*bruto|valor\s*bruto)',
    re.IGNORECASE
)
MONTO_NETO_LABEL_RE = re.compile(
    r'(l[ií]quido|liquido|neto|total\s+a\s+pagar|a\s+pagar)',
    re.IGNORECASE
)
RETENCION_LABEL_RE = re.compile(
    r'(retenc|retenido|retenci[oó]n|impto\.?\s*retenido|impuesto\s*retenido)',
    re.IGNORECASE
)

# Palabras clave para detección de ruido en montos
AMOUNT_NOISE_TERMS = [
    'timbre', 'electr', 'verifique', 'código', 'codigo', 'seguridad', 'sii',
    'resoluci', 'res. ex', 'autoriz', 'verificador', 'qr', 'barra', 'barras', 
    'barcode', 'hash'
]

# Convenios conocidos
KNOWN_CONVENIOS = [
    'AIDIA', 'PASMI', 'PRAPS', 'DIR', 'FONIS', 'Mejor Niñez', 
    'APS', 'SSVSA', 'HCV', 'PAI', 'PAI-PG', 'SENDA'
]

# Meses
MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10,
    'noviembre': 11, 'diciembre': 12
}

MESES_SHORT = {'ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'}

# Configuración de rotación de imágenes
ROTATION_ANGLES = [0, 90, 180, 270]  # Ángulos a probar
AUTO_ROTATION = True  # Detectar y corregir automáticamente

