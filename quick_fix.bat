@echo off
chcp 65001 >nul
title Quick Fix - Sistema de Boletas v3.1

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║              ARREGLO RÁPIDO - Sistema v3.1                ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

echo 📋 Este script corregirá los problemas más comunes...
echo.

REM ============================================
echo [1/5] Verificando Python...
REM ============================================
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado
    echo    Instalar desde: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo ✓ Python OK
python --version

REM ============================================
echo.
echo [2/5] Reinstalando dependencias críticas...
REM ============================================
echo    Esto puede tomar 2-3 minutos...
echo.

REM Desinstalar versiones problemáticas
python -m pip uninstall opencv-python opencv-python-headless numpy -y >nul 2>&1

REM Instalar versiones estables
echo    → opencv-python-headless...
python -m pip install opencv-python-headless==4.8.1.78 --quiet --disable-pip-version-check

echo    → numpy...
python -m pip install numpy==1.24.3 --quiet --disable-pip-version-check

echo    → pytesseract...
python -m pip install pytesseract==0.3.10 --quiet --disable-pip-version-check

echo    → pdf2image...
python -m pip install pdf2image==1.16.3 --quiet --disable-pip-version-check

echo    → pillow...
python -m pip install pillow==10.1.0 --quiet --disable-pip-version-check

echo    → pandas...
python -m pip install pandas==2.0.3 --quiet --disable-pip-version-check

echo    → pypdf...
python -m pip install pypdf==3.17.0 --quiet --disable-pip-version-check

echo.
echo ✓ Dependencias instaladas

REM ============================================
echo.
echo [3/5] Verificando Tesseract...
REM ============================================
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Tesseract NO encontrado
    echo    El OCR no funcionará sin Tesseract
    echo.
    echo    Descargar desde:
    echo    https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    echo    Después de instalar, ejecutar este script nuevamente
    echo.
    pause
    exit /b 1
)
echo ✓ Tesseract OK
tesseract --version | findstr "tesseract"

REM Verificar idioma español
tesseract --list-langs 2>nul | findstr "spa" >nul
if errorlevel 1 (
    echo ⚠️ Idioma español (spa) NO encontrado
    echo    Copiar spa.traineddata a:
    echo    C:\Program Files\Tesseract-OCR\tessdata\
    echo.
)

REM ============================================
echo.
echo [4/5] Configurando modo seguro...
REM ============================================

REM Crear backup de config.py si no existe
if not exist config.py.backup (
    copy config.py config.py.backup >nul 2>&1
)

REM Modificar MAX_WORKERS a 1 para debugging
python -c "import re; content = open('config.py', 'r', encoding='utf-8').read(); content = re.sub(r'MAX_WORKERS = .*', 'MAX_WORKERS = 1  # Modo seguro - 1 worker', content); open('config.py', 'w', encoding='utf-8').write(content)"

echo ✓ Configurado para 1 worker (modo seguro)

REM ============================================
echo.
echo [5/5] Creando script de prueba...
REM ============================================

REM Crear test_single.py
(
echo import sys
echo from pathlib import Path
echo sys.path.append^(str^(Path^(__file__^).parent^)^)
echo.
echo print^("Probando imports..."^)
echo try:
echo     from modules.data_processing import DataProcessorOptimized
echo     print^("✓ Módulos OK"^)
echo.
echo     if len^(sys.argv^) ^> 1:
echo         processor = DataProcessorOptimized^(^)
echo         file_path = Path^(sys.argv[1]^)
echo         print^(f"Procesando: {file_path.name}"^)
echo         result = processor.process_file^(file_path^)
echo         print^("✓ Procesamiento exitoso"^)
echo         print^(f"  - RUT: {result.get^('rut', 'N/A'^)}"^)
echo         print^(f"  - Monto: {result.get^('monto', 'N/A'^)}"^)
echo         print^(f"  - Confianza: {result.get^('confianza', 0^):.1%%}"^)
echo     else:
echo         print^("Uso: python test_single.py archivo.pdf"^)
echo except Exception as e:
echo     print^(f"✗ Error: {e}"^)
echo     import traceback
echo     traceback.print_exc^(^)
) > test_single.py

echo ✓ Script de prueba creado: test_single.py

REM ============================================
echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║                  ✓ ARREGLO COMPLETADO                     ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.
echo 📋 Próximos pasos:
echo.
echo 1. Probar con UN archivo:
echo    python test_single.py "ruta\al\archivo.pdf"
echo.
echo 2. Si funciona, ejecutar el sistema completo:
echo    python main.py
echo.
echo 3. Si sigue fallando, ejecutar diagnóstico:
echo    python diagnostico_errores.py "ruta\al\archivo.pdf"
echo.
echo ⚠️ El sistema está en MODO SEGURO (1 worker)
echo    Para volver a modo normal, editar config.py línea 15
echo.
pause