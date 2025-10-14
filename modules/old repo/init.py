# SPDX-License-Identifier: BUSL-1.1
# © 2025 Matías A. Fernández

# modules/__init__.py
"""
Módulos del sistema de procesamiento de boletas de honorarios
"""

from .utils import *
from .ocr_extraction import OCRExtractor
from .data_processing import DataProcessor
from .report_generator import ReportGenerator

__version__ = "2.0.0"
__author__ = "Sistema de Procesamiento de Boletas"

__all__ = [
    'OCRExtractor',
    'DataProcessor', 
    'ReportGenerator',
    'install_required_libraries',
    'detect_tesseract_cmd',
    'detect_poppler_bin',
    'dv_ok',
    'normaliza_monto',
    'clean_text',
    'plaus_amount',
    'parse_fecha',
    'looks_like_person_name',
    'iter_files',
    'get_month_year_from_date',
    'format_currency'
]

