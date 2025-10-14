# modules/config.py
"""
Configuración centralizada del sistema
"""
from pathlib import Path
import os
import re

class Config:
    """Configuración del sistema de boletas"""
    
    def __init__(self):
        # Directorios
        self.BASE_DIR = Path(__file__).parent.parent
        self.INPUT_DIR = self.BASE_DIR / "Registro"
        self.OUTPUT_DIR = self.BASE_DIR / "Export"
        self.TEMP_DIR = self.BASE_DIR / "temp"
        
        # Crear directorios si no existen
        for dir_path in [self.INPUT_DIR, self.OUTPUT_DIR, self.TEMP_DIR]:
            dir_path.mkdir(exist_ok=True, parents=True)
        
        # Archivos por defecto
        self.DEFAULT_INPUT_DIR = self.INPUT_DIR
        self.DEFAULT_OUTPUT_FILE = self.OUTPUT_DIR / "boletas_procesadas.xlsx"
        
        # Extensiones soportadas
        self.SUPPORTED_EXTENSIONS = {
            '.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp'
        }
        
        # Configuración OCR
        self.OCR_DPI = 300
        self.OCR_LANG = 'spa+eng'  # Español + Inglés
        self.OCR_TIMEOUT = 30  # segundos
        
        # Umbrales
        self.MIN_CONFIDENCE = 0.5
        self.MIN_AMOUNT = 10000
        self.MAX_AMOUNT = 5000000
        
        # Expresiones regulares
        self.init_regex_patterns()
        
        # Convenios conocidos
        self.KNOWN_CONVENIOS = [
            'PRAPS', 'APS', 'DIR', 'SSVSA', 'SENDA', 'PAI', 'PAI-PG',
            'HCV', 'PASMI', 'AIDIA', 'FONIS', 'Mejor Niñez'
        ]
        
        # Meses
        self.MESES = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        # Detectar capacidades
        self.HAS_PADDLE = os.environ.get('HAS_PADDLE', '0') == '1'
        self.HAS_TESSERACT = os.environ.get('HAS_TESSERACT', '0') == '1'
    
    def init_regex_patterns(self):
        """Inicializa los patrones regex"""
        # RUT
        self.RUT_PATTERN = re.compile(
            r'\b(\d{1,2}\.?\d{3}\.?\d{3}-[\dkK])\b'
        )
        
        # Número de boleta
        self.FOLIO_PATTERN = re.compile(
            r'(?:N[°ºo]\s*|No\.?\s*|Nro\.?\s*|Folio\s*:?\s*)(\d{1,7})',
            re.IGNORECASE
        )
        
        # Fecha
        self.DATE_PATTERN = re.compile(
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b'
        )
        
        # Monto
        self.AMOUNT_PATTERN = re.compile(
            r'\$?\s*([0-9]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)'
        )
        
        # Glosa patterns
        self.GLOSA_PATTERN = re.compile(
            r'Por\s+atenci[óo]n\s+profesional\s*:?\s*(.+?)(?:\n|$)',
            re.IGNORECASE | re.DOTALL
        )
        
        # Horas
        self.HOURS_PATTERN = re.compile(
            r'\b(\d{1,3})\s*(?:hrs?|horas?)\b',
            re.IGNORECASE
        )
        
        # Decreto
        self.DECRETO_PATTERN = re.compile(
            r'D\.?\s*A\.?\s*N?[°ºo]?\s*(\d{2,6})',
            re.IGNORECASE
        )