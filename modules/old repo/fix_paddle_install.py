# fix_paddle_install.py
"""
Instalador específico para resolver problemas de compatibilidad NumPy/PaddleOCR
Para Python 3.10 en conda
"""
import subprocess
import sys
import os

def run_install(cmd):
    """Ejecuta comando de instalación"""
    print(f"Ejecutando: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Éxito")
        return True
    else:
        print(f"✗ Error: {result.stderr[:200]}")
        return False

def main():
    print("=" * 70)
    print("INSTALADOR ESPECÍFICO PARA PYTHON 3.10 + PADDLEOCR")
    print("=" * 70)
    
    # Verificar versión de Python
    print(f"\nPython actual: {sys.version}")
    if not sys.version.startswith("3.10"):
        print("\n⚠ ERROR: Este script requiere Python 3.10")
        print("Ejecuta primero:")
        print("  conda create -n boletas310 python=3.10 -y")
        print("  conda activate boletas310")
        print("  python fix_paddle_install.py")
        return
    
    print("\n✓ Python 3.10 detectado - Continuando...\n")
    
    # PASO 1: Limpiar instalaciones previas problemáticas
    print("PASO 1: Limpiando instalaciones previas...")
    packages_to_remove = ["numpy", "opencv-python", "opencv-python-headless", 
                         "opencv-contrib-python", "paddlepaddle", "paddleocr"]
    
    for pkg in packages_to_remove:
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", pkg], 
                      capture_output=True)
    print("✓ Limpieza completada\n")
    
    # PASO 2: Instalar NumPy específico compatible
    print("PASO 2: Instalando NumPy compatible...")
    if not run_install([sys.executable, "-m", "pip", "install", "numpy==1.23.5"]):
        print("Error instalando NumPy")
        return
    
    # PASO 3: Instalar OpenCV compatible
    print("\nPASO 3: Instalando OpenCV compatible...")
    if not run_install([sys.executable, "-m", "pip", "install", 
                       "opencv-python==4.6.0.66", "opencv-contrib-python==4.6.0.66"]):
        print("Error instalando OpenCV")
        return
    
    # PASO 4: Instalar PaddlePaddle para Python 3.10
    print("\nPASO 4: Instalando PaddlePaddle...")
    if os.name == "nt":  # Windows
        # Para Windows con Python 3.10
        paddle_url = "https://paddle-wheel.bj.bcebos.com/2.5.2/windows/windows-cpu-avx-mkl/paddlepaddle-2.5.2-cp310-cp310-win_amd64.whl"
        if not run_install([sys.executable, "-m", "pip", "install", paddle_url]):
            # Fallback a versión PyPI
            if not run_install([sys.executable, "-m", "pip", "install", "paddlepaddle==2.5.2"]):
                print("Error instalando PaddlePaddle")
                return
    else:  # Linux/Mac
        if not run_install([sys.executable, "-m", "pip", "install", "paddlepaddle==2.5.2"]):
            print("Error instalando PaddlePaddle")
            return
    
    # PASO 5: Instalar dependencias de PaddleOCR en orden correcto
    print("\nPASO 5: Instalando dependencias de PaddleOCR...")
    deps = [
        "shapely==2.0.2",
        "scikit-image==0.21.0",
        "imgaug==0.4.0",
        "pyclipper==1.3.0.post5",
        "lmdb==1.4.1",
        "rapidfuzz==3.5.0",
        "Pillow==10.0.0",
        "PyMuPDF==1.23.8",  # Versión compatible con Python 3.10
        "attrdict==2.0.1",
        "PyYAML==6.0.1",
        "python-docx==1.1.0",
        "beautifulsoup4==4.12.2",
        "fonttools==4.45.0",
        "fire==0.5.0",
        "pdf2docx==0.5.6"
    ]
    
    for dep in deps:
        if not run_install([sys.executable, "-m", "pip", "install", dep]):
            print(f"Advertencia: {dep} no se instaló")
    
    # PASO 6: Instalar PaddleOCR
    print("\nPASO 6: Instalando PaddleOCR...")
    if not run_install([sys.executable, "-m", "pip", "install", "paddleocr==2.7.0.3"]):
        print("Error instalando PaddleOCR")
        return
    
    # PASO 7: Instalar resto de paquetes necesarios
    print("\nPASO 7: Instalando paquetes del sistema de boletas...")
    other_packages = [
        "pytesseract==0.3.10",
        "pdf2image==1.16.3",
        "pandas==2.0.3",
        "openpyxl==3.1.2",
        "xlsxwriter==3.1.9",
        "pypdf==3.17.0"
    ]
    
    for pkg in other_packages:
        if not run_install([sys.executable, "-m", "pip", "install", pkg]):
            print(f"Advertencia: {pkg} no se instaló")
    
    # VERIFICACIÓN FINAL
    print("\n" + "=" * 70)
    print("VERIFICACIÓN FINAL")
    print("=" * 70)
    
    print("\nProbando importaciones...")
    
    tests = [
        ("NumPy", "import numpy; print(f'  NumPy {numpy.__version__}')"),
        ("OpenCV", "import cv2; print(f'  OpenCV {cv2.__version__}')"),
        ("PaddlePaddle", "import paddle; print(f'  Paddle {paddle.__version__}')"),
        ("PaddleOCR", "from paddleocr import PaddleOCR; print('  PaddleOCR OK')"),
        ("Tesseract", "import pytesseract; print('  Tesseract OK')"),
    ]
    
    all_ok = True
    for name, test in tests:
        try:
            exec(test)
        except Exception as e:
            print(f"  ✗ {name}: {str(e)[:50]}")
            all_ok = False
    
    print("\n" + "=" * 70)
    
    if all_ok:
        print("✅ INSTALACIÓN EXITOSA")
        print("\nAhora puedes ejecutar:")
        print("  python main_enhanced.py")
        print("\nSelecciona 'PaddleOCR' o 'Auto' como motor OCR en la interfaz")
    else:
        print("⚠ INSTALACIÓN PARCIAL")
        print("\nAlgunos componentes no se instalaron correctamente.")
        print("El sistema puede funcionar con Tesseract solamente.")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
    input("\nPresiona Enter para terminar...")