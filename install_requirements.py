# install_requirements.py
"""
Instalación de dependencias para el Sistema de Boletas.
Contexto:
- GUI con Tkinter (no se instala por pip; solo se verifica).
- OCR principal Tesseract; PaddleOCR opcional como fallback.
- Manejo de rutas largas en Windows (Python de Microsoft Store).
"""
import subprocess
import sys
import platform
import os
import venv

def install_package(package: str) -> bool:
    """Instala un paquete con pip (sin cache)"""
    try:
        print(f"Instalando {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-cache-dir", package])
        print(f"✓ {package} instalado correctamente")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ Error instalando {package}")
        return False

def relaunch_in_short_venv_if_needed():
    """
    Si se usa Python de Microsoft Store (ruta larga), relanza el script
    dentro de un venv corto para evitar el límite de rutas (Win32 long paths).
    """
    if os.name == "nt" and "PythonSoftwareFoundation.Python" in sys.executable:
        target = r"C:\p\boletas_venv"
        py = os.path.join(target, "Scripts", "python.exe")
        if not os.path.exists(py):
            print(f"Creando venv corto en {target} ...")
            venv.EnvBuilder(with_pip=True).create(target)
        if os.path.abspath(sys.executable) != os.path.abspath(py):
            print("Reiniciando instalador dentro del venv corto...")
            subprocess.check_call([py, os.path.abspath(__file__)])
            sys.exit(0)

def warn_long_paths():
    """Muestra advertencia si Long Paths podría estar deshabilitado (informativo)."""
    if os.name != "nt":
        return
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem")
        val, _ = winreg.QueryValueEx(k, "LongPathsEnabled")
        if val != 1:
            print("⚠ Windows Long Paths está deshabilitado. Recomendado habilitarlo para evitar errores de pip.")
    except Exception:
        pass  # sin permisos o clave no disponible

def main():
    relaunch_in_short_venv_if_needed()
    warn_long_paths()

    print("=" * 60)
    print("INSTALADOR DE DEPENDENCIAS - SISTEMA DE BOLETAS v3.0")
    print("=" * 60)
    print()

    # Actualizar herramientas de build
    print("Actualizando pip...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])

    # Paquetes base (sin tkinter)
    basic_packages = [
        "opencv-python-headless",
        "pytesseract",
        "pdf2image",
        "pillow",
        "pandas",
        "openpyxl",
        "xlsxwriter",
        "numpy",
        "pypdf",
    ]

    print("\n1. INSTALANDO PAQUETES BÁSICOS")
    print("-" * 40)
    failed = []
    for pkg in basic_packages:
        if not install_package(pkg):
            failed.append(pkg)

    print("\n2. INSTALANDO PADDLEOCR")
    print("-" * 40)
    os_type = platform.system()
    machine = platform.machine()
    print(f"Sistema detectado: {os_type} {machine}")

    # Versiones compatibles (evitan dependencias pesadas)
    paddle_pkg = "paddlepaddle==3.1.2"
    paddleocr_pkg = "paddleocr==2.7.0.3"

    if not install_package(paddle_pkg):
        print("\n⚠ ADVERTENCIA: PaddlePaddle no se pudo instalar.")
        print("Puedes intentar instalarlo manualmente con:")
        print(f"  pip install {paddle_pkg}")
        print("\nPara GPU con CUDA (si corresponde):")
        print("  pip install paddlepaddle-gpu")
        failed.append(paddle_pkg)

    if not install_package(paddleocr_pkg):
        print("\n⚠ ADVERTENCIA: PaddleOCR no se pudo instalar.")
        print("Intenta instalarlo manualmente con:")
        print(f"  pip install {paddleocr_pkg}")
        failed.append(paddleocr_pkg)

    print("\n3. VERIFICANDO INSTALACIÓN")
    print("-" * 40)

    # Verificación de imports
    installed, not_installed = [], []
    to_check = basic_packages + [paddle_pkg, paddleocr_pkg]

    module_map = {
        "opencv-python-headless": "cv2",
        "pillow": "PIL",
        "pypdf": "pypdf",
        "pdf2image": "pdf2image",
        "paddlepaddle": "paddle",
        "paddleocr": "paddleocr",
    }

    for pkg in to_check:
        base = pkg.split("==")[0]
        mod = module_map.get(base, base.replace("-", "_"))
        try:
            __import__(mod)
            installed.append(base)
        except Exception:
            not_installed.append(base)

    # Tkinter: solo verificación (no se instala por pip)
    try:
        import tkinter  # noqa: F401
        tk_status = "✓ Tkinter disponible"
    except Exception:
        tk_status = "✗ Tkinter NO disponible (instala Python desde python.org con tcl/tk)"
    print(f"\nEstado Tkinter: {tk_status}")

    print("\n✓ Paquetes instalados correctamente:")
    for p in installed:
        print(f"  - {p}")

    if not_installed:
        print("\n✗ Paquetes que requieren instalación manual:")
        for p in not_installed:
            print(f"  - {p}")

    print("\n" + "=" * 60)
    print("INSTALACIÓN DE SOFTWARE ADICIONAL REQUERIDO")
    print("=" * 60)
    print("\n⚠ Además de las librerías Python, necesitas instalar:")
    print("1) TESSERACT OCR")
    print("   - Windows: https://github.com/tesseract-ocr/tesseract")
    print("   - Linux: sudo apt-get install tesseract-ocr tesseract-ocr-spa")
    print("   - macOS: brew install tesseract")
    print("\n2) POPPLER (para PDFs)")
    print("   - Windows: https://github.com/oschwartz10612/poppler-windows/releases")
    print("   - Linux: sudo apt-get install poppler-utils")
    print("   - macOS: brew install poppler")
    print("\n3) IDIOMA ESPAÑOL PARA TESSERACT")
    print("   - Descargar spa.traineddata de https://github.com/tesseract-ocr/tessdata")
    print("   - Copiarlo a la carpeta tessdata de Tesseract")

    print("\n" + "=" * 60)

    # Heurística de éxito:
    # - OK absoluto si no falta nada
    # - OK funcional si solo faltan paddlepaddle/paddleocr (la app corre con Tesseract)
    missing = set(not_installed)
    ok_even_if_missing_paddle = missing and missing.issubset({"paddlepaddle", "paddleocr"})
    if not not_installed or ok_even_if_missing_paddle:
        if ok_even_if_missing_paddle:
            print("✓ INSTALACIÓN COMPLETADA (sin PaddleOCR). El sistema funcionará con Tesseract.")
        else:
            print("✓ INSTALACIÓN COMPLETADA EXITOSAMENTE")
        print("\nPuedes ejecutar el sistema con:")
        print("  python main_enhanced.py")
        exit_code = 0
    else:
        print("⚠ INSTALACIÓN PARCIALMENTE COMPLETADA")
        print("Instala los paquetes faltantes manualmente antes de ejecutar el sistema.")
        exit_code = 1

    print("=" * 60)
    print(f"\nRESUMEN ▶ OK={len(installed)} | FALTAN={len(not_installed)}")
    input("\nPresiona Enter para terminar...")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
