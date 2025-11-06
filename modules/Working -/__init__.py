# modules/__init__.py
"""
Módulos del sistema de procesamiento de boletas de honorarios
Compatible con v2.x y v3.x (clases *Optimized*).
"""

# Utilidades livianas (ok reexportarlas)
from .utils import (
    install_required_libraries,
    detect_tesseract_cmd,
    detect_poppler_bin,
    dv_ok,
    normaliza_monto,
    clean_text,
    plaus_amount,
    parse_fecha,
    looks_like_person_name,
    iter_files,
    get_month_year_from_date,
    format_currency,
)

# Reexportar clases principales con compatibilidad
try:
    from .ocr_extraction import OCRExtractorOptimized as OCRExtractor
except ImportError:
    from .ocr_extraction import OCRExtractor  # type: ignore

try:
    from .data_processing import DataProcessorOptimized as DataProcessor
except ImportError:
    from .data_processing import DataProcessor  # type: ignore

# Reportes (el nombre no cambió)
from .report_generator import ReportGenerator

# MEMORIA PERSISTENTE - Instancia global
from .memory import Memory
MEMORY = Memory()  # Instancia única para todo el sistema

__version__ = "3.2.0"
__author__ = "Sistema de Procesamiento de Boletas"

# Exportamos tanto nombres "compatibles" como utilidades
__all__ = [
    # Clases públicas (compat alias hacia versiones Optimized si están)
    "OCRExtractor",
    "DataProcessor",
    "ReportGenerator",
    # Memoria
    "Memory",
    "MEMORY",  # Instancia global
    # Utils
    "install_required_libraries",
    "detect_tesseract_cmd",
    "detect_poppler_bin",
    "dv_ok",
    "normaliza_monto",
    "clean_text",
    "plaus_amount",
    "parse_fecha",
    "looks_like_person_name",
    "iter_files",
    "get_month_year_from_date",
    "format_currency",
]