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
from typing import List, Optional



def install_package(package: str, extra_args: Optional[List[str]] = None) -> bool:
    """Instala un paquete con pip (sin cache).

    Args:
        package: Cadena del paquete (puede incluir versión o URL).
        extra_args: Argumentos adicionales a pasar antes del nombre del paquete.
    """
    try:
        print(f"Instalando {package}...")
        cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir"]
        if extra_args:
            cmd.extend(extra_args)
        cmd.append(package)
        subprocess.check_call(cmd)
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

def select_paddle_package(os_type: str, machine: str, version_info: sys.version_info) -> str:
    """Devuelve la versión recomendada de paddlepaddle para la plataforma actual.

    La matriz se basa en las compilaciones oficiales CPU (ruedas manylinux/win/mac) y
    prioriza mantener un binario compatible sin obligar a instalar dependencias GPU.
    Si no hay coincidencia exacta, se devuelve la opción más estable conocida para
    ese sistema operativo o un valor por defecto para CPU.
    """

    python_tag = f"{version_info.major}.{version_info.minor}"
    normalized_os = os_type.lower()
    normalized_machine = machine.lower()

    # Curado manualmente a partir de los binarios disponibles en https://www.paddlepaddle.org.cn/
    compatibility_matrix = {
        ("windows", "amd64"): {
            "3.8": "paddlepaddle==2.5.2",
            "3.9": "paddlepaddle==2.5.2",
            "3.10": "paddlepaddle==3.1.2",
            "3.11": "paddlepaddle==3.1.2",
            "3.12": "paddlepaddle==3.2.0",
            "3.13": "paddlepaddle==3.2.0",
        },
        ("windows", "arm64"): {
            "3.10": "paddlepaddle==2.5.2",
            "3.11": "paddlepaddle==2.5.2",
            "3.12": "paddlepaddle==3.2.0",
            "3.13": "paddlepaddle==3.2.0",
        },
        ("linux", "x86_64"): {
            "3.8": "paddlepaddle==2.6.1",
            "3.9": "paddlepaddle==2.6.1",
            "3.10": "paddlepaddle==2.6.1",
            "3.11": "paddlepaddle==2.6.1",
            "3.12": "paddlepaddle==2.6.1",
        },
        ("linux", "aarch64"): {
            "3.10": "paddlepaddle==2.6.1",
            "3.11": "paddlepaddle==2.6.1",
            "3.12": "paddlepaddle==2.6.1",
        },
        ("darwin", "x86_64"): {
            "3.9": "paddlepaddle==2.5.2",
            "3.10": "paddlepaddle==2.5.2",
        },
        ("darwin", "arm64"): {
            "3.9": "paddlepaddle==2.5.2",
            "3.10": "paddlepaddle==2.5.2",
            "3.11": "paddlepaddle==2.5.2",
        },
    }

    fallback_per_os = {
        "windows": "paddlepaddle==3.2.0",
        "linux": "paddlepaddle==2.6.1",
        "darwin": "paddlepaddle==2.5.2",
    }

    chosen = None
    matrix_key = (normalized_os, normalized_machine)
    if matrix_key in compatibility_matrix:
        candidates = compatibility_matrix[matrix_key]
        if python_tag in candidates:
            chosen = candidates[python_tag]
            print(
                f"Seleccionando PaddlePaddle {chosen} (match exacto para {os_type} {machine} y Python {python_tag})."
            )
        else:
            # Usa la versión más moderna disponible para esa plataforma que no exceda
            # la versión de Python actual. Si no hay ninguna <=, toma la más reciente.
            def _parse_py_tag(tag: str) -> tuple[int, int]:
                major_str, minor_str = tag.split(".")
                return int(major_str), int(minor_str)

            sorted_candidates = sorted(
                ((_parse_py_tag(py_tag), pkg) for py_tag, pkg in candidates.items()),
                key=lambda item: item[0],
            )
            current_version = _parse_py_tag(python_tag)
            chosen_pkg = None
            for py_version, pkg in sorted_candidates:
                if py_version <= current_version:
                    chosen_pkg = pkg
            if not chosen_pkg:
                # No se encontró una versión <= a la actual; usa la más baja disponible.
                chosen_pkg = sorted_candidates[0][1]

            chosen = chosen_pkg
            print(
                "⚠ No hay build exacto para Python "
                f"{python_tag}; usando {chosen} (versión más estable disponible para {os_type} {machine})."
            )
    if not chosen:
        default_pkg = fallback_per_os.get(normalized_os, "paddlepaddle==3.2.0")
        chosen = default_pkg
        print(
            "⚠ Plataforma no listada explícitamente en la matriz de compatibilidad. "
            f"Usando valor por defecto {chosen} (CPU)."
        )

    return chosen

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
    paddle_pkg = select_paddle_package(os_type, machine, sys.version_info)
    paddleocr_pkg = "paddleocr==2.7.0.3"

    if not install_package(paddle_pkg):
        print("\n⚠ ADVERTENCIA: PaddlePaddle no se pudo instalar.")
        print("Esta es la versión sugerida para tu entorno detectado.")
        print("Intenta instalarla manualmente con:")
        print(f"  pip install {paddle_pkg}")
        print("\nPara GPU con CUDA (si corresponde):")
        print("  pip install paddlepaddle-gpu")
        failed.append(paddle_pkg)

    def manual_paddleocr_install() -> tuple[bool, bool]:
        print("\n⚠ Ejecutando instalación guiada de PaddleOCR para entornos recientes...")
        manual_deps: List[tuple[str, Optional[List[str]]]] = [
            ("shapely>=2.0,<2.2", None),
            ("scikit-image>=0.25", None),
            ("imgaug>=0.4", None),
            ("pyclipper>=1.3.0.post5", None),
            ("lmdb>=1.4", None),
            ("visualdl>=2.5", None),
            ("rapidfuzz>=3.0", None),
            ("opencv-python>=4.10", None),
            ("opencv-contrib-python>=4.10", None),
            ("cython>=3.0", None),
            ("lxml>=4.9", None),
            ("premailer>=3.10", None),
            ("attrdict>=2.0", None),
            ("PyYAML>=6.0", None),
            ("python-docx>=1.0", None),
            ("beautifulsoup4>=4.9", None),
            ("fonttools>=4.24.0", None),
            ("fire>=0.3.0", None),
            ("pdf2docx>=0.5.8", None),
            ("PyMuPDF>=1.24,<1.28", ["--only-binary", ":all:"]),
        ]

        if not install_package(paddleocr_pkg, extra_args=["--no-deps"]):
            return False, False

        pdf_ready = True
        all_ok = True
        for dep, extra in manual_deps:
            if not install_package(dep, extra_args=extra):
                failed.append(dep)
                all_ok = False
                if dep.lower().startswith("pymupdf"):
                    pdf_ready = False
        if not pdf_ready:
            print(
                "⚠ PyMuPDF no pudo instalarse automáticamente. PaddleOCR funcionará sin soporte directo de PDF."
            )
        return all_ok, pdf_ready and all_ok

    force_manual = os_type.lower() == "windows" and sys.version_info >= (3, 13)
    paddleocr_pdf_support = True
    if force_manual:
        paddleocr_installed, paddleocr_pdf_support = manual_paddleocr_install()
        if not paddleocr_installed:
    paddleocr_installed = install_package(paddleocr_pkg)
    paddleocr_pdf_support = True
    if not paddleocr_installed:
        print("\n⚠ Intento alternativo: instalando PaddleOCR sin PyMuPDF (soporte PDF deshabilitado)...")
        # PyMuPDF no ofrece binarios para Python 3.13 aún; instalamos PaddleOCR sin dependencias
        # y luego añadimos las dependencias críticas manualmente (excepto PyMuPDF).
        fallback_deps = [
            "shapely",
            "scikit-image",
            "imgaug",
            "pyclipper",
            "lmdb",
            "visualdl",
            "rapidfuzz",
            "opencv-python<=4.6.0.66",
            "opencv-contrib-python<=4.6.0.66",
            "cython",
            "lxml",
            "premailer",
            "attrdict",
            "PyYAML",
            "python-docx",
            "beautifulsoup4",
            "fonttools>=4.24.0",
            "fire>=0.3.0",
            "pdf2docx",
        ]

        paddleocr_installed = install_package(paddleocr_pkg, extra_args=["--no-deps"])
        if paddleocr_installed:
            for dep in fallback_deps:
                install_package(dep)
            paddleocr_pdf_support = False
        else:
main
            print("\n⚠ ADVERTENCIA: PaddleOCR no se pudo instalar.")
            print("Intenta instalarlo manualmente con:")
            print(f"  pip install {paddleocr_pkg}")
            failed.append(paddleocr_pkg)

    else:
        paddleocr_installed = install_package(paddleocr_pkg)
        if not paddleocr_installed:
            paddleocr_installed, paddleocr_pdf_support = manual_paddleocr_install()
            if not paddleocr_installed:
                print("\n⚠ ADVERTENCIA: PaddleOCR no se pudo instalar.")
                print("Intenta instalarlo manualmente con:")
                print(f"  pip install {paddleocr_pkg}")
                failed.append(paddleocr_pkg)

    elif os_type.lower() == "windows" and sys.version_info >= (3, 13):
        # Incluso si la instalación pasó (p. ej. en un entorno con VS Build Tools), advertimos de PDF.
        paddleocr_pdf_support = False
main

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
        except Exception as exc:
            if (
                base == "paddleocr"
                and paddleocr_installed
                and not paddleocr_pdf_support
                and isinstance(exc, ModuleNotFoundError)
                and getattr(exc, "name", "") in {"fitz", "PyMuPDF"}
            ):
                # Se permite la ausencia de PyMuPDF en el fallback sin soporte PDF.
                installed.append(base)
                continue
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

    if paddleocr_installed and not paddleocr_pdf_support:
        print(
            "\n⚠ PaddleOCR instalado sin PyMuPDF: la conversión directa de PDF con PaddleOCR queda deshabilitada."
        )
        print("   El sistema seguirá funcionando con Tesseract y PaddleOCR para imágenes.")

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
