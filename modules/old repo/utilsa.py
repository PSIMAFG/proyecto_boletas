# ============================================================================
# modules/utils.py
# ============================================================================
"""
Utilidades compartidas
"""
from pathlib import Path
import re
import os
import shutil
import subprocess

def find_files(directory, extensions):
    """Busca archivos con las extensiones especificadas"""
    directory = Path(directory)
    for ext in extensions:
        for file_path in directory.rglob(f"*{ext}"):
            if file_path.is_file():
                yield file_path

def validate_rut(rut):
    """Valida un RUT chileno"""
    if not rut:
        return False
    
    # Limpiar RUT
    rut = rut.upper().replace('.', '').replace('-', '')
    
    if len(rut) < 2:
        return False
    
    try:
        numero = int(rut[:-1])
        dv = rut[-1]
        
        # Calcular dígito verificador
        suma = 0
        multiplicador = 2
        
        for digit in reversed(str(numero)):
            suma += int(digit) * multiplicador
            multiplicador = multiplicador + 1 if multiplicador < 7 else 2
        
        resto = suma % 11
        dv_calculado = 'K' if resto == 1 else '0' if resto == 0 else str(11 - resto)
        
        return dv == dv_calculado
        
    except (ValueError, IndexError):
        return False

def clean_amount(text):
    """Limpia y normaliza un monto"""
    if not text:
        return ""
    
    # Eliminar todo excepto números, puntos y comas
    text = re.sub(r'[^\d.,]', '', text)
    
    # Manejar formato chileno (punto para miles, coma para decimales)
    if '.' in text and ',' in text:
        # Formato chileno: 1.234.567,89
        text = text.replace('.', '').replace(',', '.')
    elif ',' in text:
        # Puede ser miles o decimales
        parts = text.split(',')
        if len(parts[-1]) == 3:
            # Es separador de miles: 1,234,567
            text = text.replace(',', '')
        else:
            # Es decimal: 1234,56
            text = text.replace(',', '.')
    elif '.' in text:
        # Puede ser miles o decimales
        parts = text.split('.')
        if len(parts) > 2 or (len(parts) == 2 and len(parts[-1]) == 3):
            # Es separador de miles: 1.234.567
            text = text.replace('.', '')
    
    return text

def format_date(date_str):
    """Formatea una fecha al formato ISO"""
    if not date_str:
        return ""
    
    # Intentar parsear diferentes formatos
    import datetime
    
    # Patrones comunes
    patterns = [
        "%d/%m/%Y",
        "%d-%m-%Y", 
        "%d.%m.%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%Y-%m-%d"
    ]
    
    for pattern in patterns:
        try:
            dt = datetime.datetime.strptime(date_str.strip(), pattern)
            # Ajustar años de 2 dígitos
            if dt.year < 100:
                if dt.year < 50:
                    dt = dt.replace(year=dt.year + 2000)
                else:
                    dt = dt.replace(year=dt.year + 1900)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return date_str

def find_tesseract():
    """Encuentra la ruta de Tesseract"""
    # Windows paths
    windows_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\tesseract\tesseract.exe"
    ]
    
    for path in windows_paths:
        if Path(path).exists():
            return path
    
    # Buscar en PATH
    tesseract = shutil.which("tesseract")
    if tesseract:
        return tesseract
    
    return None

def find_poppler():
    """Encuentra la ruta de Poppler"""
    # Windows paths
    windows_paths = [
        r"C:\poppler\Library\bin",
        r"C:\Program Files\poppler\Library\bin",
        r"C:\tools\poppler\Library\bin"
    ]
    
    for path in windows_paths:
        if Path(path).exists():
            return path
    
    # Buscar pdftoppm en PATH
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        return str(Path(pdftoppm).parent)
    
    return None


