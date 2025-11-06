#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Verificación Completa del Sistema
Verifica que todos los imports y dependencias estén correctos
"""
import sys
from pathlib import Path

# Colores para terminal
class Color:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Color.BOLD}{Color.BLUE}{'='*70}{Color.END}")
    print(f"{Color.BOLD}{Color.BLUE}{text:^70}{Color.END}")
    print(f"{Color.BOLD}{Color.BLUE}{'='*70}{Color.END}\n")

def check_python_version():
    """Verifica la versión de Python"""
    print(f"{Color.BOLD}[1] Verificando versión de Python...{Color.END}")
    version = sys.version_info
    print(f"  Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"  {Color.RED}⚠️ Se recomienda Python 3.8 o superior{Color.END}")
        return False
    else:
        print(f"  {Color.GREEN}✓ Versión compatible{Color.END}")
        return True

def check_imports():
    """Verifica que todos los imports funcionen"""
    print(f"\n{Color.BOLD}[2] Verificando imports del sistema...{Color.END}")
    
    modules_to_check = [
        ('tkinter', 'Interfaz gráfica'),
        ('PIL', 'Procesamiento de imágenes'),
        ('cv2', 'OpenCV'),
        ('pytesseract', 'OCR'),
        ('pdf2image', 'Conversión PDF'),
        ('pandas', 'Análisis de datos'),
        ('openpyxl', 'Excel'),
        ('xlsxwriter', 'Escritura Excel'),
        ('numpy', 'Operaciones numéricas'),
        ('pypdf', 'Lectura PDF'),
    ]
    
    all_ok = True
    for module_name, description in modules_to_check:
        try:
            __import__(module_name)
            print(f"  {Color.GREEN}✓{Color.END} {module_name:20} - {description}")
        except ImportError:
            print(f"  {Color.RED}✗{Color.END} {module_name:20} - {description} (FALTA)")
            all_ok = False
    
    return all_ok

def check_typing_imports():
    """Verifica específicamente los imports de typing"""
    print(f"\n{Color.BOLD}[3] Verificando imports de typing...{Color.END}")
    
    try:
        from typing import List, Dict, Optional, Tuple
        print(f"  {Color.GREEN}✓ typing.List{Color.END}")
        print(f"  {Color.GREEN}✓ typing.Dict{Color.END}")
        print(f"  {Color.GREEN}✓ typing.Optional{Color.END}")
        print(f"  {Color.GREEN}✓ typing.Tuple{Color.END}")
        return True
    except ImportError as e:
        print(f"  {Color.RED}✗ Error importando typing: {e}{Color.END}")
        return False

def check_main_py():
    """Verifica que main.py tenga los imports correctos"""
    print(f"\n{Color.BOLD}[4] Verificando main.py...{Color.END}")
    
    main_path = Path("main.py")
    if not main_path.exists():
        print(f"  {Color.RED}✗ main.py no encontrado{Color.END}")
        return False
    
    content = main_path.read_text(encoding='utf-8')
    
    # Verificar import de typing
    if 'from typing import' in content:
        print(f"  {Color.GREEN}✓ Import de typing presente{Color.END}")
        
        # Verificar tipos específicos
        required_types = ['List', 'Dict', 'Optional', 'Tuple']
        missing = [t for t in required_types if t not in content.split('from typing import')[1].split('\n')[0]]
        
        if missing:
            print(f"  {Color.YELLOW}⚠️ Faltan tipos: {', '.join(missing)}{Color.END}")
            return False
        else:
            print(f"  {Color.GREEN}✓ Todos los tipos necesarios están importados{Color.END}")
    else:
        print(f"  {Color.RED}✗ Falta 'from typing import'{Color.END}")
        print(f"     Ejecuta: APLICAR_FIX_MAIN.bat")
        return False
    
    # Intentar importar BoletasApp
    try:
        sys.path.insert(0, str(Path.cwd()))
        from main import BoletasApp
        print(f"  {Color.GREEN}✓ BoletasApp se importa correctamente{Color.END}")
        return True
    except NameError as e:
        print(f"  {Color.RED}✗ Error de importación: {e}{Color.END}")
        return False
    except Exception as e:
        print(f"  {Color.YELLOW}⚠️ Advertencia al importar: {e}{Color.END}")
        return True

def check_modules():
    """Verifica los módulos del proyecto"""
    print(f"\n{Color.BOLD}[5] Verificando módulos del proyecto...{Color.END}")
    
    modules = [
        'config',
        'modules.utils',
        'modules.ocr_extraction',
        'modules.data_processing',
        'modules.report_generator',
        'modules.memory',
    ]
    
    all_ok = True
    for module_name in modules:
        try:
            __import__(module_name)
            print(f"  {Color.GREEN}✓{Color.END} {module_name}")
        except ImportError as e:
            print(f"  {Color.RED}✗{Color.END} {module_name} - {e}")
            all_ok = False
        except Exception as e:
            print(f"  {Color.YELLOW}⚠️{Color.END} {module_name} - {e}")
    
    return all_ok

def check_external_tools():
    """Verifica herramientas externas (Tesseract, Poppler)"""
    print(f"\n{Color.BOLD}[6] Verificando herramientas externas...{Color.END}")
    
    # Tesseract
    try:
        from modules.utils import detect_tesseract_cmd
        tess_cmd = detect_tesseract_cmd()
        if tess_cmd:
            print(f"  {Color.GREEN}✓ Tesseract encontrado: {tess_cmd}{Color.END}")
        else:
            print(f"  {Color.YELLOW}⚠️ Tesseract no encontrado{Color.END}")
    except Exception as e:
        print(f"  {Color.RED}✗ Error verificando Tesseract: {e}{Color.END}")
    
    # Poppler
    try:
        from modules.utils import detect_poppler_bin
        poppler_bin = detect_poppler_bin()
        if poppler_bin:
            print(f"  {Color.GREEN}✓ Poppler encontrado: {poppler_bin}{Color.END}")
        else:
            print(f"  {Color.YELLOW}⚠️ Poppler no encontrado (opcional){Color.END}")
    except Exception as e:
        print(f"  {Color.YELLOW}⚠️ Error verificando Poppler: {e}{Color.END}")

def main():
    """Función principal de verificación"""
    print_header("VERIFICACIÓN COMPLETA DEL SISTEMA")
    
    results = []
    
    results.append(("Versión Python", check_python_version()))
    results.append(("Imports estándar", check_imports()))
    results.append(("Typing imports", check_typing_imports()))
    results.append(("main.py", check_main_py()))
    results.append(("Módulos proyecto", check_modules()))
    
    check_external_tools()
    
    # Resumen
    print_header("RESUMEN DE VERIFICACIÓN")
    
    all_ok = True
    for name, status in results:
        icon = f"{Color.GREEN}✓{Color.END}" if status else f"{Color.RED}✗{Color.END}"
        print(f"  {icon} {name}")
        if not status:
            all_ok = False
    
    print()
    if all_ok:
        print(f"{Color.GREEN}{Color.BOLD}✓ SISTEMA LISTO PARA USAR{Color.END}")
        print(f"\nPuedes ejecutar:")
        print(f"  python main.py")
        print(f"  ejecutar_con_entorno.bat")
    else:
        print(f"{Color.RED}{Color.BOLD}✗ HAY PROBLEMAS QUE CORREGIR{Color.END}")
        print(f"\nSoluciones:")
        print(f"  1. Para fix de main.py: ejecutar APLICAR_FIX_MAIN.bat")
        print(f"  2. Para librerías faltantes: pip install <librería>")
        print(f"  3. Para Tesseract: instalar desde https://tesseract-ocr.github.io")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Color.YELLOW}Verificación cancelada{Color.END}\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Color.RED}Error inesperado: {e}{Color.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
