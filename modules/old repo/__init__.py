# ============================================================================
# modules/__init__.py
# ============================================================================
"""
Módulos del sistema de boletas
"""
from .config import Config
from .ocr_processor import OCRProcessor
from .data_extractor import DataExtractor
from .report_generator import ReportGenerator
from .utils import *

__version__ = "3.0.0"
__all__ = [
    'Config',
    'OCRProcessor', 
    'DataExtractor',
    'ReportGenerator'
]


