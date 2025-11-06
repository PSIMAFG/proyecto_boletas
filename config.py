# Estructura del proyecto modular:
#
# proyecto_boletas/
# ├── main.py                 # Aplicación principal con GUI
# ├── config.py               # Configuración global
# ├── modules/
# │   ├── __init__.py
# │   ├── ocr_extraction.py   # Módulo de extracción OCR
# │   ├── data_processing.py  # Procesamiento de datos
# │   ├── report_generator.py # Generación de informes
# │   └── utils.py           # Utilidades compartidas
# ├── bin/                    # Binarios de Tesseract y Poppler (opcional)
# ├── debug_preproc/          # Debug de preprocesamiento (opcional)
# ├── review_previews/        # Previews para revisión manual
# ├── Registro/               # Carpeta con archivos a procesar
# └── Export/                 # Carpeta de salida

# ========================================
# config.py - Configuración global
# ========================================
"""
Configuración global del sistema de procesamiento de boletas
"""
import os
from pathlib import Path

# Directorio base
BASE_DIR = Path(__file__).resolve().parent

# Directorios de trabajo
REVIEW_PREVIEW_DIR = BASE_DIR / "review_previews"
DEBUG_DIR = BASE_DIR / "debug_preproc"
EXPORT_DIR = BASE_DIR / "Export"
REGISTRO_DIR = BASE_DIR / "Registro"


os.environ["TESSERACT_CMD"] = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Crear directorios si no existen
for dir_path in [REVIEW_PREVIEW_DIR, EXPORT_DIR, REGISTRO_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

# Control de hilos
os.environ.setdefault("OMP_THREAD_LIMIT", "1")
MAX_WORKERS = min(8, max(2, (os.cpu_count() or 8) - 2))

# Configuración de debug
DEBUG_SAVE_PREPROC = False

# Extensiones de archivo soportadas
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

# Configuración de montos
MONTO_MIN = 10_000
MONTO_MAX = 2_000_000

# Configuración de OCR
OCR_DPI = 350
OCR_CONFIDENCE_THRESHOLD = 0.45

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

# Convenios / líneas canónicas reconocidas por el sistema
KNOWN_CONVENIOS = [
    # Núcleo AIDIA/PRAPS
    "AIDIA",
    "PASMI",
    "SALUD MENTAL",
    "ACOMPAÑAMIENTO",     # acompañamiento psicosocial
    "ESPACIOS AMIGABLES", 
    "MUNICIPAL",          # Salud municipal
    "Mejor Niñez",
    "DIR",
]

# Meses
MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10,
    'noviembre': 11, 'diciembre': 12
}

MESES_SHORT = {'ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'}

# Mapeo de números a nombres de meses
MONTH_NAMES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

# Razones de revisión
REVIEW_REASON_NO_DATE = "Sin_mes_desde_Fecha (posible ticket/tapa OCR)"
REVIEW_REASON_LOW_CONFIDENCE = "Baja_confianza_OCR"

# Orígenes de datos
DATA_SOURCE_BATCH = 'batch_post'
DATA_SOURCE_MEMORY = 'memoria_post'
DATA_SOURCE_DECREE_INFERRED = 'decreto_inferido'
DATA_SOURCE_CONVENTION_INFERRED = 'convenio_inferido'
DATA_SOURCE_USER = 'usuario'

# Configuración de la aplicación
APP_VERSION = "4.0 FINAL"
APP_TITLE = "Sistema de Boletas OCR"
