# install_requirements.py
"""
Script de instalación de todas las dependencias necesarias para el sistema
Incluye PaddleOCR y todas las librerías requeridas
"""
import subprocess
import sys
import platform
import os
import venv

def install_package(package):
    """Instala un paquete con pip (sin cache para evitar residuos)"""
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
    Si se ejecuta con el Python de Microsoft Store (ruta larga),
    relanza el script dentro de un venv en C:\p\boletas_venv para evitar el límite de rutas.
    """
    # Detecta Python de Microsoft Store por la ruta al ejecutable
    if os.name == "nt" and "PythonSoftwareFoundation.Python" in sys.executable:
        target = r"C:\p\boletas_venv"
        py = os.path.join(target, "Scripts", "python.exe")
        if not os.path.exists(py):
            print(f"Creando venv corto en {target} ...")
            venv.EnvBuilder(with_pip=True).create(target)
        # Si no estamos usando ese Python, relanzamos
        if os.path.abspath(sys.executable) != os.path.abspath(py):
            print("Reiniciando instalador dentro del venv corto...")
            subprocess.check_call([py, os.path.abspath(__file__)])
            sys.exit(0)

def warn_long_paths():
    """Advertencia si Long Paths de Windows podría estar deshabilitado."""
    if os.name != "nt":
        return
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem")
        val, _ = winreg.QueryValueEx(k, "LongPathsEnabled")
        if val != 1:
            print("⚠ Windows Long Paths está deshabilitado. Recomendado habilitarlo para evitar errores de pip.")
    except Exception:
        # Sin permisos o clave no encontrada: solo informativo
        pass

def main():
    relaunch_in_short_venv_if_needed()
    warn_long_paths()

    print("=" * 60)
    print("INSTALADOR DE DEPENDENCIAS - SISTEMA DE BOLETAS v3.0")
    print("=" * 60)
    print()

    # Actualizar pip primero
    print("Actualizando pip...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])

    # Lista de paquetes básicos (sin tkinter)
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
    for package in basic_packages:
        if not install_package(package):
            failed.append(package)

    print("\n2. INSTALANDO PADDLEOCR")
    print("-" * 40)

    # Detectar sistema operativo y arquitectura (informativo)
    os_type = platform.system()
    machine = platform.machine()
    print(f"Sistema detectado: {os_type} {machine}")

    # Fijar versiones amigables para evitar dependencias pesadas
    paddle_package = "paddlepaddle==3.1.2"   # versión estable que evita rutas enormes
    paddleocr_package = "paddleocr==2.7.0.3" # no arrastra paddlex/modelscope

    # Instalar PaddlePaddle
    if not install_package(paddle_package):
        print("\n⚠ ADVERTENCIA: PaddlePaddle no se pudo instalar.")
        print("Puedes intentar instalarlo manualmente con:")
        print(f"  pip install {paddle_package}")
        print("\nPara GPU con CUDA, usa (si corresponde):")
        print("  pip install paddlepaddle-gpu")
        failed.append(paddle_package)

    # Instalar PaddleOCR (solo si Paddle al menos intentó instalar)
    if not install_package(paddleocr_package):
        print("\n⚠ ADVERTENCIA: PaddleOCR no se pudo instalar.")
        print("Intenta instalarlo manualmente con:")
        print(f"  pip install {paddleocr_package}")
        failed.append(paddleocr_package)

    print("\n3. VERIFICANDO INSTALACIÓN")
    print("-" * 40)

    # Verificar instalaciones
    installed = []
    not_installed = []

    packages_to_check = basic_packages + [paddle_package, paddleocr_package]

    for package in packages_to_check:
        try:
            # Normaliza a nombre de módulo
            base = package.split("==")[0]  # quita versiones si las hay
            module_name = base.replace("-", "_")
            if base == "opencv-python-headless":
                module_name = "cv2"
            elif base == "pillow":
                module_name = "PIL"
            elif base == "pypdf":
                module_name = "pypdf"
            elif base == "pdf2image":
                module_name = "pdf2image"
            elif base == "paddlepaddle":
                module_name = "paddle"
            # Import test
            __import__(module_name)
            installed.append(base)
        except ImportError:
            not_installed.append(base)

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

    print("\n⚠ IMPORTANTE: Además de las librerías Python, necesitas instalar:")
    print()
    print("1. TESSERACT OCR")
    print("   - Windows: https://github.com/tesseract-ocr/tesseract")
    print("   - Linux: sudo apt-get install tesseract-ocr tesseract-ocr-spa")
    print("   - macOS: brew install tesseract")
    print()
    print("2. POPPLER (para PDFs)")
    print("   - Windows: https://github.com/oschwartz10612/poppler-windows/releases")
    print("   - Linux: sudo apt-get install poppler-utils")
    print("   - macOS: brew install poppler")
    print()
    print("3. IDIOMA ESPAÑOL PARA TESSERACT")
    print("   - Descargar spa.traineddata de:")
    print("     https://github.com/tesseract-ocr/tessdata")
    print("   - Copiarlo a la carpeta tessdata de Tesseract")

    print("\n" + "=" * 60)
    print("CONFIGURACIÓN DE VARIABLES DE ENTORNO (Opcional)")
    print("=" * 60)
    print()
    print("Si Tesseract o Poppler no son detectados automáticamente:")
    print()
    print("Windows:")
    print("  set TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
    print("  set POPPLER_PATH=C:\\poppler\\Library\\bin")
    print()
    print("Linux/macOS:")
    print("  export TESSERACT_CMD=/usr/bin/tesseract")
    print("  export POPPLER_PATH=/usr/bin")

    print("\n" + "=" * 60)

    if not not_installed or (len(not_installed) <= 2 and "paddleocr" in [p.lower() for p in not_installed]):
        print("✓ INSTALACIÓN COMPLETADA EXITOSAMENTE")
        print()
        print("Puedes ejecutar el sistema con:")
        print("  python main_enhanced.py")
    else:
        print("⚠ INSTALACIÓN PARCIALMENTE COMPLETADA")
        print()
        print("Instala los paquetes faltantes manualmente antes de ejecutar el sistema.")

    print("=" * 60)

    # Resumen rápido para lectura humana
    print(f"\nRESUMEN ▶ OK={len(installed)} | FALTAN={len(not_installed)}")
    input("\nPresiona Enter para terminar...")

    # Código de salida para automatizaciones (0=ok, 1=faltantes)
    sys.exit(0 if not not_installed else 1)

if __name__ == "__main__":
    main()
