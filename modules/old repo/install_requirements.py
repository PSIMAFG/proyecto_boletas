# install_requirements_fixed.py
"""
Script de instalación mejorado para el Sistema de Boletas v3.0
Maneja correctamente conda, venv y compatibilidad con PaddleOCR
"""
import subprocess
import sys
import platform
import os
from pathlib import Path
import json

def detect_environment():
    """Detecta el tipo de entorno Python (conda, venv, system)"""
    env_info = {
        'type': 'system',
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}",
        'executable': sys.executable,
        'is_conda': False,
        'is_venv': False,
        'is_windows_store': False
    }
    
    # Detectar Conda
    if 'CONDA_DEFAULT_ENV' in os.environ or 'conda' in sys.executable.lower():
        env_info['type'] = 'conda'
        env_info['is_conda'] = True
        env_info['conda_env'] = os.environ.get('CONDA_DEFAULT_ENV', 'unknown')
        print(f"✓ Entorno Conda detectado: {env_info['conda_env']}")
    
    # Detectar venv
    elif hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        env_info['type'] = 'venv'
        env_info['is_venv'] = True
        print("✓ Virtual environment detectado")
    
    # Detectar Windows Store Python
    if 'WindowsApps' in sys.executable or 'PythonSoftwareFoundation' in sys.executable:
        env_info['is_windows_store'] = True
        print("⚠ Python de Windows Store detectado - pueden haber limitaciones")
    
    return env_info

def run_command(cmd, check=True, capture=True):
    """Ejecuta un comando y retorna el resultado"""
    try:
        if capture:
            result = subprocess.run(cmd, check=check, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, check=check)
            return result.returncode == 0, "", ""
    except subprocess.CalledProcessError as e:
        return False, "", str(e)
    except Exception as e:
        return False, "", str(e)

def install_with_pip(package, extra_args=None):
    """Instala un paquete usando pip con manejo de errores mejorado"""
    cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir"]
    
    if extra_args:
        cmd.extend(extra_args)
    
    cmd.append(package)
    
    print(f"Instalando {package}...")
    success, stdout, stderr = run_command(cmd, check=False)
    
    if success:
        print(f"✓ {package} instalado correctamente")
    else:
        print(f"✗ Error instalando {package}")
        if stderr:
            print(f"  Error: {stderr[:200]}...")
    
    return success

def install_with_conda(package, channel=None):
    """Instala un paquete usando conda"""
    cmd = ["conda", "install", "-y"]
    
    if channel:
        cmd.extend(["-c", channel])
    
    cmd.append(package)
    
    print(f"Instalando {package} con conda...")
    success, stdout, stderr = run_command(cmd, check=False)
    
    if success:
        print(f"✓ {package} instalado correctamente con conda")
    else:
        print(f"✗ Error instalando {package} con conda")
    
    return success

def get_paddle_package(env_info):
    """Determina el paquete de PaddlePaddle correcto para el entorno"""
    os_type = platform.system().lower()
    py_version = env_info['python_version']
    
    # Matriz de compatibilidad simplificada
    paddle_versions = {
        ("windows", "3.8"): "paddlepaddle==2.5.2",
        ("windows", "3.9"): "paddlepaddle==2.5.2",
        ("windows", "3.10"): "paddlepaddle==2.5.2",
        ("windows", "3.11"): "paddlepaddle==2.6.1",
        ("windows", "3.12"): "paddlepaddle==2.6.1",
        ("linux", "3.8"): "paddlepaddle==2.6.1",
        ("linux", "3.9"): "paddlepaddle==2.6.1",
        ("linux", "3.10"): "paddlepaddle==2.6.1",
        ("linux", "3.11"): "paddlepaddle==2.6.1",
        ("linux", "3.12"): "paddlepaddle==2.6.1",
        ("darwin", "3.9"): "paddlepaddle==2.5.2",
        ("darwin", "3.10"): "paddlepaddle==2.5.2",
        ("darwin", "3.11"): "paddlepaddle==2.5.2",
    }
    
    key = (os_type, py_version)
    
    # Si no hay versión específica, usar la más reciente estable
    if key not in paddle_versions:
        print(f"⚠ No hay versión específica de PaddlePaddle para {os_type} Python {py_version}")
        if py_version >= "3.12":
            return "paddlepaddle==2.6.1"
        else:
            return "paddlepaddle==2.5.2"
    
    return paddle_versions[key]

def install_paddleocr_complete(env_info):
    """Instala PaddleOCR con todas sus dependencias de manera robusta"""
    success_paddle = False
    success_ocr = False
    
    # Paso 1: Instalar PaddlePaddle
    paddle_package = get_paddle_package(env_info)
    print(f"\n📦 Instalando PaddlePaddle: {paddle_package}")
    
    if env_info['is_conda']:
        # Intentar con conda primero
        success_paddle = install_with_conda("paddlepaddle", channel="paddle")
        if not success_paddle:
            success_paddle = install_with_pip(paddle_package)
    else:
        success_paddle = install_with_pip(paddle_package)
    
    if not success_paddle:
        print("\n⚠ PaddlePaddle no se pudo instalar automáticamente")
        print("Intenta manualmente:")
        print(f"  pip install {paddle_package}")
        return False, False
    
    # Paso 2: Instalar dependencias de PaddleOCR primero
    print("\n📦 Instalando dependencias de PaddleOCR...")
    
    # Dependencias críticas en orden
    dependencies = [
        "shapely>=2.0.0",
        "scikit-image",
        "imgaug",
        "pyclipper",
        "lmdb",
        "rapidfuzz",
        "opencv-python",
        "opencv-contrib-python",
        "cython",
        "lxml",
        "premailer",
        "attrdict",
        "PyYAML",
        "python-docx",
        "beautifulsoup4",
        "fonttools>=4.0.0",
        "fire>=0.3.0",
    ]
    
    failed_deps = []
    for dep in dependencies:
        if not install_with_pip(dep):
            failed_deps.append(dep)
    
    # Paso 3: Instalar PaddleOCR
    print("\n📦 Instalando PaddleOCR...")
    
    # Para Python >= 3.12, usar versión sin PyMuPDF si hay problemas
    if env_info['python_version'] >= "3.12":
        # Intentar instalar sin PyMuPDF
        success_ocr = install_with_pip("paddleocr==2.7.0.3", ["--no-deps"])
        if success_ocr:
            print("✓ PaddleOCR instalado sin PyMuPDF (Python 3.12+)")
            # Instalar pdf2docx como alternativa
            install_with_pip("pdf2docx")
    else:
        # Versión normal con todas las dependencias
        success_ocr = install_with_pip("paddleocr==2.7.0.3")
    
    return success_paddle, success_ocr

def verify_imports():
    """Verifica qué módulos están instalados correctamente"""
    modules_to_check = {
        'cv2': 'OpenCV',
        'pytesseract': 'PyTesseract',
        'pdf2image': 'PDF2Image',
        'PIL': 'Pillow',
        'pandas': 'Pandas',
        'openpyxl': 'OpenPyXL',
        'xlsxwriter': 'XlsxWriter',
        'numpy': 'NumPy',
        'pypdf': 'PyPDF',
        'paddle': 'PaddlePaddle',
        'paddleocr': 'PaddleOCR'
    }
    
    installed = []
    not_installed = []
    
    for module, name in modules_to_check.items():
        try:
            if module == 'paddleocr':
                # Verificación especial para PaddleOCR
                from paddleocr import PaddleOCR
                test = PaddleOCR(use_angle_cls=False, lang='en', show_log=False)
                installed.append(name)
            else:
                __import__(module)
                installed.append(name)
        except ImportError as e:
            not_installed.append(name)
        except Exception as e:
            # Puede estar instalado pero con problemas de configuración
            if 'paddle' in module.lower():
                installed.append(f"{name} (con advertencias)")
            else:
                not_installed.append(name)
    
    return installed, not_installed

def create_environment_script(env_info):
    """Crea un script .bat/.sh para configurar el entorno"""
    os_type = platform.system().lower()
    
    if os_type == "windows":
        script_name = "setup_environment.bat"
        content = f"""@echo off
echo Configurando entorno para Sistema de Boletas v3.0...

REM Configurar variables de entorno
set PYTHONPATH=%CD%
set PYTHONIOENCODING=utf-8

REM Activar entorno si existe
"""
        if env_info['is_conda']:
            content += f"""
call conda activate {env_info.get('conda_env', 'base')}
"""
        
        content += """
REM Verificar instalación
python -c "import paddle; print('PaddlePaddle OK')"
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"

echo.
echo Entorno configurado. Ejecuta: python main_enhanced.py
pause
"""
    else:  # Linux/Mac
        script_name = "setup_environment.sh"
        content = f"""#!/bin/bash
echo "Configurando entorno para Sistema de Boletas v3.0..."

# Configurar variables de entorno
export PYTHONPATH=$PWD
export PYTHONIOENCODING=utf-8

# Activar entorno si existe
"""
        if env_info['is_conda']:
            content += f"""
conda activate {env_info.get('conda_env', 'base')}
"""
        
        content += """
# Verificar instalación
python -c "import paddle; print('PaddlePaddle OK')"
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"

echo ""
echo "Entorno configurado. Ejecuta: python main_enhanced.py"
"""
    
    with open(script_name, 'w') as f:
        f.write(content)
    
    if os_type != "windows":
        os.chmod(script_name, 0o755)
    
    print(f"\n✓ Script de configuración creado: {script_name}")

def main():
    print("=" * 70)
    print("INSTALADOR MEJORADO - SISTEMA DE BOLETAS v3.0")
    print("=" * 70)
    
    # Detectar entorno
    env_info = detect_environment()
    print(f"\n📊 Entorno detectado:")
    print(f"  • Tipo: {env_info['type']}")
    print(f"  • Python: {env_info['python_version']} ({env_info['executable']})")
    print(f"  • Sistema: {platform.system()} {platform.machine()}")
    
    # Advertencias especiales
    if env_info['is_windows_store']:
        print("\n⚠ ADVERTENCIA: Python de Windows Store detectado")
        print("  Recomendado: Instalar Python desde python.org para evitar problemas")
    
    if env_info['python_version'] >= "3.12":
        print("\n⚠ ADVERTENCIA: Python 3.12+ detectado")
        print("  PaddleOCR puede tener compatibilidad limitada")
    
    # Actualizar pip
    print("\n📦 Actualizando herramientas de construcción...")
    install_with_pip("pip", ["--upgrade"])
    install_with_pip("setuptools wheel", ["--upgrade"])
    
    # Instalar paquetes básicos
    print("\n📦 Instalando paquetes básicos...")
    basic_packages = [
        "opencv-python-headless",
        "pytesseract",
        "pdf2image",
        "pillow",
        "pandas",
        "openpyxl",
        "xlsxwriter",
        "numpy",
        "pypdf"
    ]
    
    failed_basic = []
    for package in basic_packages:
        if not install_with_pip(package):
            failed_basic.append(package)
    
    # Instalar PaddleOCR
    print("\n" + "=" * 50)
    print("INSTALANDO PADDLEOCR")
    print("=" * 50)
    
    paddle_ok, ocr_ok = install_paddleocr_complete(env_info)
    
    # Verificar instalaciones
    print("\n" + "=" * 50)
    print("VERIFICANDO INSTALACIÓN")
    print("=" * 50)
    
    installed, not_installed = verify_imports()
    
    print("\n✅ Módulos instalados correctamente:")
    for module in installed:
        print(f"  • {module}")
    
    if not_installed:
        print("\n❌ Módulos NO instalados:")
        for module in not_installed:
            print(f"  • {module}")
    
    # Crear script de configuración
    create_environment_script(env_info)
    
    # Instrucciones finales
    print("\n" + "=" * 70)
    print("PASOS SIGUIENTES")
    print("=" * 70)
    
    if not not_installed or (len(not_installed) == 1 and 'PaddleOCR' in not_installed):
        print("\n✅ INSTALACIÓN EXITOSA")
        print("\nEl sistema puede funcionar:")
        print("  • Con Tesseract solamente (si PaddleOCR falló)")
        print("  • Con ambos motores (si todo se instaló)")
        print("\nEjecuta el sistema con:")
        print(f"  python main_enhanced.py")
    else:
        print("\n⚠ INSTALACIÓN PARCIAL")
        print("\nPaquetes críticos faltantes. Opciones:")
        print("1. Intentar instalación manual de los faltantes")
        print("2. Usar solo Tesseract (sin PaddleOCR)")
        print("3. Crear un entorno conda limpio:")
        print("   conda create -n boletas python=3.10")
        print("   conda activate boletas")
        print("   python install_requirements_fixed.py")
    
    print("\n" + "=" * 70)
    print("INSTALACIÓN DE SOFTWARE EXTERNO REQUERIDO")
    print("=" * 70)
    
    print("\n1. TESSERACT OCR (obligatorio)")
    print("   • Windows: https://github.com/tesseract-ocr/tesseract")
    print("   • Linux: sudo apt-get install tesseract-ocr tesseract-ocr-spa")
    print("   • Mac: brew install tesseract")
    
    print("\n2. POPPLER (para PDFs)")
    print("   • Windows: https://github.com/oschwartz10612/poppler-windows")
    print("   • Linux: sudo apt-get install poppler-utils")
    print("   • Mac: brew install poppler")
    
    print("\n3. Configurar rutas (si no se detectan automáticamente):")
    if platform.system() == "Windows":
        print("   set TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
        print("   set POPPLER_PATH=C:\\poppler\\Library\\bin")
    else:
        print("   export TESSERACT_CMD=/usr/bin/tesseract")
        print("   export POPPLER_PATH=/usr/bin")
    
    print("\n" + "=" * 70)
    input("\nPresiona Enter para terminar...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Instalación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
        input("\nPresiona Enter para terminar...")
        sys.exit(1)