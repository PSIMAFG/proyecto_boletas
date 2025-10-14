# ============================================================================
# instalar_tesseract.bat
# ============================================================================
@echo off
title Instalador de Tesseract OCR
cls

echo =====================================================
echo    INSTALADOR DE TESSERACT OCR
echo =====================================================
echo.
echo Este script descargará e instalará Tesseract OCR
echo.

echo Verificando si Tesseract ya está instalado...
where tesseract >nul 2>&1
if not errorlevel 1 (
    echo.
    echo Tesseract ya está instalado en su sistema
    tesseract --version
    pause
    exit /b 0
)

echo.
echo Tesseract NO está instalado.
echo.
echo Para instalar Tesseract manualmente:
echo.
echo 1. Visite: https://github.com/UB-Mannheim/tesseract/wiki
echo 2. Descargue el instalador para Windows (64-bit)
echo 3. Durante la instalación:
echo    - Seleccione "Additional language data"
echo    - Marque "Spanish" para soporte en español
echo 4. Instale en la ruta por defecto: C:\Program Files\Tesseract-OCR
echo.
echo Presione cualquier tecla para abrir la página de descarga...
pause >nul

start https://github.com/UB-Mannheim/tesseract/wiki

echo.
echo Después de instalar Tesseract, ejecute nuevamente "ejecutar_sistema.bat"
echo.
pause
exit /b 0


