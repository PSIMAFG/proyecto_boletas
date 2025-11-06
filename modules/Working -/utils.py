# modules/utils.py (Corregido para procesamiento paralelo)
"""
Utilidades compartidas para el procesamiento de boletas
Versión 3.1.1 - Corregido para evitar instalaciones en paralelo
"""
import re
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import sys
import os
from .memory import Memory  # ⟵ importa la clase Memory
import json

# instancia global (a nivel de módulo)
MEMORY = Memory()  # carga automática de memory.json

sys.path.append(str(Path(__file__).parent.parent))
from config import *

def install_required_libraries():
    """
    Instala las librerías requeridas si no están disponibles
    SOLO debe ejecutarse desde el proceso principal, NO en workers
    """
    # Verificar si estamos en un proceso hijo
    import multiprocessing
    if multiprocessing.current_process().name != 'MainProcess':
        # En proceso hijo, NO instalar, solo reportar
        return
    
    REQUIRED_LIBS = [
        "opencv-python-headless",
        "pytesseract",
        "pdf2image",
        "pillow",
        "pandas",
        "openpyxl",
        "numpy",
        "pypdf",
        "xlsxwriter"
    ]
    
    missing = []
    for lib in REQUIRED_LIBS:
        lib_name = lib.split("==")[0].split(">=")[0].split("<=")[0].replace("-", "_")
        try:
            __import__(lib_name)
        except ImportError:
            missing.append(lib)
    
    if missing:
        print(f"⚠️ Faltan {len(missing)} librerías. Por favor ejecuta:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True

# NO ejecutar automáticamente al importar en workers
# Solo verificar si estamos en el proceso principal
import multiprocessing
if multiprocessing.current_process().name == 'MainProcess':
    # Solo en proceso principal, verificar (sin instalar automáticamente)
    pass

def run_cmd(cmd):
    """Ejecuta un comando del sistema"""
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return out
    except Exception as e:
        return ""

def detect_tesseract_cmd():
    """Detecta la ubicación del comando Tesseract"""
    env_cmd = os.getenv("TESSERACT_CMD")
    if env_cmd and Path(env_cmd).exists():
        return env_cmd
    
    local_cmd = BASE_DIR / "bin" / "tesseract" / "tesseract.exe"
    if local_cmd.exists():
        return str(local_cmd)
    
    conda_prefix = os.environ.get("CONDA_PREFIX") or ""
    if conda_prefix:
        c = Path(conda_prefix) / "Library" / "bin" / "tesseract.exe"
        if c.exists(): 
            return str(c)
    
    pf = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if pf.exists(): 
        return str(pf)
    
    w = shutil.which("tesseract")
    return w or ""

def detect_poppler_bin():
    """Detecta la ubicación de los binarios de Poppler"""
    env_bin = os.getenv("POPPLER_PATH")
    if env_bin and Path(env_bin).exists():
        return env_bin
    
    local_bin = BASE_DIR / "bin" / "poppler" / "bin"
    if local_bin.exists():
        return str(local_bin)
    
    conda_prefix = os.environ.get("CONDA_PREFIX") or ""
    if conda_prefix:
        b = Path(conda_prefix) / "Library" / "bin"
        if b.exists(): 
            return str(b)
    
    w = shutil.which("pdftoppm") or shutil.which("pdftocairo")
    if w:
        return str(Path(w).parent)
    
    for cand in (
        r"C:\Program Files\poppler\Library\bin",
        r"C:\Program Files\poppler-24.02.0\Library\bin",
        r"C:\Program Files\poppler-23.11.0\Library\bin",
    ):
        if Path(cand).exists():
            return cand
    
    return ""

def dv_ok(rut: str) -> bool:
    """Valida el dígito verificador de un RUT chileno"""
    limpio = rut.replace('.', '').upper()
    if '-' not in limpio:
        return False
    try:
        cuerpo, dv = limpio.split('-')
        if not cuerpo.isdigit():
            return False
    except ValueError:
        return False
    
    s = 0
    m = 2
    for d in cuerpo[::-1]:
        s += int(d) * m
        m = 2 if m == 7 else m + 1
    
    res = 11 - (s % 11)
    dv_calc = 'K' if res == 10 else '0' if res == 11 else str(res)
    return dv_calc == dv

def normaliza_monto(txt: str) -> str:
    """Normaliza un texto de monto a formato numérico"""
    if not txt:
        return ""
    
    t = txt.strip()
    t = re.sub(r'[^\d\.,]', '', t)
    
    # Manejo de separadores de miles y decimales
    if '.' in t and ',' in t:
        t = t.replace('.', '').replace(',', '.')
    elif ',' in t and '.' not in t:
        last = t.split(',')[-1]
        if len(last) == 2:
            t = t.replace(',', '.')
        else:
            t = t.replace(',', '')
    elif '.' in t and ',' not in t:
        parts = t.split('.')
        if len(parts[-1]) == 3 and len(re.sub(r'\D','', t)) > 3:
            t = t.replace('.', '')
    
    t = re.sub(r'[^\d\.]', '', t)
    return t

def clean_text(s: str) -> str:
    """Limpia un texto de caracteres especiales y espacios múltiples"""
    s = s.replace('\x00', ' ')
    s = re.sub(r'[ \t]+', ' ', s)
    return s

def plaus_amount(v: float) -> bool:
    """Verifica si un monto está dentro del rango plausible"""
    return MONTO_MIN <= v <= MONTO_MAX

def parse_fecha(fecha_str: str) -> str:
    """Parsea una fecha en varios formatos y retorna formato ISO"""
    if not fecha_str:
        return ""
    
    s_raw = fecha_str.strip()
    
    # Formato: "15 de marzo de 2024"
    m = FECHA_TEXT_RE.search(s_raw)
    if m:
        d = int(m.group(1))
        mes_txt = m.group(2).lower()
        a = int(m.group(3))
        a = a + 2000 if a < 100 else a
        mes = MESES.get(mes_txt, 0)
        if 1 <= d <= 31 and 1 <= mes <= 12 and 2000 <= a <= 2035:
            try:
                return datetime(a, mes, d).strftime("%Y-%m-%d")
            except ValueError:
                pass
    
    # Formato: DD/MM/YYYY o similar
    s = s_raw.replace('.', '/').replace('-', '/')
    m2 = re.match(r'^\s*(\d{1,2})/(\d{1,2})/(\d{2,4})\s*$', s)
    if m2:
        d, mes, a = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        a = a + 2000 if a < 100 else a
        if 1 <= d <= 31 and 1 <= mes <= 12 and 2000 <= a <= 2035:
            try:
                return datetime(a, mes, d).strftime("%Y-%m-%d")
            except ValueError:
                pass
    
    return ""

def looks_like_person_name(s: str) -> bool:
    """Heurística para determinar si un texto parece ser un nombre de persona"""
    s_clean = re.sub(r'[^A-Za-zÁÉÍÓÚÑáéíóú\s\-]', '', s).strip()
    if not s_clean:
        return False
    
    low = s_clean.lower()
    
    # Palabras que no deben estar en un nombre
    stop_words = {
        'rut','r.u.t','folio','nº','no','nro','n°','prestador','proveedor',
        'contribuyente','emisor','señor','señores','boleta','documento',
        'municipalidad','ilustre','i.','servicio','hospital','universidad',
        'corporación','fundación', 'ministerio','seremi','dirección',
        'departamento','subdirección','gobierno','ssvsa','senda','programa',
        'dir','aps'
    }
    
    if any(word in low for word in stop_words):
        return False
    
    tokens = [t for t in s_clean.split() if len(t) >= 2]
    if len(tokens) < 2 or len(tokens) > 6:
        return False
    
    # Al menos dos tokens con letras
    alpha = sum(1 for t in tokens if re.search(r'[A-Za-zÁÉÍÓÚÑáéíóú]', t))
    return alpha >= 2

def iter_files(root_dir: Path):
    """Itera sobre todos los archivos válidos en un directorio"""
    for p in root_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield p

def get_month_year_from_date(date_str: str) -> tuple:
    """Extrae mes y año de una fecha ISO"""
    try:
        if not date_str:
            return None, None
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.month, dt.year
    except:
        return None, None

def format_currency(amount: float) -> str:
    """Formatea un monto como moneda chilena"""
    try:
        return f"${amount:,.0f}".replace(",", ".")
    except:
        return "$0"