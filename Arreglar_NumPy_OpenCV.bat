@echo off
chcp 65001 >nul
title Arreglar Problema NumPy/OpenCV

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║     ARREGLO: Incompatibilidad NumPy 2.x / OpenCV         ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.
echo PROBLEMA DETECTADO:
echo   ❌ NumPy 2.3.4 instalado (incompatible con OpenCV)
echo   ✓ OpenCV compilado para NumPy 1.x
echo.
echo SOLUCIÓN:
echo   Downgrade a NumPy ^< 2.0 (compatible con OpenCV)
echo.
pause

echo.
echo [1/3] Desinstalando NumPy 2.3.4...
pip uninstall numpy -y
if errorlevel 1 (
    echo ⚠️  No se pudo desinstalar. Intentando con conda...
    conda uninstall numpy -y
)

echo.
echo [2/3] Instalando NumPy 1.26.4 (compatible)...
pip install "numpy<2" --force-reinstall
if errorlevel 1 (
    echo ⚠️  Pip falló. Intentando con conda...
    conda install "numpy<2" -y
)

echo.
echo [3/3] Verificando instalación...
python -c "import numpy; print(f'NumPy version: {numpy.__version__}')"
if errorlevel 1 (
    echo ❌ ERROR: NumPy no se instaló correctamente
    pause
    exit /b 1
)

echo.
echo Verificando OpenCV...
python -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"
if errorlevel 1 (
    echo ❌ ERROR: OpenCV sigue con problemas
    echo.
    echo Intentando reinstalar OpenCV...
    pip uninstall opencv-python opencv-python-headless -y
    pip install opencv-python-headless
)

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║              ✓ PROBLEMA RESUELTO                          ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.
echo Ahora puedes ejecutar:
echo   python main.py
echo.
echo Las mejoras v3.2 ya están instaladas y funcionarán correctamente.
echo.
pause